import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk
from app.db.types import UTCDateTime


class Hub(UUIDPk, Timestamps, Base):
    __tablename__ = "hubs"

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # SHA-256 of hub_token (hex). The token itself is shown once at creation.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    last_seen: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    version: Mapped[Optional[str]] = mapped_column(String(40))
    # Reported by the hub itself (heartbeat). Used only to build local/Tailscale links;
    # the cloud never connects to these addresses.
    tailnet_host: Mapped[Optional[str]] = mapped_column(String(253))
    lan_host: Mapped[Optional[str]] = mapped_column(String(253))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    # ADR 0014 watchdog: set when "hub offline" was announced, cleared when it is back.
    offline_notified_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    # Faza 14: last health the hub reported (broker, disks, outbox) and the watchdog's
    # bookkeeping of active health alerts {kind: {"since": iso, "notified": bool}}.
    health: Mapped[Optional[dict]] = mapped_column(JSON)
    health_alerts: Mapped[Optional[dict]] = mapped_column(JSON)

    __table_args__ = (
        CheckConstraint("status IN ('active','revoked')", name="status_valid"),
        Index(
            "uq_hubs_one_active_per_home",
            "home_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )
