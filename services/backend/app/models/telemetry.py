"""Aggregated telemetry (ARCHITECTURE 7). Raw readings stay on the hub (7 days)."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import UTCDateTime


class _Agg:
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    metric: Mapped[str] = mapped_column(String(64), primary_key=True)  # "<capability>.<attribute>"
    ts: Mapped[datetime] = mapped_column(UTCDateTime, primary_key=True)  # bucket start, UTC
    avg: Mapped[float] = mapped_column(Float, nullable=False)
    min: Mapped[float] = mapped_column(Float, nullable=False)
    max: Mapped[float] = mapped_column(Float, nullable=False)
    # Last value in the bucket (counters such as energy need it).
    last: Mapped[float] = mapped_column(Float, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)


class Telemetry1m(_Agg, Base):
    """1-minute buckets, kept 30 days."""
    __tablename__ = "telemetry_1m"


class Telemetry1h(_Agg, Base):
    """1-hour buckets, kept 2 years."""
    __tablename__ = "telemetry_1h"


class EnergyDaily(Base):
    """kWh per device per LOCAL day (home timezone). Kept forever."""
    __tablename__ = "energy_daily"

    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    kwh: Mapped[float] = mapped_column(Float, nullable=False)
    # Price at computation time; null when the home has no tariff (never invented).
    cost: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[Optional[str]] = mapped_column(String(3))
