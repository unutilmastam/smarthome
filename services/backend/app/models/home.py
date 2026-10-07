import uuid
from typing import Optional

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk

ROLES = ("owner", "admin", "family", "guest", "viewer")


class Home(UUIDPk, Timestamps, Base):
    __tablename__ = "homes"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tashkent", nullable=False)
    # Unknown until the owner sets them (needed for sunrise/sunset automations).
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    # Electricity price per kWh. Unknown until the owner sets it: costs stay null.
    tariff_per_kwh: Mapped[Optional[float]] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="UZS", server_default="UZS",
                                          nullable=False)


class HomeMember(Timestamps, Base):
    __tablename__ = "home_members"

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "role IN ('owner','admin','family','guest','viewer')", name="role_valid"
        ),
        # Exactly one owner per home.
        Index(
            "uq_home_members_one_owner",
            "home_id",
            unique=True,
            postgresql_where=text("role = 'owner'"),
            sqlite_where=text("role = 'owner'"),
        ),
    )


class Floor(UUIDPk, Timestamps, Base):
    __tablename__ = "floors"

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Room(UUIDPk, Timestamps, Base):
    __tablename__ = "rooms"

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    floor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("floors.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    type: Mapped[str] = mapped_column(String(16), default="indoor", nullable=False)
    icon: Mapped[Optional[str]] = mapped_column(String(32))

    __table_args__ = (CheckConstraint("type IN ('indoor','outdoor')", name="type_valid"),)
