"""Links to other ecosystems (ADR 0016): Yandex Alisa. The token is write-only."""

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    Principal, client_ip, get_contracts, get_db, get_principal, membership_or_404, require_permission,
)
from app.core.config import Settings, get_settings
from app.core.contracts import Contracts
from app.core.errors import ApiError, not_found
from app.core.responses import ok
from app.core.secretbox import seal
from app.models import Device, Integration
from app.schemas.common import Model
from app.services import audit, yandex
from app.services.device_view import iso

router = APIRouter(tags=["integrations"])


class YandexIn(Model):
    # OAuth token from oauth.yandex.ru (iot:view, iot:control). Never returned.
    token: str = Field(min_length=20, max_length=200, pattern=r"^[A-Za-z0-9_\-.]+$")


def _view(i: Integration) -> dict:
    data = i.data or {}
    return {"kind": i.kind, "status": i.status, "error": i.error, "last_sync": iso(i.last_sync_at),
            "scenarios": data.get("scenarios", []), "skipped": data.get("skipped", [])}


def _get(db: Session, home_id: uuid.UUID) -> Integration:
    i = db.scalar(select(Integration).where(Integration.home_id == home_id, Integration.kind == "yandex"))
    if i is None:
        raise not_found("Yandex integration")
    return i


@router.get("/homes/{home_id}/integrations/yandex")
def get_yandex(home_id: uuid.UUID, p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    membership_or_404(db, home_id, p.user)
    i = db.scalar(select(Integration).where(Integration.home_id == home_id, Integration.kind == "yandex"))
    return ok(_view(i) if i else {"kind": "yandex", "status": "not_connected"})


@router.put("/homes/{home_id}/integrations/yandex")
def connect_yandex(home_id: uuid.UUID, body: YandexIn, request: Request, p: Principal = Depends(get_principal),
                   db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
                   contracts: Contracts = Depends(get_contracts)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    i = db.scalar(select(Integration).where(Integration.home_id == home_id, Integration.kind == "yandex"))
    if i is None:
        i = Integration(id=uuid.uuid4(), home_id=home_id, kind="yandex", secret_enc="")
        db.add(i)
    i.secret_enc = seal(settings.signing_master_key, body.token, str(i.id))
    i.status = "pending"
    audit.record(db, "integration.connected", actor_id=p.user.id, home_id=home_id,
                 target_type="integration", target_id=i.id, ip=client_ip(request), details={"kind": "yandex"})
    db.commit()
    yandex.sync(db, i, contracts, settings)      # tells at once whether the token works
    return ok(_view(i))


@router.post("/homes/{home_id}/integrations/yandex/sync")
def sync_yandex(home_id: uuid.UUID, p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                settings: Settings = Depends(get_settings), contracts: Contracts = Depends(get_contracts)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    i = _get(db, home_id)
    yandex.sync(db, i, contracts, settings)
    return ok(_view(i))


@router.post("/homes/{home_id}/integrations/yandex/scenarios/{scenario_id}/run")
def run_scenario(home_id: uuid.UUID, scenario_id: str, request: Request, p: Principal = Depends(get_principal),
                 db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "control_basic")
    i = _get(db, home_id)
    if scenario_id not in {s["id"] for s in (i.data or {}).get("scenarios", [])}:
        raise not_found("Scenario")
    try:
        yandex.run_scenario(i, settings, scenario_id)
    except yandex.YandexError as exc:
        raise ApiError(502, "INTEGRATION_ERROR", str(exc))
    audit.record(db, "integration.scenario_run", actor_id=p.user.id, home_id=home_id, target_type="integration",
                 target_id=i.id, ip=client_ip(request), details={"scenario_id": scenario_id})
    db.commit()
    return ok({"started": True})


@router.delete("/homes/{home_id}/integrations/yandex")
def disconnect_yandex(home_id: uuid.UUID, request: Request, p: Principal = Depends(get_principal),
                      db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    i = _get(db, home_id)
    # The token is gone with the row; Yandex devices stay (history), honestly unreachable.
    for d in db.scalars(select(Device).where(Device.home_id == home_id, Device.adapter == "yandex")):
        d.availability, d.availability_ts = "offline", None
    audit.record(db, "integration.disconnected", actor_id=p.user.id, home_id=home_id,
                 target_type="integration", target_id=i.id, ip=client_ip(request), details={"kind": "yandex"})
    db.delete(i)
    db.commit()
    return ok({"deleted": True})
