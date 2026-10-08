"""Notifications (ADR 0014): create, fan out to Telegram / Web Push, deliver, ack, watchdog.

Rules:
- Recipients: owner/admin/family members whose notify_min_severity <= severity
  (critical always). An explicit `users` set (test, "back online") bypasses the filter.
- Each delivery is claimed (pending -> sending, conditional UPDATE) before sending, so the
  hub request and the cron never send the same message twice.
- Nothing is reported as sent unless the channel accepted it.
"""

import hashlib
import hmac
import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Set

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.types import utcnow
from app.models import (
    Automation, Device, Event, Home, HomeMember, Hub, Notification, NotificationDelivery,
    PushSubscription, TelegramLink, TelegramLinkCode, User,
)
from app.models.notification import SEVERITIES, SEVERITY_RANK
from app.services import channels, notify_texts
from app.services.device_view import iso

log = logging.getLogger(__name__)

RECIPIENT_ROLES = ("owner", "admin", "family")
BACKOFF_S = (60, 120, 240, 480)
MAX_ATTEMPTS = 5
CLAIM_STALE = timedelta(minutes=5)
RETENTION = timedelta(days=180)
LINK_CODE_TTL = timedelta(minutes=10)
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
DELIVER_BATCH = 200


# ---------------------------------------------------------------- create / fan out

def create(db: Session, *, home_id: uuid.UUID, severity: str, source: str, kind: str,
           title: str, body: str = "", data: Optional[dict] = None,
           ts: Optional[datetime] = None, dedupe_key: Optional[str] = None,
           users: Optional[Set[uuid.UUID]] = None) -> Optional[Notification]:
    """Adds the notification and its deliveries (no commit). None if already created."""
    if severity not in SEVERITIES:
        raise ValueError(f"bad severity {severity}")
    if dedupe_key and db.scalar(select(Notification.id).where(
            Notification.home_id == home_id, Notification.dedupe_key == dedupe_key)):
        return None
    n = Notification(id=uuid.uuid4(), home_id=home_id, severity=severity, source=source,
                     kind=kind, title=title[:200], body=body[:1000], data=data or {},
                     ts=ts or utcnow(), dedupe_key=dedupe_key)
    db.add(n)
    db.flush()
    fan_out(db, n, users=users)
    return n


def fan_out(db: Session, n: Notification, users: Optional[Set[uuid.UUID]] = None,
            reminder: int = 0) -> int:
    members = db.scalars(select(HomeMember).where(
        HomeMember.home_id == n.home_id, HomeMember.role.in_(RECIPIENT_ROLES))).all()
    count = 0
    for m in members:
        if users is not None:
            if m.user_id not in users:
                continue
        elif SEVERITY_RANK[n.severity] < SEVERITY_RANK.get(m.notify_min_severity, 1):
            continue
        for link in db.scalars(select(TelegramLink).where(TelegramLink.user_id == m.user_id)):
            db.add(NotificationDelivery(notification_id=n.id, user_id=m.user_id, channel="telegram",
                                        target=link.chat_id, reminder=reminder))
            count += 1
        for sub in db.scalars(select(PushSubscription).where(PushSubscription.user_id == m.user_id)):
            db.add(NotificationDelivery(notification_id=n.id, user_id=m.user_id, channel="push",
                                        target=str(sub.id), reminder=reminder))
            count += 1
    db.flush()
    return count


def recipients_of(db: Session, n: Notification) -> Set[uuid.UUID]:
    return set(db.scalars(select(NotificationDelivery.user_id).where(
        NotificationDelivery.notification_id == n.id)))


# ---------------------------------------------------------------- sources

def from_events(db: Session, home_id: uuid.UUID, new_events: Iterable[Event]) -> List[Notification]:
    new_events = list(new_events)
    if not new_events:
        return []
    names: Dict[str, str] = dict(db.execute(select(Device.key, Device.name).where(
        Device.home_id == home_id)).all())
    out = []
    for e in new_events:
        title = notify_texts.event_title(e.type, e.data or {}, lambda k: names.get(k, k))
        n = create(db, home_id=home_id, severity=e.severity, source="event", kind=e.type,
                   title=title, body=f"📍 {names.get(e.device_key, e.device_key)}",
                   data={**(e.data or {}), "event_id": str(e.id), "device_key": e.device_key},
                   ts=e.ts, dedupe_key=f"event:{e.id}")
        if n:
            out.append(n)
    return out


