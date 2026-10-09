import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    Principal, client_ip, get_db, get_principal, membership_or_404, require_permission,
)
from app.core.config import Settings, get_settings
from app.core.errors import ApiError, conflict, not_found
from app.core.responses import ok
from app.core.security import new_token, sha256_hex
from app.core.signing import derive_home_key
from app.db.types import utcnow
from app.models import Hub
from app.schemas.homes import HubIn
from app.services import audit
from app.services.device_view import hub_view
from app.services.devices import active_hub

router = APIRouter(tags=["hubs"])


@router.get("/homes/{home_id}/hubs")
def list_hubs(home_id: uuid.UUID, p: Principal = Depends(get_principal),
              db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    membership_or_404(db, home_id, p.user)
    hubs = db.scalars(select(Hub).where(Hub.home_id == home_id).order_by(Hub.created_at)).all()
    return ok([hub_view(h, settings) for h in hubs], {"total": len(hubs)})


@router.post("/homes/{home_id}/hubs", status_code=201)
def create_hub(home_id: uuid.UUID, body: HubIn, request: Request,
               p: Principal = Depends(get_principal), db: Session = Depends(get_db),
               settings: Settings = Depends(get_settings)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    if active_hub(db, home_id) is not None:
        raise conflict("This home already has an active hub; revoke it first")
    token = "hub_" + new_token(32)
    hub = Hub(id=uuid.uuid4(), home_id=home_id, name=body.name, token_hash=sha256_hex(token),
              status="active")
    db.add(hub)
    audit.record(db, "hub.created", actor_id=p.user.id, home_id=home_id, target_type="hub",
                 target_id=hub.id, ip=client_ip(request))
    db.commit()
    data = hub_view(hub, settings)
    # Shown exactly once. Neither value is stored in plain form.
    data["hub_token"] = token
    data["signing_key_hex"] = derive_home_key(settings.signing_master_key, home_id).hex()
    return ok(data, {"warning": "hub_token and signing_key_hex are shown only once"})


@router.post("/hubs/{hub_id}/revoke")
def revoke_hub(hub_id: uuid.UUID, request: Request, p: Principal = Depends(get_principal),
               db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    hub = db.get(Hub, hub_id)
    if hub is None:
        raise not_found("Hub")
    try:
        m = membership_or_404(db, hub.home_id, p.user)
    except ApiError:
        raise not_found("Hub")
    require_permission(m, "configure")
    if hub.status != "revoked":
        hub.status = "revoked"
        hub.revoked_at = utcnow()
        audit.record(db, "hub.revoked", actor_id=p.user.id, home_id=hub.home_id,
                     target_type="hub", target_id=hub.id, ip=client_ip(request))
        db.commit()
    return ok(hub_view(hub, settings))
