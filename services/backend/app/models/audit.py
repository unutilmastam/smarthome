import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, BigInteger, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, utcnow


class AuditLog(Base):
    """Append-only. No API updates or deletes audit rows."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    home_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="SET NULL")
    )
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)  # user | hub | system
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(32))
    target_id: Mapped[Optional[str]] = mapped_column(String(64))
    ip: Mapped[Optional[str]] = mapped_column(String(64))
    details: Mapped[Optional[dict]] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_audit_log_home_ts", "home_id", "ts"),
        Index("ix_audit_log_actor_ts", "actor_id", "ts"),
    )
