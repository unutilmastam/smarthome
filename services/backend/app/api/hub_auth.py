from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.errors import auth_required
from app.core.security import sha256_hex
from app.db.types import utcnow
from app.models import Hub

LAST_SEEN_MIN_STEP = timedelta(seconds=5)


def get_hub(request: Request, db: Session = Depends(get_db)) -> Hub:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token.startswith("hub_"):
        raise auth_required("Hub token required")
    hub = db.scalar(select(Hub).where(Hub.token_hash == sha256_hex(token)))
    if hub is None or hub.status != "active":
        raise auth_required("Invalid or revoked hub token")
    now = utcnow()
    # Any authenticated call proves the hub is alive; avoid a write on every poll.
    if hub.last_seen is None or now - hub.last_seen >= LAST_SEEN_MIN_STEP:
        hub.last_seen = now
        db.commit()
    return hub
