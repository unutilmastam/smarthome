"""Homes, members, floors, rooms, audit."""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    Principal, client_ip, get_db, get_principal, membership_or_404, require_permission,
)
from app.core.errors import ApiError, conflict, forbidden, not_found, validation_error
from app.core.responses import ok
from app.core.security import hash_secret
from app.models import AuditLog, Floor, Home, HomeMember, Room, User
from app.schemas.common import Page
from app.schemas.homes import (
    FloorIn, FloorPatch, HomeIn, HomePatch, MemberIn, MemberPatch, RoomIn, RoomPatch,
)
from app.services import audit
from app.services.device_view import iso

router = APIRouter(tags=["homes"])


def home_out(h: Home, role: str) -> dict:
    return {"id": str(h.id), "name": h.name, "timezone": h.timezone,
            "latitude": h.latitude, "longitude": h.longitude, "my_role": role,
            "tariff_per_kwh": h.tariff_per_kwh, "currency": h.currency,
            "created_at": iso(h.created_at)}


def member_out(m: HomeMember, u: User) -> dict:
    return {"user_id": str(u.id), "email": u.email, "name": u.name, "role": m.role,
            "created_at": iso(m.created_at)}


def floor_out(f: Floor) -> dict:
    return {"id": str(f.id), "home_id": str(f.home_id), "name": f.name, "level": f.level}


def room_out(r: Room) -> dict:
    return {"id": str(r.id), "home_id": str(r.home_id), "name": r.name, "type": r.type,
            "floor_id": str(r.floor_id) if r.floor_id else None}


# ---- homes ---------------------------------------------------------------------

@router.get("/homes")
def list_homes(page: Page = Depends(), p: Principal = Depends(get_principal),
               db: Session = Depends(get_db)):
    base = (select(Home, HomeMember.role).join(HomeMember, HomeMember.home_id == Home.id)
            .where(HomeMember.user_id == p.user.id))
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    rows = db.execute(base.order_by(Home.created_at).limit(page.limit).offset(page.offset)).all()
    return ok([home_out(h, r) for h, r in rows], page.meta(total))


@router.post("/homes", status_code=201)
def create_home(body: HomeIn, request: Request, p: Principal = Depends(get_principal),
                db: Session = Depends(get_db)):
    home = Home(id=uuid.uuid4(), **body.model_dump())
    db.add(home)
    db.flush()
    db.add(HomeMember(home_id=home.id, user_id=p.user.id, role="owner"))
    audit.record(db, "home.created", actor_id=p.user.id, home_id=home.id,
                 target_type="home", target_id=home.id, ip=client_ip(request))
    db.commit()
    return ok(home_out(home, "owner"))


