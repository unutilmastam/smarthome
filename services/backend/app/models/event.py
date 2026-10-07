"""Events from devices and the hub (ADR 0012): gate left open, alarm triggered, ...

The id is assigned by the hub gateway, so a retried batch is idempotent.
Kept 180 days (retention job). Delivery to Telegram/Push is Phase 13.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime, utcnow


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_home_ts", "home_id", "ts"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False)
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="SET NULL"), index=True)
    device_key: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(64), nullable=False)       # "<capability>.<name>"
    severity: Mapped[str] = mapped_column(String(16), nullable=False)   # info | warning | critical
    ts: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
