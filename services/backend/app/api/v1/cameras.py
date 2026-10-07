"""Camera METADATA and access links only (ADR 0006).

The cloud never stores, proxies or relays video, snapshots or clips: no upload
endpoint exists, no binary column exists. Live view and archive are opened directly
on the hub's Frigate over the LAN or Tailscale; the cloud only checks permission.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    Principal, client_ip, get_contracts, get_db, get_principal, membership_or_404,
    require_permission,
)
from app.core.config import Settings, get_settings
from app.core.contracts import Contracts
from app.core.errors import ApiError, conflict, not_found
from app.core.permissions import has_permission
from app.core.responses import ok
from app.models import Camera, Device, DeviceCapability
from app.schemas.common import Model
from app.services import audit
from app.services.device_view import device_view, iso
from app.services.devices import active_hub, check_room

router = APIRouter(tags=["cameras"])

FRIGATE_PORT = 8971  # Frigate's authenticated UI/API port


class CameraIn(Model):
    name: str = Field(min_length=1, max_length=120)
    frigate_name: str = Field(pattern=r"^[a-z][a-z0-9_]{1,40}$")
    room_id: Optional[uuid.UUID] = None


def camera_out(c: Camera, device_view_: Optional[dict]) -> dict:
    return {"id": str(c.id), "home_id": str(c.home_id), "name": c.name,
            "frigate_name": c.frigate_name, "room_id": str(c.room_id) if c.room_id else None,
            "device_id": str(c.device_id) if c.device_id else None,
            "status": device_view_["capabilities"]["camera"]["attributes"] if device_view_ else None,
            "availability": device_view_["availability"] if device_view_ else None,
            "created_at": iso(c.created_at)}


@router.get("/homes/{home_id}/cameras")
def list_cameras(home_id: uuid.UUID, p: Principal = Depends(get_principal),
                 db: Session = Depends(get_db), contracts: Contracts = Depends(get_contracts),
                 settings: Settings = Depends(get_settings)):
    membership_or_404(db, home_id, p.user)
    hub = active_hub(db, home_id)
    out = []
    for c in db.scalars(select(Camera).where(Camera.home_id == home_id).order_by(Camera.name)):
        dev = db.get(Device, c.device_id) if c.device_id else None
        out.append(camera_out(c, device_view(dev, contracts, settings, hub) if dev else None))
    return ok(out, {"total": len(out)})


@router.post("/homes/{home_id}/cameras", status_code=201)
def create_camera(home_id: uuid.UUID, body: CameraIn, request: Request,
                  p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                  contracts: Contracts = Depends(get_contracts),
                  settings: Settings = Depends(get_settings)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    check_room(db, home_id, body.room_id)
    key = f"cam_{body.frigate_name}"
    if db.scalar(select(Camera.id).where(Camera.home_id == home_id,
                                         Camera.frigate_name == body.frigate_name)) or \
            db.scalar(select(Device.id).where(Device.home_id == home_id, Device.key == key)):
        raise conflict("Camera already exists")
    dev = Device(id=uuid.uuid4(), home_id=home_id, room_id=body.room_id, key=key, name=body.name,
                 adapter="frigate", protocol="frigate", unsupported=[], availability="unknown")
    dev.capabilities = [DeviceCapability(capability="camera", config_json={})]
    db.add(dev)
    db.flush()  # no ORM relationship: the device row must exist before the FK points to it
    cam = Camera(id=uuid.uuid4(), home_id=home_id, room_id=body.room_id, name=body.name,
                 frigate_name=body.frigate_name, device_id=dev.id,
                 hub_id=getattr(active_hub(db, home_id), "id", None))
    db.add(cam)
    audit.record(db, "camera.created", actor_id=p.user.id, home_id=home_id, target_type="camera",
                 target_id=cam.id, ip=client_ip(request), details={"frigate_name": body.frigate_name})
    db.commit()
    return ok(camera_out(cam, device_view(dev, contracts, settings, active_hub(db, home_id))))


def _camera_for(db: Session, camera_id: uuid.UUID, p: Principal):
    c = db.get(Camera, camera_id)
    if c is None:
        raise not_found("Camera")
    try:
        m = membership_or_404(db, c.home_id, p.user)
    except ApiError:
        raise not_found("Camera")
    return c, m


@router.delete("/cameras/{camera_id}")
def delete_camera(camera_id: uuid.UUID, request: Request, p: Principal = Depends(get_principal),
                  db: Session = Depends(get_db)):
    c, m = _camera_for(db, camera_id, p)
    require_permission(m, "configure")
    dev = db.get(Device, c.device_id) if c.device_id else None
    audit.record(db, "camera.deleted", actor_id=p.user.id, home_id=c.home_id,
                 target_type="camera", target_id=c.id, ip=client_ip(request))
    db.delete(c)
    if dev:
        db.delete(dev)
    db.commit()
    return ok({"deleted": True})


@router.get("/cameras/{camera_id}/access")
def camera_access(camera_id: uuid.UUID, request: Request, p: Principal = Depends(get_principal),
                  db: Session = Depends(get_db)):
    """Links to the hub's Frigate. Video flows phone <-> hub only (LAN or Tailscale)."""
    c, m = _camera_for(db, camera_id, p)
    require_permission(m, "camera_live")
    hub = active_hub(db, c.home_id)
    links = {}
    if hub is not None and hub.tailnet_host:
        links["tailscale"] = f"https://{hub.tailnet_host}:{FRIGATE_PORT}/"
    if hub is not None and hub.lan_host:
        links["lan"] = f"https://{hub.lan_host}:{FRIGATE_PORT}/"
    audit.record(db, "camera.access", actor_id=p.user.id, home_id=c.home_id,
                 target_type="camera", target_id=c.id, ip=client_ip(request))
    db.commit()
    return ok({
        "camera_id": str(c.id), "frigate_camera": c.frigate_name, "links": links,
        "archive_allowed": has_permission(m.role, "camera_archive"),
        "requires": "Tailscale app connected, or the phone on the home Wi-Fi",
    })


