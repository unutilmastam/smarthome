"""Hub-facing API (hub token auth). The Hub always connects outbound."""

import json
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from pydantic import Field
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_contracts, get_db
from app.api.hub_auth import get_hub
from app.core.config import Settings, get_settings
from app.core.contracts import Contracts
from app.core.errors import validation_error
from app.core.responses import ok
from app.db.types import utcnow
from app.models import Device, Home, Hub
from app.schemas.common import Model
from app.services.commands import apply_ack, claim_for_hub, expire_due
from app.services.device_view import iso
from app.services.hub_reports import apply_report
from app.services.telemetry import ingest as ingest_telemetry

router = APIRouter(prefix="/hub", tags=["hub"])


@lru_cache(maxsize=4)
def _validators(schemas_dir: str):
    from pathlib import Path
    schemas = {p.name: json.loads(p.read_text(encoding="utf-8"))
               for p in Path(schemas_dir).glob("*.schema.json")}
    registry = Registry().with_resources(
        [(s["$id"], Resource.from_contents(s)) for s in schemas.values()]
        + [(n, Resource.from_contents(s)) for n, s in schemas.items()]
    )
    fc = Draft202012Validator.FORMAT_CHECKER
    return {n: Draft202012Validator(s, registry=registry, format_checker=fc)
            for n, s in schemas.items()}


def _validate(contracts: Contracts, name: str, doc) -> None:
    v = _validators(str(contracts.dir / "schemas"))[name]
    errors = sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if errors:
        raise validation_error(
            f"Document does not match {name}",
            [{"path": "/".join(str(x) for x in e.absolute_path), "msg": e.message}
             for e in errors[:20]],
        )


class HeartbeatIn(Model):
    version: Optional[str] = None
    hub_time: Optional[str] = None
    health: Optional[dict] = None
    # Where the user's phone can reach the hub (never used by the cloud itself).
    tailnet_host: Optional[str] = Field(default=None, max_length=253,
                                        pattern=r"^[A-Za-z0-9.\-]+$")
    lan_host: Optional[str] = Field(default=None, max_length=253, pattern=r"^[A-Za-z0-9.\-]+$")


@router.post("/heartbeat")
def heartbeat(body: HeartbeatIn, hub: Hub = Depends(get_hub), db: Session = Depends(get_db)):
    now = utcnow()
    hub.last_seen = now
    if body.version and body.version != hub.version:
        hub.version = body.version[:40]
    if body.tailnet_host is not None:
        hub.tailnet_host = body.tailnet_host or None
    if body.lan_host is not None:
        hub.lan_host = body.lan_host or None
    db.commit()
    return ok({"server_time": iso(now), "hub_id": str(hub.id)})


@router.get("/commands")
def get_commands(limit: int = Query(20, ge=1, le=100), hub: Hub = Depends(get_hub),
                 db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
                 contracts: Contracts = Depends(get_contracts)):
    expire_due(db, settings, contracts, home_id=hub.home_id)
    cmds = claim_for_hub(db, hub, limit)
    return ok([c.envelope for c in cmds], {"count": len(cmds), "server_time": iso(utcnow())})


@router.post("/acks")
def post_acks(body: dict = Body(...), hub: Hub = Depends(get_hub), db: Session = Depends(get_db),
              contracts: Contracts = Depends(get_contracts)):
    acks = body.get("acks")
    if not isinstance(acks, list) or not 1 <= len(acks) <= 200:
        raise validation_error("acks must be a list of 1..200 items")
    for a in acks:
        _validate(contracts, "ack.schema.json", a)
    results = [apply_ack(db, hub, a) for a in acks]
    db.commit()
    return ok({"results": results})


@router.post("/report")
def post_report(body: dict = Body(...), hub: Hub = Depends(get_hub),
                db: Session = Depends(get_db), contracts: Contracts = Depends(get_contracts)):
    _validate(contracts, "state-report.schema.json", body)
    return ok(apply_report(db, hub, contracts, body))


@router.get("/config")
def get_config(hub: Hub = Depends(get_hub), db: Session = Depends(get_db),
               contracts: Contracts = Depends(get_contracts)):
    home = db.get(Home, hub.home_id)
    devices = db.scalars(select(Device).where(Device.home_id == hub.home_id)
                         .order_by(Device.key)).all()
    return ok({
        "home": {"id": str(home.id), "name": home.name, "timezone": home.timezone,
                 "latitude": home.latitude, "longitude": home.longitude},
        "hub_id": str(hub.id),
        "contracts_version": contracts.registry.get("version"),
        "devices": [
            {"id": str(d.id), "key": d.key, "name": d.name, "adapter": d.adapter,
             "protocol": d.protocol, "model": d.model, "enabled": d.enabled,
             "fail_safe_state": d.fail_safe_state, "unsupported": d.unsupported or [],
             "capabilities": {c.capability: c.config_json or {} for c in d.capabilities}}
            for d in devices
        ],
        "server_time": iso(utcnow()),
    })




@router.post("/telemetry:batch")
def post_telemetry(body: dict = Body(...), hub: Hub = Depends(get_hub),
                   db: Session = Depends(get_db), contracts: Contracts = Depends(get_contracts)):
    _validate(contracts, "telemetry-batch.schema.json", body)
    return ok(ingest_telemetry(db, hub, contracts, body))
