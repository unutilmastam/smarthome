import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Uuid, text
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
    revoked_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

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
