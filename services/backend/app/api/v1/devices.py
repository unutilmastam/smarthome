import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    Principal, client_ip, get_contracts, get_db, get_principal, membership_or_404,
    require_permission,
)
from app.core.config import Settings, get_settings
from app.core.contracts import Contracts
from app.core.errors import ApiError, conflict, not_found, validation_error
from app.core.responses import ok
from app.models import Device, DeviceCapability
from app.schemas.common import Page
from app.schemas.devices import DeviceIn, DevicePatch
from app.services import audit
from app.services.device_view import device_view
from app.services.devices import active_hub, check_room, set_capabilities, validate_capabilities

router = APIRouter(tags=["devices"])


@router.get("/homes/{home_id}/devices")
def list_devices(
    home_id: uuid.UUID,
    page: Page = Depends(),
    room_id: Optional[uuid.UUID] = Query(None),
    capability: Optional[str] = Query(None, max_length=40),
    availability: Optional[str] = Query(None, pattern="^(online|offline|unknown)$"),
    q: Optional[str] = Query(None, max_length=120),
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
    contracts: Contracts = Depends(get_contracts),
    settings: Settings = Depends(get_settings),
):
    membership_or_404(db, home_id, p.user)
    base = select(Device).where(Device.home_id == home_id)
    if room_id is not None:
        base = base.where(Device.room_id == room_id)
    if capability:
        base = base.where(Device.id.in_(
            select(DeviceCapability.device_id).where(DeviceCapability.capability == capability)))
    if q:
        like = f"%{q.lower()}%"
        base = base.where(func.lower(Device.name).like(like) | func.lower(Device.key).like(like))
    hub = active_hub(db, home_id)
    devices = db.scalars(base.order_by(Device.name, Device.key)).all()
    views = [device_view(d, contracts, settings, hub) for d in devices]
    if availability:
        # Effective availability depends on hub liveness, so filter after computing it.
        views = [v for v in views if v["availability"]["status"] == availability]
    total = len(views)
    views = views[page.offset: page.offset + page.limit]
    return ok(views, page.meta(total))


@router.post("/homes/{home_id}/devices", status_code=201)
def create_device(home_id: uuid.UUID, body: DeviceIn, request: Request,
                  p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                  contracts: Contracts = Depends(get_contracts),
                  settings: Settings = Depends(get_settings)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    validate_capabilities(contracts, body.capabilities, body.unsupported)
    check_room(db, home_id, body.room_id)
    if db.scalar(select(Device.id).where(Device.home_id == home_id, Device.key == body.key)):
        raise conflict(f"Device key '{body.key}' already exists in this home")
    d = Device(
        id=uuid.uuid4(), home_id=home_id, room_id=body.room_id, key=body.key, name=body.name,
        adapter=body.adapter, protocol=body.protocol, model=body.model,
        fail_safe_state=body.fail_safe_state, unsupported=sorted(body.unsupported),
        enabled=body.enabled, availability="unknown",
    )
    set_capabilities(d, body.capabilities)
    db.add(d)
    audit.record(db, "device.created", actor_id=p.user.id, home_id=home_id,
                 target_type="device", target_id=d.id, ip=client_ip(request),
                 details={"key": d.key, "capabilities": sorted(body.capabilities)})
    db.commit()
    return ok(device_view(d, contracts, settings, active_hub(db, home_id)))


def _device_for(db: Session, device_id: uuid.UUID, p: Principal):
    d = db.get(Device, device_id)
    if d is None:
        raise not_found("Device")
    try:
        m = membership_or_404(db, d.home_id, p.user)
    except ApiError:
        raise not_found("Device")
    return d, m


@router.get("/devices/{device_id}")
def get_device(device_id: uuid.UUID, p: Principal = Depends(get_principal),
               db: Session = Depends(get_db), contracts: Contracts = Depends(get_contracts),
               settings: Settings = Depends(get_settings)):
    d, _ = _device_for(db, device_id, p)
    return ok(device_view(d, contracts, settings, active_hub(db, d.home_id)))


@router.patch("/devices/{device_id}")
def patch_device(device_id: uuid.UUID, body: DevicePatch, request: Request,
                 p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                 contracts: Contracts = Depends(get_contracts),
                 settings: Settings = Depends(get_settings)):
    d, m = _device_for(db, device_id, p)
    require_permission(m, "configure")
    changes = body.model_dump(exclude_unset=True)
    for f in ("name", "capabilities", "unsupported", "enabled"):
        if f in changes and changes[f] is None:
            raise validation_error(f"{f} cannot be null")
    caps = changes.get("capabilities") or {c.capability: c.config_json for c in d.capabilities}
    unsupported = changes.get("unsupported", d.unsupported or [])
    if "capabilities" in changes or "unsupported" in changes:
        validate_capabilities(contracts, caps, unsupported)
    if "room_id" in changes:
        check_room(db, d.home_id, changes["room_id"])
    for k in ("name", "room_id", "model", "fail_safe_state", "enabled"):
        if k in changes:
            setattr(d, k, changes[k])
    if "unsupported" in changes:
        d.unsupported = sorted(unsupported)
    if "capabilities" in changes:
        set_capabilities(d, caps)
    audit.record(db, "device.updated", actor_id=p.user.id, home_id=d.home_id,
                 target_type="device", target_id=d.id, ip=client_ip(request),
                 details={"fields": sorted(changes)})
    db.commit()
    db.refresh(d)
    return ok(device_view(d, contracts, settings, active_hub(db, d.home_id)))


@router.delete("/devices/{device_id}")
def delete_device(device_id: uuid.UUID, request: Request, p: Principal = Depends(get_principal),
                  db: Session = Depends(get_db)):
    d, m = _device_for(db, device_id, p)
    require_permission(m, "configure")
    audit.record(db, "device.deleted", actor_id=p.user.id, home_id=d.home_id,
                 target_type="device", target_id=d.id, ip=client_ip(request),
                 details={"key": d.key})
    db.delete(d)
    db.commit()
    return ok({"deleted": True})
