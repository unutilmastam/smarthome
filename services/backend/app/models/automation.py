"""Automations (ARCHITECTURE 11, ADR 0013). Stored and validated here, executed by the hub."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk
from app.db.types import UTCDateTime, utcnow


class Automation(UUIDPk, Timestamps, Base):
    __tablename__ = "automations"

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    definition: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Bumped on every change; the hub reports which version a run used.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"))


class AutomationRun(Base):
    """One run reported by the hub. id comes from the hub (idempotent retries)."""
    __tablename__ = "automation_runs"
    __table_args__ = (Index("ix_automation_runs_automation_ts", "automation_id", "ts"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True)
    automation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("automations.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    trigger: Mapped[str] = mapped_column(String(160), nullable=False)
    result: Mapped[str] = mapped_column(String(16), nullable=False)  # ok|partial|failed|skipped
    reason: Mapped[Optional[str]] = mapped_column(String(64))
    actions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