@router.get("/homes/{home_id}")
def get_home(home_id: uuid.UUID, p: Principal = Depends(get_principal),
             db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    return ok(home_out(db.get(Home, home_id), m.role))


@router.patch("/homes/{home_id}")
def patch_home(home_id: uuid.UUID, body: HomePatch, request: Request,
               p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    home = db.get(Home, home_id)
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is None:
        raise validation_error("name cannot be null")
    if "currency" in changes and changes["currency"] is None:
        raise validation_error("currency cannot be null")
    if "timezone" in changes and changes["timezone"] is None:
        raise validation_error("timezone cannot be null")
    lat = changes.get("latitude", home.latitude)
    lon = changes.get("longitude", home.longitude)
    if (lat is None) != (lon is None):
        raise validation_error("latitude and longitude must be set together")
    for k, v in changes.items():
        setattr(home, k, v)
    audit.record(db, "home.updated", actor_id=p.user.id, home_id=home_id, target_type="home",
                 target_id=home_id, ip=client_ip(request), details={"fields": sorted(changes)})
    db.commit()
    return ok(home_out(home, m.role))


# ---- members -------------------------------------------------------------------

@router.get("/homes/{home_id}/members")
def list_members(home_id: uuid.UUID, page: Page = Depends(),
                 p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    base = (select(HomeMember, User).join(User, User.id == HomeMember.user_id)
            .where(HomeMember.home_id == home_id))
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    rows = db.execute(base.order_by(HomeMember.created_at).limit(page.limit)
                      .offset(page.offset)).all()
    return ok([member_out(mm, u) for mm, u in rows], page.meta(total))


@router.post("/homes/{home_id}/members", status_code=201)
def add_member(home_id: uuid.UUID, body: MemberIn, request: Request,
               p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "manage_users")
    user = db.scalar(select(User).where(User.email == body.email))
    created = False
    if user is None:
        if not body.initial_password or not body.name:
            raise validation_error("New user requires name and initial_password")
        user = User(id=uuid.uuid4(), email=body.email, name=body.name,
                    password_hash=hash_secret(body.initial_password))
        db.add(user)
        db.flush()
        created = True
    elif body.initial_password:
        raise validation_error("User already exists; initial_password must not be sent")
    exists = db.scalar(select(HomeMember).where(HomeMember.home_id == home_id,
                                                HomeMember.user_id == user.id))
    if exists:
        raise conflict("User is already a member of this home")
    member = HomeMember(home_id=home_id, user_id=user.id, role=body.role)
    db.add(member)
    audit.record(db, "member.added", actor_id=p.user.id, home_id=home_id, target_type="user",
                 target_id=user.id, ip=client_ip(request),
                 details={"role": body.role, "user_created": created})
    db.commit()
    return ok(member_out(member, user))


def _member_or_404(db: Session, home_id: uuid.UUID, user_id: uuid.UUID) -> HomeMember:
    mm = db.scalar(select(HomeMember).where(HomeMember.home_id == home_id,
                                            HomeMember.user_id == user_id))
    if mm is None:
        raise not_found("Member")
    return mm


@router.patch("/homes/{home_id}/members/{user_id}")
def change_member_role(home_id: uuid.UUID, user_id: uuid.UUID, body: MemberPatch,
                       request: Request, p: Principal = Depends(get_principal),
                       db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "manage_users")
    mm = _member_or_404(db, home_id, user_id)
    if mm.role == "owner":
        raise forbidden("The owner's role cannot be changed")
    old = mm.role
    mm.role = body.role
    audit.record(db, "member.role_changed", actor_id=p.user.id, home_id=home_id,
                 target_type="user", target_id=user_id, ip=client_ip(request),
                 details={"from": old, "to": body.role})
    db.commit()
    return ok(member_out(mm, db.get(User, user_id)))


@router.delete("/homes/{home_id}/members/{user_id}")
def remove_member(home_id: uuid.UUID, user_id: uuid.UUID, request: Request,
                  p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "manage_users")
    mm = _member_or_404(db, home_id, user_id)
    if mm.role == "owner":
        raise forbidden("The owner cannot be removed")
    db.delete(mm)
    audit.record(db, "member.removed", actor_id=p.user.id, home_id=home_id, target_type="user",
                 target_id=user_id, ip=client_ip(request), details={"role": mm.role})
    db.commit()
    return ok({"removed": True})


# ---- floors --------------------------------------------------------------------

@router.get("/homes/{home_id}/floors")
def list_floors(home_id: uuid.UUID, p: Principal = Depends(get_principal),
                db: Session = Depends(get_db)):
    membership_or_404(db, home_id, p.user)
    rows = db.scalars(select(Floor).where(Floor.home_id == home_id)
                      .order_by(Floor.level, Floor.name)).all()
    return ok([floor_out(f) for f in rows], {"total": len(rows)})


@router.post("/homes/{home_id}/floors", status_code=201)
def create_floor(home_id: uuid.UUID, body: FloorIn, request: Request,
                 p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    f = Floor(id=uuid.uuid4(), home_id=home_id, **body.model_dump())
    db.add(f)
    audit.record(db, "floor.created", actor_id=p.user.id, home_id=home_id, target_type="floor",
                 target_id=f.id, ip=client_ip(request))
    db.commit()
    return ok(floor_out(f))


def _floor_for(db: Session, floor_id: uuid.UUID, user: User):
    f = db.get(Floor, floor_id)
    if f is None:
        raise not_found("Floor")
    try:
        m = membership_or_404(db, f.home_id, user)
    except ApiError:
        raise not_found("Floor")
    return f, m


@router.patch("/floors/{floor_id}")
def patch_floor(floor_id: uuid.UUID, body: FloorPatch, request: Request,
                p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    f, m = _floor_for(db, floor_id, p.user)
    require_permission(m, "configure")
    changes = body.model_dump(exclude_unset=True)
    if any(v is None for v in changes.values()):
        raise validation_error("Fields cannot be null")
    for k, v in changes.items():
        setattr(f, k, v)
    audit.record(db, "floor.updated", actor_id=p.user.id, home_id=f.home_id, target_type="floor",
                 target_id=f.id, ip=client_ip(request))
    db.commit()
    return ok(floor_out(f))


@router.delete("/floors/{floor_id}")
def delete_floor(floor_id: uuid.UUID, request: Request, p: Principal = Depends(get_principal),
                 db: Session = Depends(get_db)):
    f, m = _floor_for(db, floor_id, p.user)
    require_permission(m, "configure")
    db.delete(f)
    audit.record(db, "floor.deleted", actor_id=p.user.id, home_id=f.home_id, target_type="floor",
                 target_id=f.id, ip=client_ip(request), details={"name": f.name})
    db.commit()
    return ok({"deleted": True})


# ---- rooms ---------------------------------------------------------------------

def _check_floor(db: Session, home_id: uuid.UUID, floor_id) -> None:
    if floor_id is None:
        return
    f = db.get(Floor, floor_id)
    if f is None or f.home_id != home_id:
        raise validation_error("floor_id does not belong to this home")


@router.get("/homes/{home_id}/rooms")
def list_rooms(home_id: uuid.UUID, p: Principal = Depends(get_principal),
               db: Session = Depends(get_db)):
    membership_or_404(db, home_id, p.user)
    rows = db.scalars(select(Room).where(Room.home_id == home_id).order_by(Room.name)).all()
    return ok([room_out(r) for r in rows], {"total": len(rows)})


@router.post("/homes/{home_id}/rooms", status_code=201)
def create_room(home_id: uuid.UUID, body: RoomIn, request: Request,
                p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "configure")
    _check_floor(db, home_id, body.floor_id)
    r = Room(id=uuid.uuid4(), home_id=home_id, **body.model_dump())
    db.add(r)
    audit.record(db, "room.created", actor_id=p.user.id, home_id=home_id, target_type="room",
                 target_id=r.id, ip=client_ip(request))
    db.commit()
    return ok(room_out(r))


def _room_for(db: Session, room_id: uuid.UUID, user: User):
    r = db.get(Room, room_id)
    if r is None:
        raise not_found("Room")
    try:
        m = membership_or_404(db, r.home_id, user)
    except ApiError:
        raise not_found("Room")
    return r, m


@router.get("/rooms/{room_id}")
def get_room(room_id: uuid.UUID, p: Principal = Depends(get_principal),
             db: Session = Depends(get_db)):
    r, _ = _room_for(db, room_id, p.user)
    return ok(room_out(r))


@router.patch("/rooms/{room_id}")
def patch_room(room_id: uuid.UUID, body: RoomPatch, request: Request,
               p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    r, m = _room_for(db, room_id, p.user)
    require_permission(m, "configure")
    changes = body.model_dump(exclude_unset=True)
    if changes.get("name", "") is None or ("type" in changes and changes["type"] is None):
        raise validation_error("Fields cannot be null")
    if "floor_id" in changes:
        _check_floor(db, r.home_id, changes["floor_id"])
    for k, v in changes.items():
        setattr(r, k, v)
    audit.record(db, "room.updated", actor_id=p.user.id, home_id=r.home_id, target_type="room",
                 target_id=r.id, ip=client_ip(request))
    db.commit()
    return ok(room_out(r))


@router.delete("/rooms/{room_id}")
def delete_room(room_id: uuid.UUID, request: Request, p: Principal = Depends(get_principal),
                db: Session = Depends(get_db)):
    r, m = _room_for(db, room_id, p.user)
    require_permission(m, "configure")
    db.delete(r)
    audit.record(db, "room.deleted", actor_id=p.user.id, home_id=r.home_id, target_type="room",
                 target_id=r.id, ip=client_ip(request), details={"name": r.name})
    db.commit()
    return ok({"deleted": True})


# ---- audit (read only) ------------------------------------------------------------

@router.get("/homes/{home_id}/audit")
def list_audit(home_id: uuid.UUID, page: Page = Depends(),
               p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    require_permission(m, "view_audit")
    base = select(AuditLog).where(AuditLog.home_id == home_id)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    rows = db.scalars(base.order_by(AuditLog.ts.desc(), AuditLog.id.desc())
                      .limit(page.limit).offset(page.offset)).all()
    return ok([
        {"id": a.id, "ts": iso(a.ts), "actor_type": a.actor_type,
         "actor_id": str(a.actor_id) if a.actor_id else None, "action": a.action,
         "target_type": a.target_type, "target_id": a.target_id, "ip": a.ip,
         "details": a.details}
        for a in rows
    ], page.meta(total))
