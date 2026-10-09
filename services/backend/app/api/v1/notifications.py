"""Notifications (ADR 0014): list + ack, channel setup (Telegram link, Web Push), prefs,
test message, Telegram webhook."""

import hmac
import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db, get_principal, membership_or_404
from app.core.config import Settings, get_settings
from app.core.errors import ApiError, forbidden, not_found, validation_error
from app.core.responses import ok
from app.models import (
    HomeMember, Notification, NotificationDelivery, PushSubscription, TelegramLink,
)
from app.schemas.common import Model
from app.services import channels, notifications as svc, webpush
from app.services.device_view import iso

router = APIRouter(tags=["notifications"])

# Push endpoints are URLs the server will POST to: only real push services (no SSRF).
PUSH_HOST_SUFFIXES = (".googleapis.com", ".mozilla.com", ".push.apple.com", ".notify.windows.com")


def not_configured(what: str) -> ApiError:
    return ApiError(503, "NOT_CONFIGURED", f"{what} is not configured on the server")


def _get(db: Session, nid: uuid.UUID) -> Notification:
    n = db.get(Notification, nid)
    if n is None:
        raise not_found("Notification")
    return n


@router.get("/homes/{home_id}/notifications")
def list_notifications(home_id: uuid.UUID, limit: int = Query(50, ge=1, le=200),
                       before: Optional[datetime] = Query(None),
                       unacked: bool = Query(False),
                       p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    membership_or_404(db, home_id, p.user)
    q = select(Notification).where(Notification.home_id == home_id)
    if before is not None:
        q = q.where(Notification.created_at < before)
    if unacked:
        q = q.where(Notification.acked_at.is_(None), Notification.severity != "info")
    rows = db.scalars(q.order_by(Notification.created_at.desc(), Notification.id).limit(limit)).all()
    pending = db.scalar(select(func.count()).select_from(Notification).where(
        Notification.home_id == home_id, Notification.acked_at.is_(None),
        Notification.severity != "info"))
    names = svc.user_names(db, (n.acked_by for n in rows))
    return ok([svc.notification_out(n, names) for n in rows],
              {"count": len(rows), "unacked": pending})


@router.post("/notifications/{nid}/ack")
def ack_notification(nid: uuid.UUID, p: Principal = Depends(get_principal),
                     db: Session = Depends(get_db)):
    n = _get(db, nid)
    membership_or_404(db, n.home_id, p.user)
    if not svc.can_ack(db, n, p.user.id):
        raise forbidden("Only owner/admin/family can acknowledge")
    svc.ack(db, n, p.user.id)
    return ok(svc.notification_out(n, svc.user_names(db, [n.acked_by])))


class AckTokenIn(Model):
    user_id: uuid.UUID
    token: str = Field(min_length=32, max_length=32)


@router.post("/notifications/{nid}/ack-token")
def ack_with_token(nid: uuid.UUID, body: AckTokenIn, db: Session = Depends(get_db),
                   settings: Settings = Depends(get_settings)):
    """'Ko'rdim' button of a push notification: the service worker has no access token,
    so the push payload carries an HMAC token valid for this notification x user only."""
    n = db.get(Notification, nid)
    good = svc.ack_token(settings, nid, body.user_id)
    if n is None or not hmac.compare_digest(good, body.token) or not svc.can_ack(db, n, body.user_id):
        raise not_found("Notification")
    svc.ack(db, n, body.user_id)
    return ok({"id": str(n.id), "acked_at": iso(n.acked_at)})


# ------------------------------------------------------------------ channel setup

@router.get("/notifications/settings")
def channel_settings(p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                     settings: Settings = Depends(get_settings)):
    links = db.scalars(select(TelegramLink).where(TelegramLink.user_id == p.user.id)
                       .order_by(TelegramLink.created_at)).all()
    subs = db.scalars(select(PushSubscription).where(PushSubscription.user_id == p.user.id)
                      .order_by(PushSubscription.created_at)).all()
    push_on = channels.push_enabled(settings)
    return ok({
        "telegram": {"available": channels.telegram_enabled(settings),
                     "links": [{"id": str(x.id), "username": x.username, "created_at": iso(x.created_at)}
                               for x in links]},
        "push": {"available": push_on,
                 "public_key": webpush.public_key_b64u(settings.vapid_private_key) if push_on else None,
                 "subscriptions": [{"id": str(x.id), "endpoint": x.endpoint, "user_agent": x.user_agent,
                                    "created_at": iso(x.created_at),
                                    "last_success_at": iso(x.last_success_at) if x.last_success_at else None}
                                   for x in subs]},
    })


@router.post("/notifications/telegram/link")
def telegram_link_code(p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                       settings: Settings = Depends(get_settings)):
    if not channels.telegram_enabled(settings):
        raise not_configured("Telegram bot")
    code, expires = svc.new_link_code(db, p.user.id)
    bot = channels.bot_username(settings)
    return ok({"code": code, "expires_at": iso(expires), "bot_username": bot,
               "url": f"https://t.me/{bot}?start={code}" if bot else None})


@router.delete("/notifications/telegram/links/{link_id}")
def telegram_unlink(link_id: uuid.UUID, p: Principal = Depends(get_principal),
                    db: Session = Depends(get_db)):
    n = db.execute(delete(TelegramLink).where(TelegramLink.id == link_id,
                                              TelegramLink.user_id == p.user.id)).rowcount
    db.commit()
    if not n:
        raise not_found("Telegram link")
    return ok({"deleted": True})


class PushKeys(Model):
    p256dh: str = Field(min_length=80, max_length=128)
    auth: str = Field(min_length=16, max_length=64)


class PushSubscribeIn(Model):
    endpoint: str = Field(min_length=10, max_length=1024)
    keys: PushKeys
    user_agent: Optional[str] = Field(default=None, max_length=200)
    expirationTime: Optional[float] = None    # sent by PushSubscription.toJSON(); unused


def _check_endpoint(url: str) -> None:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not any(host.endswith(s) or host == s[1:] for s in PUSH_HOST_SUFFIXES):
        raise validation_error("Unsupported push service endpoint")


@router.post("/notifications/push/subscribe", status_code=201)
def push_subscribe(body: PushSubscribeIn, p: Principal = Depends(get_principal),
                   db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    if not channels.push_enabled(settings):
        raise not_configured("Web Push")
    _check_endpoint(body.endpoint)
    try:
        ok_keys = (len(webpush.b64u_decode(body.keys.p256dh)) == 65
                   and len(webpush.b64u_decode(body.keys.auth)) == 16)
    except ValueError:
        ok_keys = False
    if not ok_keys:
        raise validation_error("Invalid push subscription keys")
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub is None:
        sub = PushSubscription(endpoint=body.endpoint)
        db.add(sub)
    # Same browser, other account (logout/login): the subscription follows the new user.
    sub.user_id, sub.p256dh, sub.auth, sub.user_agent = (
        p.user.id, body.keys.p256dh, body.keys.auth, body.user_agent)
    db.commit()
    return ok({"id": str(sub.id)})


class PushUnsubscribeIn(Model):
    endpoint: str = Field(min_length=10, max_length=1024)


@router.post("/notifications/push/unsubscribe")
def push_unsubscribe(body: PushUnsubscribeIn, p: Principal = Depends(get_principal),
                     db: Session = Depends(get_db)):
    n = db.execute(delete(PushSubscription).where(PushSubscription.endpoint == body.endpoint,
                                                  PushSubscription.user_id == p.user.id)).rowcount
    db.commit()
    return ok({"deleted": bool(n)})


# ------------------------------------------------------------------ prefs / test

class PrefsIn(Model):
    notify_min_severity: str = Field(pattern="^(info|warning|critical)$")


def _prefs_out(m: HomeMember) -> dict:
    return {"notify_min_severity": m.notify_min_severity,
            "receives": m.role in svc.RECIPIENT_ROLES}


@router.get("/homes/{home_id}/notification-prefs")
def get_prefs(home_id: uuid.UUID, p: Principal = Depends(get_principal),
              db: Session = Depends(get_db)):
    return ok(_prefs_out(membership_or_404(db, home_id, p.user)))


@router.put("/homes/{home_id}/notification-prefs")
def put_prefs(home_id: uuid.UUID, body: PrefsIn, p: Principal = Depends(get_principal),
              db: Session = Depends(get_db)):
    m = membership_or_404(db, home_id, p.user)
    m.notify_min_severity = body.notify_min_severity
    db.commit()
    return ok(_prefs_out(m))


@router.post("/homes/{home_id}/notifications:test")
def send_test(home_id: uuid.UUID, p: Principal = Depends(get_principal),
              db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Sends a test message to the caller's own channels and reports what really happened."""
    membership_or_404(db, home_id, p.user)
    n = svc.create(db, home_id=home_id, severity="info", source="test", kind="test",
                   title=svc.notify_texts.system_title("test", {}), users={p.user.id})
    db.commit()
    svc.deliver_due(db, settings, notification_ids=[n.id], budget_s=8.0)
    rows = db.scalars(select(NotificationDelivery).where(
        NotificationDelivery.notification_id == n.id)).all()
    return ok({"id": str(n.id), "deliveries": [
        {"channel": d.channel, "status": d.status, "error": d.error} for d in rows]})


# ------------------------------------------------------------------ Telegram webhook

@router.post("/telegram/webhook", include_in_schema=False)
def telegram_webhook(request: Request, update: dict = Body(...), db: Session = Depends(get_db),
                     settings: Settings = Depends(get_settings)):
    secret = request.headers.get("x-telegram-bot-api-secret-token", "")
    if (not channels.telegram_enabled(settings) or not settings.telegram_webhook_secret
            or not hmac.compare_digest(secret, settings.telegram_webhook_secret)):
        raise not_found("Resource")
    return ok({"result": svc.handle_update(db, settings, update)})