def from_run(db: Session, home_id: uuid.UUID, run_id: uuid.UUID, automation_id: uuid.UUID,
             ts: datetime, actions: list) -> List[Notification]:
    auto = db.get(Automation, automation_id)
    out = []
    for i, a in enumerate(actions or []):
        if a.get("type") != "notify" or not a.get("text"):
            continue
        sev = a.get("severity") if a.get("severity") in SEVERITIES else "info"
        n = create(db, home_id=home_id, severity=sev, source="automation", kind="automation.notify",
                   title=str(a["text"]), body=f"⚙️ {auto.name if auto else ''}".strip(),
                   data={"automation_id": str(automation_id), "run_id": str(run_id)},
                   ts=ts, dedupe_key=f"run:{run_id}:{i}")
        if n:
            out.append(n)
    return out


def _hub_offline(h: Hub, s: Settings, now: datetime) -> bool:
    return h.last_seen is None or h.last_seen < now - timedelta(seconds=s.hub_offline_alert_s)


def watchdog(db: Session, s: Settings, now: Optional[datetime] = None) -> List[Notification]:
    """Hub silent > hub_offline_alert_s -> critical; device offline > device_offline_alert_s
    (while its hub is online) -> warning; both announce when they are back. Commits."""
    now = now or utcnow()
    out: List[Notification] = []
    hubs = db.scalars(select(Hub).where(Hub.status == "active", Hub.last_seen.is_not(None))).all()
    online_homes = set()
    for h in hubs:
        if _hub_offline(h, s, now):
            if h.offline_notified_at is None:
                n = create(db, home_id=h.home_id, severity="critical", source="hub", kind="hub.offline",
                           title=notify_texts.system_title("hub.offline", {
                               "minutes": int((now - h.last_seen).total_seconds() // 60)}),
                           body=f"🖥 {h.name}", data={"hub_id": str(h.id), "last_seen": iso(h.last_seen)},
                           ts=h.last_seen, dedupe_key=f"hub.offline:{h.id}:{iso(h.last_seen)}")
                h.offline_notified_at = now
                out += [n] if n else []
        else:
            online_homes.add(h.home_id)
            if h.offline_notified_at is not None:
                prev = db.scalars(select(Notification).where(
                    Notification.home_id == h.home_id, Notification.kind == "hub.offline")
                    .order_by(Notification.created_at.desc()).limit(1)).first()
                n = create(db, home_id=h.home_id, severity="info", source="hub", kind="hub.online",
                           title=notify_texts.system_title("hub.online", {}), body=f"🖥 {h.name}",
                           data={"hub_id": str(h.id)}, ts=now,
                           dedupe_key=f"hub.online:{h.id}:{iso(h.offline_notified_at)}",
                           users=recipients_of(db, prev) if prev else set())
                h.offline_notified_at = None
                out += [n] if n else []
    if online_homes:
        devices = db.scalars(select(Device).where(
            Device.home_id.in_(online_homes), Device.enabled.is_(True), Device.adapter != "hub")).all()
        limit = now - timedelta(seconds=s.device_offline_alert_s)
        for d in devices:
            if (d.availability == "offline" and d.offline_notified_at is None
                    and d.availability_ts is not None and d.availability_ts < limit):
                n = create(db, home_id=d.home_id, severity="warning", source="device",
                           kind="device.offline",
                           title=notify_texts.system_title("device.offline", {"device": d.name}),
                           data={"device_id": str(d.id), "device": d.name}, ts=d.availability_ts,
                           dedupe_key=f"device.offline:{d.id}:{iso(d.availability_ts)}")
                d.offline_notified_at = now
                out += [n] if n else []
            elif d.availability == "online" and d.offline_notified_at is not None:
                prev = db.scalars(select(Notification).where(
                    Notification.home_id == d.home_id, Notification.kind == "device.offline",
                    Notification.created_at >= d.offline_notified_at - timedelta(seconds=5))
                    .order_by(Notification.created_at.desc())).first()
                n = create(db, home_id=d.home_id, severity="info", source="device",
                           kind="device.online",
                           title=notify_texts.system_title("device.online", {"device": d.name}),
                           data={"device_id": str(d.id), "device": d.name}, ts=now,
                           dedupe_key=f"device.online:{d.id}:{iso(d.offline_notified_at)}",
                           users=recipients_of(db, prev) if prev else set())
                d.offline_notified_at = None
                out += [n] if n else []
    db.commit()
    return out


def reminders(db: Session, s: Settings, now: Optional[datetime] = None) -> int:
    """Critical, not acked after notify_reminder_s -> sent once more to the same people."""
    now = now or utcnow()
    due = db.scalars(select(Notification).where(
        Notification.severity == "critical", Notification.acked_at.is_(None),
        Notification.reminded_at.is_(None),
        Notification.created_at < now - timedelta(seconds=s.notify_reminder_s),
        Notification.created_at > now - timedelta(days=1))).all()
    for n in due:
        users = recipients_of(db, n)
        if users:
            fan_out(db, n, users=users, reminder=1)
        n.reminded_at = now
    db.commit()
    return len(due)


# ---------------------------------------------------------------- delivery

def ack_token(s: Settings, nid: uuid.UUID, uid: uuid.UUID) -> str:
    return hmac.new(s.signing_master_key.encode(), f"notify-ack:{nid}:{uid}".encode(),
                    hashlib.sha256).hexdigest()[:32]


def _claim(db: Session, did: uuid.UUID, now: datetime) -> bool:
    r = db.execute(update(NotificationDelivery)
                   .where(NotificationDelivery.id == did, NotificationDelivery.status == "pending")
                   .values(status="sending", claimed_at=now))
    db.commit()
    return r.rowcount == 1


def _retry(d: NotificationDelivery, error: str, now: datetime) -> None:
    d.attempts += 1
    d.error = error[:200]
    if d.attempts >= MAX_ATTEMPTS:
        d.status = "failed"
    else:
        d.status = "pending"
        d.next_attempt_at = now + timedelta(seconds=BACKOFF_S[d.attempts - 1])


def _needs_ack(n: Notification) -> bool:
    return n.severity != "info" and n.acked_at is None


def _send_telegram(db, s, http, d, n, home) -> None:
    now = utcnow()
    text = notify_texts.message(n.severity, n.title, n.body, home.name,
                                notify_texts.local_time(n.ts, home.timezone), bool(d.reminder))
    payload = {"chat_id": d.target, "text": text, "disable_web_page_preview": True}
    if _needs_ack(n):
        payload["reply_markup"] = {"inline_keyboard": [[
            {"text": "✅ Ko'rdim", "callback_data": f"ack:{n.id}"}]]}
    try:
        channels.telegram(s, "sendMessage", payload, http=http)
    except channels.TelegramError as e:
        if e.status in (400, 403) and ("blocked" in e.description or "not found" in e.description
                                       or "deactivated" in e.description or e.status == 403):
            # The person blocked the bot / chat is gone: unlink, never retry.
            db.execute(delete(TelegramLink).where(TelegramLink.chat_id == d.target))
            d.status, d.error = "gone", e.description[:200]
        else:
            _retry(d, str(e), now)
        return
    d.status, d.sent_at, d.error = "sent", now, None


def _send_push(db, s, http, d, n, home) -> None:
    now = utcnow()
    sub = db.get(PushSubscription, uuid.UUID(d.target))
    if sub is None:
        d.status, d.error = "gone", "subscription removed"
        return
    payload = {"id": str(n.id), "severity": n.severity,
               "title": f"{notify_texts.SEVERITY_MARK.get(n.severity, '')} {n.title}".strip(),
               "body": " · ".join(x for x in (n.body, home.name,
                                              notify_texts.local_time(n.ts, home.timezone)) if x),
               "url": "/notifications", "reminder": bool(d.reminder)}
    if _needs_ack(n):
        payload["ack"] = {"user_id": str(d.user_id), "token": ack_token(s, n.id, d.user_id)}
    status = channels.push(s, sub.endpoint, sub.p256dh, sub.auth, payload,
                           urgency="high" if n.severity == "critical" else "normal", http=http)
    if status in (200, 201, 202):
        d.status, d.sent_at, d.error = "sent", now, None
        sub.last_success_at = now
    elif status in (404, 410):
        db.delete(sub)
        d.status, d.error = "gone", f"push {status}: subscription expired"
    elif status in (400, 403, 413):
        d.status, d.error = "failed", f"push {status}"
    else:
        _retry(d, f"push {status or 'network error'}", now)


def deliver_due(db: Session, s: Settings, notification_ids: Optional[List[uuid.UUID]] = None,
                budget_s: Optional[float] = None) -> Dict[str, int]:
    now = utcnow()
    db.execute(update(NotificationDelivery).where(
        NotificationDelivery.status == "sending",
        NotificationDelivery.claimed_at < now - CLAIM_STALE).values(status="pending"))
    db.commit()
    q = select(NotificationDelivery.id).where(NotificationDelivery.status == "pending",
                                              NotificationDelivery.next_attempt_at <= now)
    if notification_ids is not None:
        if not notification_ids:
            return {}
        q = q.where(NotificationDelivery.notification_id.in_(notification_ids))
    ids = list(db.scalars(q.order_by(NotificationDelivery.created_at).limit(DELIVER_BATCH)))
    counts: Dict[str, int] = {}
    if not ids:
        return counts
    start = time.monotonic()
    with channels.client(timeout=4.0 if budget_s else 8.0) as http:
        for did in ids:
            if budget_s is not None and time.monotonic() - start > budget_s:
                break
            if not _claim(db, did, utcnow()):
                continue
            d = db.get(NotificationDelivery, did)
            n = db.get(Notification, d.notification_id)
            home = db.get(Home, n.home_id)
            if d.reminder and n.acked_at is not None:
                d.status = "cancelled"     # someone already saw it: no reminder
            elif d.channel == "telegram":
                if channels.telegram_enabled(s):
                    _send_telegram(db, s, http, d, n, home)
                else:
                    _retry(d, "telegram not configured", utcnow())
            elif d.channel == "push":
                if channels.push_enabled(s):
                    _send_push(db, s, http, d, n, home)
                else:
                    _retry(d, "push not configured", utcnow())
            db.commit()
            counts[d.status] = counts.get(d.status, 0) + 1
    return counts


def dispatch_now(db: Session, s: Settings, created: List[Notification]) -> None:
    """Best effort inside the hub request: warning/critical only, <= 5 s. Cron does the rest."""
    ids = [n.id for n in created if n.severity != "info"]
    if not ids:
        return
    try:
        deliver_due(db, s, notification_ids=ids, budget_s=5.0)
    except Exception:   # never fail the hub upload because Telegram was slow
        db.rollback()
        log.exception("immediate notification delivery failed; cron will retry")


# ---------------------------------------------------------------- ack / output

def can_ack(db: Session, n: Notification, user_id: uuid.UUID) -> bool:
    role = db.scalar(select(HomeMember.role).where(HomeMember.home_id == n.home_id,
                                                   HomeMember.user_id == user_id))
    return role in RECIPIENT_ROLES


def ack(db: Session, n: Notification, user_id: uuid.UUID) -> bool:
    """First ack wins (it says who saw it first). Returns True if this call acked it."""
    if n.acked_at is not None:
        return False
    n.acked_by, n.acked_at = user_id, utcnow()
    db.commit()
    return True


def notification_out(n: Notification, names: Dict[uuid.UUID, str]) -> dict:
    return {"id": str(n.id), "ts": iso(n.ts), "created_at": iso(n.created_at),
            "severity": n.severity, "source": n.source, "kind": n.kind, "title": n.title,
            "body": n.body, "data": n.data or {}, "needs_ack": n.severity != "info",
            "acked_at": iso(n.acked_at) if n.acked_at else None,
            "acked_by": str(n.acked_by) if n.acked_by else None,
            "acked_by_name": names.get(n.acked_by) if n.acked_by else None}


def user_names(db: Session, ids: Iterable[Optional[uuid.UUID]]) -> Dict[uuid.UUID, str]:
    ids = {i for i in ids if i}
    return dict(db.execute(select(User.id, User.name).where(User.id.in_(ids))).all()) if ids else {}


# ---------------------------------------------------------------- telegram linking

def _code_hash(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode()).hexdigest()


def new_link_code(db: Session, user_id: uuid.UUID) -> tuple:
    db.execute(delete(TelegramLinkCode).where(TelegramLinkCode.user_id == user_id,
                                              TelegramLinkCode.used_at.is_(None)))
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    expires = utcnow() + LINK_CODE_TTL
    db.add(TelegramLinkCode(code_hash=_code_hash(code), user_id=user_id, expires_at=expires))
    db.commit()
    return code, expires


def _reply(s: Settings, chat_id, text: str) -> None:
    try:
        channels.telegram(s, "sendMessage", {"chat_id": chat_id, "text": text})
    except channels.TelegramError as e:
        log.warning("telegram reply failed: %s", e)


HELP = ("Bu SmartHome uy bildirishnomalari boti.\n"
        "Bog'lash: ilovada Sozlamalar → Bildirishnomalar → «Telegram'ni bog'lash».\n"
        "/stop — bu chatga xabar yuborishni to'xtatish.")


def handle_update(db: Session, s: Settings, update_: dict) -> str:
    """Telegram webhook update. Returns what was done (for tests/logs)."""
    cq = update_.get("callback_query")
    if cq:
        return _handle_callback(db, s, cq)
    msg = update_.get("message") or {}
    chat = msg.get("chat") or {}
    text = (msg.get("text") or "").strip()
    if not chat or not text:
        return "ignored"
    if chat.get("type") != "private":
        _reply(s, chat["id"], "Faqat shaxsiy chat qo'llab-quvvatlanadi.")
        return "not_private"
    chat_id = str(chat["id"])
    cmd, _, arg = text.partition(" ")
    cmd = cmd.split("@", 1)[0].lower()
    if cmd == "/start" and arg.strip():
        row = db.get(TelegramLinkCode, _code_hash(arg))
        if row is None or row.used_at is not None or row.expires_at < utcnow():
            _reply(s, chat_id, "Kod noto'g'ri yoki muddati o'tgan. Ilovadan yangi kod oling.")
            return "bad_code"
        row.used_at = utcnow()
        db.execute(delete(TelegramLink).where(TelegramLink.chat_id == chat_id))
        db.add(TelegramLink(user_id=row.user_id, chat_id=chat_id,
                            username=(msg.get("from") or {}).get("username")))
        db.commit()
        user = db.get(User, row.user_id)
        _reply(s, chat_id, f"✅ Bog'landi: {user.name if user else ''}. "
                           "Endi uy bildirishnomalari shu yerga keladi.")
        return "linked"
    if cmd == "/stop":
        n = db.execute(delete(TelegramLink).where(TelegramLink.chat_id == chat_id)).rowcount
        db.commit()
        _reply(s, chat_id, "Bildirishnomalar to'xtatildi." if n else "Bu chat bog'lanmagan.")
        return "unlinked" if n else "not_linked"
    _reply(s, chat_id, HELP)
    return "help"


def _handle_callback(db: Session, s: Settings, cq: dict) -> str:
    data = cq.get("data") or ""
    msg = cq.get("message") or {}
    chat_id = str((msg.get("chat") or {}).get("id", ""))
    answer = "Bu chat bog'lanmagan"
    result = "not_linked"
    link = db.scalar(select(TelegramLink).where(TelegramLink.chat_id == chat_id)) if chat_id else None
    n = None
    if link and data.startswith("ack:"):
        try:
            n = db.get(Notification, uuid.UUID(data[4:]))
        except ValueError:
            n = None
        if n is None or not can_ack(db, n, link.user_id):
            answer, result = "Topilmadi", "not_found"
        else:
            if ack(db, n, link.user_id):
                answer, result = "✅ Tasdiqlandi", "acked"
            else:
                answer, result = "Allaqachon tasdiqlangan", "already"
    try:
        channels.telegram(s, "answerCallbackQuery", {"callback_query_id": cq.get("id"), "text": answer})
        if n is not None and n.acked_at is not None and msg.get("message_id"):
            who = db.get(User, n.acked_by) if n.acked_by else None
            channels.telegram(s, "editMessageReplyMarkup", {
                "chat_id": chat_id, "message_id": msg["message_id"],
                "reply_markup": {"inline_keyboard": [[{
                    "text": f"✅ Ko'rildi — {who.name if who else ''}".strip(" —"),
                    "callback_data": "noop"}]]}})
    except channels.TelegramError as e:
        log.warning("telegram callback answer failed: %s", e)
    return result


# ---------------------------------------------------------------- retention

def purge(db: Session) -> int:
    n = db.execute(delete(Notification).where(Notification.created_at < utcnow() - RETENTION)).rowcount or 0
    db.execute(delete(TelegramLinkCode).where(TelegramLinkCode.expires_at < utcnow() - timedelta(days=1)))
    db.commit()
    return n
