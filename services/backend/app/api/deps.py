import uuid
from dataclasses import dataclass
from typing import Iterator, Optional

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.contracts import Contracts, load_contracts
from app.core.errors import auth_required, forbidden, not_found
from app.core.permissions import has_permission
from app.core.security import decode_access_token
from app.db.types import utcnow
from app.models import AuthSession, HomeMember, User


def get_db(request: Request) -> Iterator[Session]:
    yield from request.app.state.db.session()


def get_contracts(settings: Settings = Depends(get_settings)) -> Contracts:
    return load_contracts(str(settings.contracts_dir))


def client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@dataclass
class Principal:
    user: User
    session: AuthSession


def _bearer(request: Request) -> Optional[str]:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def get_principal(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Principal:
    token = _bearer(request)
    if not token:
        raise auth_required()
    payload = decode_access_token(token, settings.jwt_secret)
    if payload is None:
        raise auth_required("Invalid or expired access token")
    try:
        sid = uuid.UUID(payload["sid"])
        uid = uuid.UUID(payload["sub"])
    except (ValueError, KeyError):
        raise auth_required("Invalid access token")
    session = db.get(AuthSession, sid)
    if (
        session is None
        or session.user_id != uid
        or session.revoked_at is not None
        or session.expires_at <= utcnow()
    ):
        raise auth_required("Session is no longer valid")
    user = db.get(User, uid)
    if user is None or not user.is_active:
        raise auth_required("Session is no longer valid")
    return Principal(user=user, session=session)


def membership_or_404(db: Session, home_id: uuid.UUID, user: User) -> HomeMember:
    """Non-members get 404 (not 403) so IDs cannot be probed."""
    member = db.scalar(
        select(HomeMember).where(HomeMember.home_id == home_id, HomeMember.user_id == user.id)
    )
    if member is None:
        raise not_found("Home")
    return member


def require_permission(member: HomeMember, permission: str) -> None:
    if not has_permission(member.role, permission):
        raise forbidden(f"Role '{member.role}' lacks permission '{permission}'")
