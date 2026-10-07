import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON, BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPk
from app.db.types import UTCDateTime, utcnow

COMMAND_STATUSES = (
    "queued", "sent", "acked", "confirmed", "rejected", "failed", "expired", "timeout",
)
TERMINAL = frozenset({"confirmed", "rejected", "failed", "expired", "timeout"})
# Status may only move forward (a late ack must not undo "confirmed").
RANK = {"queued": 0, "sent": 1, "acked": 2}
RANK.update({s: 3 for s in TERMINAL})


class Command(UUIDPk, Base):
    __tablename__ = "commands"

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    hub_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("hubs.id", ondelete="SET NULL")
    )
    capability: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    risk: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    reason: Mapped[Optional[str]] = mapped_column(String(32))
    detail: Mapped[Optional[str]] = mapped_column(String(500))
    requested_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    requested_role: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    # Exactly what was signed and what the hub receives.
    envelope: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    acked_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    events: Mapped[list["CommandEvent"]] = relationship(
        order_by="CommandEvent.id", cascade="all, delete-orphan", passive_deletes=True,
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("requested_by", "idempotency_key", name="uq_commands_user_idem"),
        CheckConstraint(
            "status IN ('queued','sent','acked','confirmed','rejected','failed','expired','timeout')",
            name="status_valid",
        ),
        Index("ix_commands_home_status", "home_id", "status"),
        Index("ix_commands_device_created", "device_id", "created_at"),
    )


class CommandEvent(Base):
    __tablename__ = "command_events"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    command_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("commands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ts: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # backend | hub | system
    applied: Mapped[bool] = mapped_column(default=True, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(32))
    detail: Mapped[Optional[str]] = mapped_column(String(500))
