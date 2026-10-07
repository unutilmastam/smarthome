"""Command lifecycle: create (validate + sign), hub claim, acks, expiry.

queued -> sent -> acked -> confirmed
   \\-> expired   \\-> rejected / failed / timeout
Status only moves forward; terminal states are final.
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.contracts import Contracts
from app.core.errors import ApiError, conflict, forbidden, validation_error
from app.core.permissions import has_permission
from app.core.security import verify_secret
from app.core.signing import derive_home_key, sign
from app.db.types import utcnow
from app.models import Command, CommandEvent, Device, HomeMember, Hub, User
from app.models.command import RANK, TERMINAL
from app.services import audit, rate_limit
from app.services.device_view import hub_is_online, iso
from app.services.devices import active_hub

PIN_FAIL_LIMIT = 5
PIN_FAIL_WINDOW_S = 900


def ts_ms(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def command_view(c: Command, with_events: bool = True) -> dict:
    out = {
        "id": str(c.id),
        "home_id": str(c.home_id),
        "device_id": str(c.device_id),
        "capability": c.capability,
        "action": c.action,
        "params": c.params,
        "risk": c.risk,
        "status": c.status,
        "reason": c.reason,
        "detail": c.detail,
        "requested_by": str(c.requested_by),
        "idempotency_key": c.idempotency_key,
        "created_at": iso(c.created_at),
        "expires_at": iso(c.expires_at),
        "sent_at": iso(c.sent_at),
        "acked_at": iso(c.acked_at),
        "finished_at": iso(c.finished_at),
    }
    if with_events:
        out["events"] = [
            {"ts": iso(e.ts), "status": e.status, "source": e.source, "applied": e.applied,
             "reason": e.reason, "detail": e.detail}
            for e in c.events
        ]
    return out


def _event(db: Session, c: Command, status: str, source: str, applied: bool = True,
           reason: Optional[str] = None, detail: Optional[str] = None,
           ts: Optional[datetime] = None) -> None:
    ev = CommandEvent(command_id=c.id, status=status, source=source, applied=applied,
                      reason=reason, detail=(detail or None) and detail[:500], ts=ts or utcnow())
    c.events.append(ev)
    db.add(ev)


def transition(db: Session, c: Command, new: str, source: str, reason: Optional[str] = None,
               detail: Optional[str] = None, now: Optional[datetime] = None) -> bool:
    """Apply a status change if it moves forward. Returns True if applied."""
    now = now or utcnow()
    if c.status in TERMINAL or RANK[new] <= RANK[c.status]:
        _event(db, c, new, source, applied=False, reason=reason,
               detail=f"ignored: command already {c.status}" + (f"; {detail}" if detail else ""))
        return False
    c.status = new
    if new == "sent":
        c.sent_at = now
    elif new == "acked":
        c.acked_at = now
    if new in TERMINAL:
        c.finished_at = now
        c.reason = reason
        c.detail = detail[:500] if detail else None
    _event(db, c, new, source, reason=reason, detail=detail)
    return True


# ---- creation -----------------------------------------------------------------------

def _reject(code: str, status: int, message: str, details=None) -> ApiError:
    return ApiError(status, code, message, details)


def create_command(db: Session, settings: Settings, contracts: Contracts, user: User,
                   body, ip: Optional[str]) -> tuple:
    """Returns (command, created: bool)."""
    rate_limit.hit(db, f"cmd:user:{user.id}", settings.command_rate_limit_per_min, 60)

    existing = db.scalar(select(Command).where(Command.requested_by == user.id,
                                               Command.idempotency_key == body.idempotency_key))
    if existing is not None:
        same = (existing.device_id == body.device_id and existing.capability == body.capability
                and existing.action == body.action and existing.params == body.params)
        if not same:
            raise conflict("idempotency_key was already used for a different command")
        return existing, False

    device = db.get(Device, body.device_id)
    member = None
    if device is not None:
        member = db.scalar(select(HomeMember).where(HomeMember.home_id == device.home_id,
                                                    HomeMember.user_id == user.id))
    if device is None or member is None:
        raise ApiError(404, "NOT_FOUND", "Device not found")

    caps = {c.capability: c.config_json or {} for c in device.capabilities}
    if body.capability not in caps:
        raise _reject("CAPABILITY_NOT_SUPPORTED", 422,
                      f"Device has no capability '{body.capability}'")
    spec = contracts.capability(body.capability)
    if body.action not in spec["actions"]:
        raise validation_error(f"Capability '{body.capability}' has no action '{body.action}'")
    errors = sorted(e.message for e in
                    contracts.params_validator(body.capability, body.action)
                    .iter_errors(body.params))
    if errors:
        raise validation_error("Invalid params", errors)
    max_rt = caps[body.capability].get("max_runtime_s")
    if max_rt and isinstance(body.params.get("duration_s"), int) \
            and body.params["duration_s"] > max_rt:
        raise validation_error(f"duration_s exceeds this device's max_runtime_s ({max_rt})")

    if not has_permission(member.role, spec["permission"]):
        raise forbidden(f"Role '{member.role}' lacks permission '{spec['permission']}'")

    if spec["risk"] == "high":
        if not body.confirm_pin:
            raise _reject("PIN_REQUIRED", 403, "This action requires PIN confirmation")
        if user.pin_hash is None:
            raise _reject("PIN_REQUIRED", 403, "Set a PIN before using high-risk actions")
        pin_key = f"pin:user:{user.id}"
        rate_limit.ensure_below(db, pin_key, PIN_FAIL_LIMIT, PIN_FAIL_WINDOW_S)
        if not verify_secret(user.pin_hash, body.confirm_pin):
            audit.record(db, "command.pin_invalid", actor_id=user.id, home_id=device.home_id,
                         target_type="device", target_id=device.id, ip=ip)
            db.commit()
            try:
                rate_limit.hit(db, pin_key, PIN_FAIL_LIMIT, PIN_FAIL_WINDOW_S)
            except ApiError:
                pass  # the next attempt is refused by ensure_below
            raise _reject("PIN_INVALID", 403, "Wrong PIN")

    if not device.enabled:
        raise _reject("DEVICE_DISABLED", 409, "Device is disabled")
    hub = active_hub(db, device.home_id)
    if not hub_is_online(hub, settings):
        raise _reject("HUB_UNREACHABLE", 503, "Home hub is not reachable; command not created")
    if device.availability == "offline":
        raise _reject("DEVICE_OFFLINE", 409, "Device is offline")

    now = utcnow()
    ttl = settings.command_ttl_high_risk_s if spec["risk"] == "high" else settings.command_ttl_s
    expires = now + timedelta(seconds=ttl)
    cid = uuid.uuid4()
    payload = {
        "command_id": str(cid),
        "device_id": str(device.id),
        "device_key": device.key,
        "capability": body.capability,
        "action": body.action,
        "params": body.params,
        "issued_at": ts_ms(now),
        "expires_at": ts_ms(expires),
        "issued_by": {"user_id": str(user.id), "role": member.role},
    }
    key = derive_home_key(settings.signing_master_key, device.home_id)
    envelope = {"schema": 1, "payload": payload, "signature": sign(key, payload)}
    cmd = Command(
        id=cid, home_id=device.home_id, device_id=device.id, hub_id=hub.id,
        capability=body.capability, action=body.action, params=body.params, risk=spec["risk"],
        status="queued", requested_by=user.id, requested_role=member.role,
        idempotency_key=body.idempotency_key, envelope=envelope, created_at=now,
        expires_at=expires,
    )
    db.add(cmd)
    _event(db, cmd, "queued", "backend", detail="signed")
    audit.record(db, "command.created", actor_id=user.id, home_id=device.home_id,
                 target_type="command", target_id=cid, ip=ip,
                 details={"device_key": device.key, "capability": body.capability,
                          "action": body.action, "risk": spec["risk"]})
    try:
        db.commit()
    except IntegrityError:
        # Same idempotency key raced in another request.
        db.rollback()
        existing = db.scalar(select(Command).where(
            Command.requested_by == user.id, Command.idempotency_key == body.idempotency_key))
        if existing is None:
            raise
        return existing, False
    return cmd, True


# ---- expiry ---------------------------------------------------------------------------

def expire_due(db: Session, settings: Settings, contracts: Contracts,
               home_id: Optional[uuid.UUID] = None, now: Optional[datetime] = None) -> int:
    """queued past expires_at -> expired; sent w/o ack -> timeout; acked w/o confirm -> timeout."""
    now = now or utcnow()
    q = select(Command).where(Command.status.in_(("queued", "sent", "acked")))
    if home_id is not None:
        q = q.where(Command.home_id == home_id)
    q = q.where(or_(
        (Command.status == "queued") & (Command.expires_at <= now),
        (Command.status == "sent")
        & (Command.expires_at <= now - timedelta(seconds=settings.command_ack_grace_s)),
        Command.status == "acked",
    ))
    n = 0
    for c in db.scalars(q).all():
        if c.status == "queued":
            n += transition(db, c, "expired", "system", reason="expired",
                            detail="not picked up by hub before expires_at", now=now)
        elif c.status == "sent":
            n += transition(db, c, "timeout", "system", reason="no_ack",
                            detail="hub received the command but sent no ack", now=now)
        elif c.status == "acked":
            if "confirm_attribute" not in contracts.capability(c.capability):
                continue  # acked is the last state for capabilities without feedback
            limit = settings.command_confirm_timeout_s + settings.command_ack_grace_s
            if c.acked_at and c.acked_at <= now - timedelta(seconds=limit):
                n += transition(db, c, "timeout", "system", reason="no_feedback",
                                detail="no confirmation from the device state", now=now)
    if n:
        db.commit()
    return n


# ---- hub side ---------------------------------------------------------------------------

def claim_for_hub(db: Session, hub: Hub, limit: int = 20) -> List[Command]:
    """Atomically hand each queued, unexpired command to the hub exactly once."""
    now = utcnow()
    candidates = db.scalars(
        select(Command.id).where(Command.home_id == hub.home_id, Command.status == "queued",
                                 Command.expires_at > now)
        .order_by(Command.created_at).limit(limit)
    ).all()
    claimed = []
    for cid in candidates:
        res = db.execute(
            update(Command).where(Command.id == cid, Command.status == "queued")
            .values(status="sent", sent_at=now, hub_id=hub.id)
            .execution_options(synchronize_session=False)
        )
        if res.rowcount == 1:
            claimed.append(cid)
    if not claimed:
        db.commit()
        return []
    cmds = db.scalars(select(Command).where(Command.id.in_(claimed))
                      .order_by(Command.created_at)).all()
    for c in cmds:
        db.refresh(c)
        _event(db, c, "sent", "backend", detail=f"delivered to hub {hub.id}", ts=now)
    db.commit()
    return cmds


ACK_TO_STATUS = {"acked": "acked", "confirmed": "confirmed", "rejected": "rejected",
                 "failed": "failed"}


def apply_ack(db: Session, hub: Hub, ack: dict) -> dict:
    try:
        cid = uuid.UUID(ack["command_id"])
    except ValueError:
        return {"command_id": ack.get("command_id"), "result": "invalid"}
    c = db.get(Command, cid)
    if c is None or c.home_id != hub.home_id:
        # Another home's hub must not learn or touch foreign commands.
        return {"command_id": ack["command_id"], "result": "not_found"}
    if c.status == "queued":
        _event(db, c, ACK_TO_STATUS[ack["status"]], "hub", applied=False,
               reason=ack.get("reason"), detail="ignored: command was never delivered")
        return {"command_id": str(c.id), "result": "ignored", "status": c.status}
    applied = transition(db, c, ACK_TO_STATUS[ack["status"]], "hub", reason=ack.get("reason"),
                         detail=ack.get("detail"))
    return {"command_id": str(c.id), "result": "applied" if applied else "ignored",
            "status": c.status}
