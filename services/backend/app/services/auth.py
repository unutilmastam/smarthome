"""Authentication: login, refresh rotation with reuse detection, logout, password, PIN."""

import uuid
from datetime import timedelta
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import auth_required, invalid_credentials, rate_limited
from app.core.security import (
    REFRESH_TOKEN_TTL,
    constant_time_equals,
    create_access_token,
    hash_secret,
    make_refresh_token,
    needs_rehash,
    parse_refresh_token,
    verify_secret,
)
from app.db.types import utcnow
from app.models import AuthSession, User
from app.services import audit, rate_limit

MAX_FAILED_LOGINS = 5
LOCK_DURATION = timedelta(minutes=5)
LOGIN_IP_LIMIT = 20
LOGIN_IP_WINDOW_S = 300


def _issue(settings: Settings, user: User, session: AuthSession) -> dict:
    refresh, refresh_hash = make_refresh_token(session.id)
    session.refresh_hash = refresh_hash
    session.last_used_at = utcnow()
    session.expires_at = utcnow() + REFRESH_TOKEN_TTL
    access, exp = create_access_token(user.id, session.id, settings.jwt_secret)
    return {
        "access_token": access,
        "access_expires_at": exp.isoformat().replace("+00:00", "Z"),
        "refresh_token": refresh,
        "token_type": "bearer",
    }


def user_out(user: User) -> dict:
    return {"id": str(user.id), "email": user.email, "name": user.name,
            "has_pin": user.pin_hash is not None}


def login(db: Session, settings: Settings, email: str, password: str,
          ip: Optional[str], user_agent: Optional[str]) -> dict:
    rate_limit.hit(db, f"login:ip:{ip or 'unknown'}", LOGIN_IP_LIMIT, LOGIN_IP_WINDOW_S)

    user = db.scalar(select(User).where(User.email == email))
    now = utcnow()

    if user is not None and user.locked_until is not None and user.locked_until > now:
        # Burn the same time as a real check.
        verify_secret(None, password)
        audit.record(db, "auth.login.locked", actor_id=user.id, ip=ip)
        db.commit()
        raise rate_limited(int((user.locked_until - now).total_seconds()))

    ok = verify_secret(user.password_hash if user else None, password)
    if not ok or user is None or not user.is_active:
        if user is not None:
            user.failed_logins += 1
            if user.failed_logins >= MAX_FAILED_LOGINS:
                user.locked_until = now + LOCK_DURATION
                user.failed_logins = 0
                audit.record(db, "auth.account.locked", actor_id=user.id, ip=ip)
        audit.record(
            db, "auth.login.failure", actor_id=user.id if user else None, ip=ip,
            details={"email_known": user is not None},
        )
        db.commit()
        raise invalid_credentials()

    user.failed_logins = 0
    user.locked_until = None
    if needs_rehash(user.password_hash):
        user.password_hash = hash_secret(password)
    session = AuthSession(
        id=uuid.uuid4(), user_id=user.id, refresh_hash="", expires_at=now + REFRESH_TOKEN_TTL,
        ip=ip, user_agent=(user_agent or "")[:255] or None,
    )
    db.add(session)
    tokens = _issue(settings, user, session)
    audit.record(db, "auth.login.success", actor_id=user.id, ip=ip,
                 target_type="session", target_id=session.id)
    db.commit()
    tokens["user"] = user_out(user)
    return tokens


def revoke_all(db: Session, user_id: uuid.UUID, reason: str,
               except_session: Optional[uuid.UUID] = None) -> int:
    stmt = (
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow(), revoke_reason=reason)
    )
    if except_session is not None:
        stmt = stmt.where(AuthSession.id != except_session)
    return db.execute(stmt).rowcount or 0


def refresh(db: Session, settings: Settings, token: str, ip: Optional[str]) -> dict:
    parsed = parse_refresh_token(token)
    if parsed is None:
        raise auth_required("Invalid refresh token")
    sid, presented_hash = parsed
    session = db.get(AuthSession, sid)
    if session is None:
        raise auth_required("Invalid refresh token")
    if session.revoked_at is not None or session.expires_at <= utcnow():
        raise auth_required("Session is no longer valid")
    if not constant_time_equals(session.refresh_hash, presented_hash):
        # An old (already rotated) or forged token for a live session: assume theft.
        n = revoke_all(db, session.user_id, "refresh_reuse")
        audit.record(db, "auth.refresh.reuse_detected", actor_id=session.user_id, ip=ip,
                     target_type="session", target_id=session.id,
                     details={"sessions_revoked": n})
        db.commit()
        raise auth_required("Refresh token reuse detected; all sessions revoked")
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise auth_required("Session is no longer valid")
    tokens = _issue(settings, user, session)
    db.commit()
    return tokens


def logout(db: Session, user: User, session: AuthSession, ip: Optional[str]) -> None:
    session.revoked_at = utcnow()
    session.revoke_reason = "logout"
    audit.record(db, "auth.logout", actor_id=user.id, ip=ip, target_type="session",
                 target_id=session.id)
    db.commit()


def logout_all(db: Session, user: User, ip: Optional[str]) -> int:
    n = revoke_all(db, user.id, "logout_all")
    audit.record(db, "auth.logout_all", actor_id=user.id, ip=ip, details={"sessions_revoked": n})
    db.commit()
    return n


def change_password(db: Session, user: User, session: AuthSession, current: str, new: str,
                    ip: Optional[str]) -> Tuple[int, None]:
    if not verify_secret(user.password_hash, current):
        audit.record(db, "auth.password.change_failed", actor_id=user.id, ip=ip)
        db.commit()
        raise invalid_credentials()
    user.password_hash = hash_secret(new)
    user.password_changed_at = utcnow()
    n = revoke_all(db, user.id, "password_changed", except_session=session.id)
    audit.record(db, "auth.password.changed", actor_id=user.id, ip=ip,
                 details={"other_sessions_revoked": n})
    db.commit()
    return n, None


def set_pin(db: Session, user: User, password: str, pin: str, ip: Optional[str]) -> None:
    if not verify_secret(user.password_hash, password):
        audit.record(db, "auth.pin.change_failed", actor_id=user.id, ip=ip)
        db.commit()
        raise invalid_credentials()
    user.pin_hash = hash_secret(pin)
    audit.record(db, "auth.pin.set", actor_id=user.id, ip=ip)
    db.commit()


def active_sessions(db: Session, user: User) -> list:
    return db.scalars(
        select(AuthSession).where(AuthSession.user_id == user.id,
                                  AuthSession.revoked_at.is_(None),
                                  AuthSession.expires_at > utcnow())
        .order_by(AuthSession.last_used_at.desc())).all()


def revoke_session(db: Session, user: User, session_id: uuid.UUID, ip: Optional[str]) -> bool:
    s = db.get(AuthSession, session_id)
    if s is None or s.user_id != user.id or s.revoked_at is not None:
        return False
    s.revoked_at = utcnow()
    s.revoke_reason = "revoked_by_user"
    audit.record(db, "auth.session.revoked", actor_id=user.id, ip=ip, target_type="session",
                 target_id=s.id)
    db.commit()
    return True
