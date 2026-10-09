"""Automations CRUD (ADR 0013). Read: any member. Write: 'configure'."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    Principal, client_ip, get_contracts, get_db, get_principal, membership_or_404,
    require_permission,
)
from app.core.contracts import Contracts
from app.core.errors import ApiError, not_found, validation_error
from app.core.responses import ok
from app.models import Automation, AutomationRun, Home
from app.schemas.common import Model
from app.services import audit
from app.services.automations import automation_out, run_out, validate

router = APIRouter(tags=["automations"])


class AutomationIn(Model):
    name: str = Field(min_length=1, max_length=120)
    enabled: bool = True
    definition: dict


class AutomationPatch(Model):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    enabled: Optional[bool] = None
    definition: Optional[dict] = None


def _last_runs(db: Session, ids):
    if not ids:
        return {}
    sub = (select(AutomationRun.automation_id, func.max(AutomationRun.ts).label("ts"))
           .where(AutomationRun.automation_id.in_(ids)).group_by(AutomationRun.automation_id)
           .subquery())
    rows = db.scalars(select(AutomationRun).join(
        sub, (AutomationRun.automation_id == sub.c.automation_id) & (AutomationRun.ts == sub.c.ts)))
    return {r.automation_id: r for r in rows}


@router.get("/homes/{home_id}/automations")
def list_automations(home_id: uuid.UUID, p: Principal = Depends(get_principal),
                     db: Session = Depends(get_db)):
    membership_or_404(db, home_id, p.user)
    rows = db.scalars(select(Automation).where(Automation.home_id == home_id)
                      .order_by(Automation.name)).all()
    last = _last_runs(db, [a.id for a in rows])
    return ok([automation_out(a, last.get(a.id)) for a in rows], {"total": len(rows)})


@router.post("/homes/{home_id}/automations:validate")
def validate_automation(home_id: uuid.UUID, body: AutomationIn,
                        p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                        contracts: Contracts = Depends(get_contracts)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    validate(db, contracts, db.get(Home, home_id), body.definition, name=body.name)
    return ok({"valid": True})


@router.post("/homes/{home_id}/automations", status_code=201)
def create_automation(home_id: uuid.UUID, body: AutomationIn, request: Request,
                      p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                      contracts: Contracts = Depends(get_contracts)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    validate(db, contracts, db.get(Home, home_id), body.definition, name=body.name)
    a = Automation(id=uuid.uuid4(), home_id=home_id, name=body.name, enabled=body.enabled,
                   definition=body.definition, version=1, created_by=p.user.id)
    db.add(a)
    audit.record(db, "automation.created", actor_id=p.user.id, home_id=home_id,
                 target_type="automation", target_id=a.id, ip=client_ip(request),
                 details={"name": a.name})
    db.commit()
    return ok(automation_out(a))


def _get(db: Session, automation_id: uuid.UUID, p: Principal):
    a = db.get(Automation, automation_id)
    if a is None:
        raise not_found("Automation")
    try:
        m = membership_or_404(db, a.home_id, p.user)
    except ApiError:
        raise not_found("Automation")
    return a, m


@router.get("/automations/{automation_id}")
def get_automation(automation_id: uuid.UUID, p: Principal = Depends(get_principal),
                   db: Session = Depends(get_db)):
    a, _ = _get(db, automation_id, p)
    return ok(automation_out(a, _last_runs(db, [a.id]).get(a.id)))


@router.patch("/automations/{automation_id}")
def patch_automation(automation_id: uuid.UUID, body: AutomationPatch, request: Request,
                     p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                     contracts: Contracts = Depends(get_contracts)):
    a, m = _get(db, automation_id, p)
    require_permission(m, "configure")
    changes = body.model_dump(exclude_unset=True)
    if any(changes.get(k, "") is None for k in ("name", "enabled", "definition")):
        raise validation_error("Fields cannot be null")
    definition = changes.get("definition", a.definition)
    enabled = changes.get("enabled", a.enabled)
    if "definition" in changes or (enabled and not a.enabled):
        # Re-check against today's devices and loops before it becomes active again.
        validate(db, contracts, db.get(Home, a.home_id), definition, self_id=a.id,
                 name=changes.get("name", a.name))
    for k, v in changes.items():
        setattr(a, k, v)
    a.version += 1
    audit.record(db, "automation.updated", actor_id=p.user.id, home_id=a.home_id,
                 target_type="automation", target_id=a.id, ip=client_ip(request),
                 details={"fields": sorted(changes), "version": a.version})
    db.commit()
    return ok(automation_out(a))


@router.delete("/automations/{automation_id}")
def delete_automation(automation_id: uuid.UUID, request: Request,
                      p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    a, m = _get(db, automation_id, p)
    require_permission(m, "configure")
    db.delete(a)
    audit.record(db, "automation.deleted", actor_id=p.user.id, home_id=a.home_id,
                 target_type="automation", target_id=a.id, ip=client_ip(request),
                 details={"name": a.name})
    db.commit()
    return ok({"deleted": True})


@router.get("/automations/{automation_id}/runs")
def list_runs(automation_id: uuid.UUID, limit: int = Query(50, ge=1, le=200),
              p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    a, _ = _get(db, automation_id, p)
    rows = db.scalars(select(AutomationRun).where(AutomationRun.automation_id == a.id)
                      .order_by(AutomationRun.ts.desc()).limit(limit)).all()
    return ok([run_out(r) for r in rows], {"count": len(rows)})
