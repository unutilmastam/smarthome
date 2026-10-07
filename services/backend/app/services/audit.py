import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    action: str,
    *,
    actor_type: str = "user",
    actor_id: Optional[uuid.UUID] = None,
    home_id: Optional[uuid.UUID] = None,
    target_type: Optional[str] = None,
    target_id: Any = None,
    ip: Optional[str] = None,
    details: Optional[dict] = None,
) -> AuditLog:
    """Append an audit entry to the current transaction (caller commits)."""
    entry = AuditLog(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        home_id=home_id,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        ip=ip,
        details=details,
    )
    db.add(entry)
    return entry
