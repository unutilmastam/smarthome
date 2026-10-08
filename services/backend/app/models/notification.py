"""Notifications (ADR 0014): what a person must know, and how it reached them.

notifications            one row per thing that happened (event, automation notify, hub/device
                         offline, test); acked by a person. Kept 180 days.
notification_deliveries  one row per recipient x channel target; the cron / request that sends
                         it first claims it (pending -> sending) so nothing is sent twice.
telegram_links           private Telegram chat <-> user (after /start CODE).
telegram_link_codes      one-time link codes (SHA-256 only), 10 minutes.
push_subscriptions       Web Push endpoints of a user's browsers / installed PWAs.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPk
from app.db.types import UTCDateTime, utcnow

SEVERITIES = ("info", "warning", "critical")
SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}


class Notification(UUIDPk, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_home_created", "home_id", "created_at"),
        Index("uq_notifications_home_dedupe", "home_id", "dedupe_key", unique=True),
    )

    home_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("homes.id", ondelete="CASCADE"), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)   # event|automation|hub|device|test
    kind: Mapped[str] = mapped_column(String(64), nullable=False)     # e.g. alarm.triggered, hub.offline
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # When it happened (event ts), not when the cloud heard about it.
    ts: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    acked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    acked_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    reminded_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)


class NotificationDelivery(UUIDPk, Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (Index("ix_notification_deliveries_status_next", "status", "next_attempt_at"),)

    notification_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False)   # telegram | push
    target: Mapped[str] = mapped_column(String(64), nullable=False)    # chat id | subscription id
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    # pending | sending | sent | failed | gone (target no longer exists)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    sent_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
    error: Mapped[Optional[str]] = mapped_column(String(200))
    reminder: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)


class TelegramLink(UUIDPk, Base):
    __tablename__ = "telegram_links"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)


class TelegramLinkCode(Base):
    __tablename__ = "telegram_link_codes"

    code_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)


class PushSubscription(UUIDPk, Base):
    __tablename__ = "push_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(128), nullable=False)
    auth: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
