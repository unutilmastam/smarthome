import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk
from app.db.types import UTCDateTime


class Integration(UUIDPk, Timestamps, Base):
    """A home's link to another ecosystem in the cloud (ADR 0016), e.g. Yandex Alisa.
    The token is sealed (app.core.secretbox) with the integration id as associated data."""

    __tablename__ = "integrations"

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    secret_enc: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    error: Mapped[Optional[str]] = mapped_column(String(300))
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    # Not secret: scenario list, devices Yandex has that we cannot show.
    data: Mapped[Optional[dict]] = mapped_column(JSON)

    __table_args__ = (
        UniqueConstraint("home_id", "kind", name="uq_integrations_home_kind"),
        CheckConstraint("kind IN ('yandex')", name="kind_valid"),
        CheckConstraint("status IN ('pending','ok','error')", name="status_valid"),
    )
