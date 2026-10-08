import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk
from app.db.types import UTCDateTime, utcnow


class Device(UUIDPk, Timestamps, Base):
    __tablename__ = "devices"

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    room_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("rooms.id", ondelete="SET NULL"), index=True
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    adapter: Mapped[str] = mapped_column(String(40), nullable=False)
    protocol: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(120))
    icon: Mapped[Optional[str]] = mapped_column(String(32))
    fail_safe_state: Mapped[Optional[dict]] = mapped_column(JSON)
    # ["capability.attribute", ...] the hardware cannot measure -> shown as not_supported.
    unsupported: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    availability: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    availability_ts: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    # ADR 0014 watchdog: set when "device offline" was announced, cleared when it is back.
    offline_notified_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    capabilities: Mapped[list["DeviceCapability"]] = relationship(
        back_populates="device",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DeviceCapability.capability",
        lazy="selectin",
    )
    states: Mapped[list["DeviceState"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("home_id", "key", name="uq_devices_home_key"),
        CheckConstraint(
            "availability IN ('online','offline','unknown')", name="availability_valid"
        ),
    )


class DeviceCapability(Base):
    __tablename__ = "device_capabilities"

    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    capability: Mapped[str] = mapped_column(String(40), primary_key=True)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    device: Mapped[Device] = relationship(back_populates="capabilities")


class DeviceState(Base):
    """Current value of one attribute (ARCHITECTURE 4.2). History lives elsewhere."""

    __tablename__ = "device_state"

    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True
    )
    capability: Mapped[str] = mapped_column(String(40), primary_key=True)
    attribute: Mapped[str] = mapped_column(String(40), primary_key=True)
    value_json: Mapped[Any] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    quality: Mapped[str] = mapped_column(String(16), nullable=False)
    ts: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint("source IN ('reported','assumed','computed')", name="source_valid"),
        CheckConstraint(
            "quality IN ('good','stale','unknown','not_supported')", name="quality_valid"
        ),
    )


class Camera(UUIDPk, Timestamps, Base):
    """Camera METADATA only. Video never touches the cloud (ADR 0006)."""

    __tablename__ = "cameras"

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hub_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("hubs.id", ondelete="SET NULL")
    )
    room_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("rooms.id", ondelete="SET NULL")
    )
    # Status (stream/recording/disk) lives on a linked device with the "camera" capability.
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("devices.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    frigate_name: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (UniqueConstraint("home_id", "frigate_name", name="uq_cameras_home_frigate"),)
