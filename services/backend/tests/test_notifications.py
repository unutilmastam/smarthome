"""Phase 13 / ADR 0014: notifications over Telegram and Web Push [SIM].

Telegram and push services are replaced by an httpx MockTransport. Push payloads are
DECRYPTED here (RFC 8291 receiver side), so encryption is checked end to end.
"""

import base64
import json
import os
import uuid
from datetime import timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select, update

from app.core.config import Settings
from app.db.types import utcnow
from app.jobs import notify as notify_job
from app.models import (
    Device, Hub, Notification, NotificationDelivery, PushSubscription, TelegramLink,
)
from app.services import channels, notifications, webpush
from app.services.webpush import _hmac, b64u_decode, b64u_encode, public_bytes
from conftest import Api
from test_events import ALARM, GATE, ev

SECRET = "w" * 40
VAPID = webpush.generate_private_key()
WEBHOOK = "/api/v1/telegram/webhook"


@pytest.fixture
def settings():
    return Settings(_env_file=None, env="test", cookie_secure=False,
                    telegram_bot_token="123:abc", telegram_webhook_secret=SECRET,
                    vapid_private_key=VAPID, public_base_url="https://home.example.uz")


class Fake:
    """Telegram Bot API + push services."""

    def __init__(self):
        self.calls = []
        self.tg_status, self.tg_desc = 200, ""
        self.push_status = 201
        self.msg_id = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.startswith("https://api.telegram.org/bot123:abc/"):
            method = url.rsplit("/", 1)[1]
            body = json.loads(request.content or b"{}")
            self.calls.append(("tg", method, body))
            if self.tg_status != 200:
                return httpx.Response(self.tg_status, json={
                    "ok": False, "error_code": self.tg_status, "description": self.tg_desc})
            if method == "getMe":
                return httpx.Response(200, json={"ok": True, "result": {"username": "uy_bot"}})
            self.msg_id += 1
            return httpx.Response(200, json={"ok": True, "result": {"message_id": self.msg_id}})
        self.calls.append(("push", url, request))
        return httpx.Response(self.push_status)

    def tg(self, method):
        return [c[2] for c in self.calls if c[0] == "tg" and c[1] == method]

    def pushes(self):
        return [c[2] for c in self.calls if c[0] == "push"]


@pytest.fixture
def fake():
    f = Fake()
    channels.set_transport(httpx.MockTransport(f))
    yield f
    channels.set_transport(None)


@pytest.fixture
def hub(client, owner, owner_home):
    data = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "hub"}).json()["data"]
    h = Api(client, data["hub_token"])
    assert h.post("/api/v1/hub/heartbeat", json={"version": "1"}).status_code == 200
    return h


@pytest.fixture
def alarm(owner, owner_home):
    url = f"/api/v1/homes/{owner_home}/devices"
    assert owner.post(url, json=ALARM).status_code == 201
    door = {"key": "front_door", "name": "Old eshik", "adapter": "esphome", "protocol": "mqtt",
            "capabilities": {"contact": {}}}
    assert owner.post(url, json=door).status_code == 201
    assert owner.post(url, json=GATE).status_code == 201


def tg_update(chat_id, text, chat_type="private"):
    return {"update_id": 1, "message": {"message_id": 1, "text": text, "from": {"id": chat_id, "username": "ali"},
                                        "chat": {"id": chat_id, "type": chat_type}}}


def webhook(client, body, secret=SECRET):
    return client.post(WEBHOOK, json=body, headers={"X-Telegram-Bot-Api-Secret-Token": secret})


def link(client, api, chat_id=111):
    data = api.post("/api/v1/notifications/telegram/link").json()["data"]
    r = webhook(client, tg_update(chat_id, f"/start {data['code']}"))
    assert r.json()["data"]["result"] == "linked", r.text
    return data


def ua_keys():
    key = ec.generate_private_key(ec.SECP256R1())
    return key, b64u_encode(public_bytes(key)), b64u_encode(os.urandom(16))


def decrypt(body: bytes, ua_key, auth_b64u: str) -> dict:
    """RFC 8291 receiver side (what the browser does)."""
    salt, rs, idlen = body[:16], int.from_bytes(body[16:20], "big"), body[20]
    as_pub, ct = body[21:21 + idlen], body[21 + idlen:]
    assert rs == 4096
    ecdh = ua_key.exchange(ec.ECDH(), ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), as_pub))
    prk_key = _hmac(b64u_decode(auth_b64u), ecdh)
    ikm = _hmac(prk_key, b"WebPush: info\x00" + public_bytes(ua_key) + as_pub + b"\x01")
    prk = _hmac(salt, ikm)
    cek = _hmac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = _hmac(prk, b"Content-Encoding: nonce\x00\x01")[:12]
    pt = AESGCM(cek).decrypt(nonce, ct, None)
    assert pt.endswith(b"\x02")
    return json.loads(pt[:-1])


def notes(dbs, kind=None):
    dbs.expire_all()
    q = select(Notification)
    if kind:
        q = q.where(Notification.kind == kind)
    return dbs.scalars(q.order_by(Notification.created_at)).all()


# ------------------------------------------------------------------ crypto


def test_webpush_matches_rfc8291_vector():
    as_key = webpush.private_key("yfWPiYE-n46HLnH0KqZOF1fJJU3MYrct3AELtAQ-oRw")
    out = webpush.encrypt(
        b"When I grow up, I want to be a watermelon",
        "BCVxsr7N_eNgVRqvHtD0zTZsEc6-VV-JvLexhqUzORcxaOzi6-AYWXvTBHm4bjyPjs7Vd8pZGH6SRpkNtoIAiw4",
        "BTBZMqHH6r4Tts7J_aSIgg", salt=b64u_decode("DGv6ra1nlYgDCS1FRnbzlw"), as_key=as_key)
    assert b64u_encode(out) == (
        "DGv6ra1nlYgDCS1FRnbzlwAAEABBBP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocIn"
        "mYWAmS6TlzAC8wEqKK6PBru3jl7A_yl95bQpu6cVPTpK4Mqgkf1CXztLVBSt2Ks3oZwbuwXPXLWyouBWLVWGNW"
        "QexSgSxsj_Qulcy4a-fN")


def test_vapid_header_is_a_valid_es256_token_for_the_push_origin():
    h = webpush.vapid_headers("https://fcm.googleapis.com/fcm/send/xyz", VAPID, "mailto:a@b.uz")
    t = h["Authorization"].split("t=", 1)[1].split(",", 1)[0]
    k = h["Authorization"].split("k=", 1)[1]
    assert k == webpush.public_key_b64u(VAPID)
    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), b64u_decode(k))
    claims = jwt.decode(t, pub, algorithms=["ES256"], audience="https://fcm.googleapis.com")
    assert claims["sub"] == "mailto:a@b.uz" and claims["exp"] > utcnow().timestamp() + 3600


# ------------------------------------------------------------------ Telegram


def test_telegram_link_flow_and_webhook_secret(client, owner, fake, dbs):
    data = owner.post("/api/v1/notifications/telegram/link").json()["data"]
    assert len(data["code"]) == 8 and data["url"] == f"https://t.me/uy_bot?start={data['code']}"
    # Wrong / missing secret: looks like nothing is there.
    assert webhook(client, tg_update(111, f"/start {data['code']}"), secret="x").status_code == 404
    assert webhook(client, tg_update(5, f"/start {data['code']}"), secret="").status_code == 404
    # Group chats are refused.
    assert webhook(client, tg_update(-9, f"/start {data['code']}", "group")).json()["data"]["result"] == "not_private"
    assert webhook(client, tg_update(111, f"/start {data['code'].lower()}")).json()["data"]["result"] == "linked"
    assert "Bog'landi" in fake.tg("sendMessage")[-1]["text"]
    # One-time code.
    assert webhook(client, tg_update(222, f"/start {data['code']}")).json()["data"]["result"] == "bad_code"
    s = owner.get("/api/v1/notifications/settings").json()["data"]
    assert s["telegram"]["available"] and [x["username"] for x in s["telegram"]["links"]] == ["ali"]
    # Only the hash is stored.
    from app.models import TelegramLinkCode
    assert all(len(c.code_hash) == 64 and c.code_hash != data["code"]
               for c in dbs.scalars(select(TelegramLinkCode)))
    assert webhook(client, tg_update(111, "/stop")).json()["data"]["result"] == "unlinked"
    assert owner.get("/api/v1/notifications/settings").json()["data"]["telegram"]["links"] == []


def test_expired_code_is_refused(client, owner, fake, dbs):
    from app.models import TelegramLinkCode
    code = owner.post("/api/v1/notifications/telegram/link").json()["data"]["code"]
    dbs.execute(update(TelegramLinkCode).values(expires_at=utcnow() - timedelta(seconds=1)))
    dbs.commit()
    assert webhook(client, tg_update(111, f"/start {code}")).json()["data"]["result"] == "bad_code"


def test_critical_event_reaches_telegram_at_once_and_is_acked_from_the_button(
        client, owner, owner_home, hub, alarm, fake, dbs):
    link(client, owner)
    r = hub.post("/api/v1/hub/events", json={"schema": 1, "events": [
        ev("alarm.triggered", key="security", data={"zone": "front_door", "mode": "entry"})]})
    assert r.json()["data"]["accepted"] == 1
    sent = fake.tg("sendMessage")[-1]           # delivered inside the hub request, no cron
    assert sent["chat_id"] == "111"
    assert "🚨 SIGNAL: Old eshik" in sent["text"] and "🏠 Uy" in sent["text"]
    btn = sent["reply_markup"]["inline_keyboard"][0][0]
    assert btn["text"] == "✅ Ko'rdim"
    listing = owner.get(f"/api/v1/homes/{owner_home}/notifications").json()
    assert listing["meta"]["unacked"] == 1
    n = listing["data"][0]
    assert n["kind"] == "alarm.triggered" and n["needs_ack"] and n["acked_at"] is None
    cb = {"update_id": 2, "callback_query": {"id": "cq1", "data": btn["callback_data"],
                                             "message": {"message_id": 7, "chat": {"id": 111}}}}
    assert webhook(client, cb).json()["data"]["result"] == "acked"
    assert fake.tg("answerCallbackQuery")[-1]["text"] == "✅ Tasdiqlandi"
    assert "Owner" in fake.tg("editMessageReplyMarkup")[-1]["reply_markup"]["inline_keyboard"][0][0]["text"]
    n = owner.get(f"/api/v1/homes/{owner_home}/notifications").json()["data"][0]
    assert n["acked_by_name"] == "Owner" and n["acked_at"]
    assert webhook(client, cb).json()["data"]["result"] == "already"
    # Retried hub batch: no second notification, no second message.
    count = len(fake.tg("sendMessage"))
    dbs.expire_all()
    assert len(notes(dbs)) == 1 and len(fake.tg("sendMessage")) == count


def test_callback_from_unlinked_chat_or_other_home_does_nothing(client, owner, owner_home, hub, alarm,
                                                                 fake, outsider, dbs):
    link(client, owner)
    link(client, outsider, chat_id=999)
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    nid = notes(dbs)[0].id
    for chat, want in ((555, "not_linked"), (999, "not_found")):
        cb = {"update_id": 3, "callback_query": {"id": "x", "data": f"ack:{nid}",
                                                 "message": {"message_id": 1, "chat": {"id": chat}}}}
        assert webhook(client, cb).json()["data"]["result"] == want
    assert notes(dbs)[0].acked_at is None


def test_min_severity_filter_and_prefs(client, owner, owner_home, hub, alarm, fake, dbs, settings):
    link(client, owner)
    base = len(fake.tg("sendMessage"))
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("alarm.armed", key="security")]})
    notify_job.run(dbs, settings)
    assert len(fake.tg("sendMessage")) == base          # info: in the app only (default warning)
    assert owner.get(f"/api/v1/homes/{owner_home}/notification-prefs").json()["data"] == {
        "notify_min_severity": "warning", "receives": True}
    r = owner.put(f"/api/v1/homes/{owner_home}/notification-prefs", json={"notify_min_severity": "info"})
    assert r.json()["data"]["notify_min_severity"] == "info"
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("alarm.disarmed", key="security")]})
    notify_job.run(dbs, settings)                       # info is not sent in the request: cron does it
    texts = [m["text"] for m in fake.tg("sendMessage")[base:]]
    assert len(texts) == 1 and "Qo'riqlash o'chirildi" in texts[0]
    assert "reply_markup" not in fake.tg("sendMessage")[-1]   # info needs no ack
    owner.put(f"/api/v1/homes/{owner_home}/notification-prefs", json={"notify_min_severity": "critical"})
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev(data={"open_s": 900})]})
    notify_job.run(dbs, settings)
    assert len(fake.tg("sendMessage")) == base + 1      # warning filtered out now
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    assert len(fake.tg("sendMessage")) == base + 2      # critical always
    assert owner.put(f"/api/v1/homes/{owner_home}/notification-prefs",
                     json={"notify_min_severity": "loud"}).status_code == 422


def test_viewer_gets_nothing_and_cannot_ack(client, owner, owner_home, hub, alarm, fake, make_member, dbs):
    viewer = make_member("viewer")
    link(client, viewer, chat_id=333)
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    assert not [m for m in fake.tg("sendMessage") if m["chat_id"] == "333" and "Gerkon" in m["text"]]
    nid = notes(dbs)[0].id
    assert viewer.post(f"/api/v1/notifications/{nid}/ack").status_code == 403
    assert viewer.get(f"/api/v1/homes/{owner_home}/notification-prefs").json()["data"]["receives"] is False
    family = make_member("family")
    assert family.post(f"/api/v1/notifications/{nid}/ack").json()["data"]["acked_by_name"] == "family"
    # First ack wins.
    assert owner.post(f"/api/v1/notifications/{nid}/ack").json()["data"]["acked_by_name"] == "family"


def test_outsider_sees_and_acks_nothing(owner_home, hub, alarm, fake, outsider, dbs):
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    nid = notes(dbs)[0].id
    assert outsider.get(f"/api/v1/homes/{owner_home}/notifications").status_code == 404
    assert outsider.post(f"/api/v1/notifications/{nid}/ack").status_code == 404


def test_retries_with_backoff_then_failed(client, owner, hub, alarm, fake, dbs, settings):
    link(client, owner)
    fake.tg_status, fake.tg_desc = 502, "Bad Gateway"
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    dbs.expire_all()
    d = dbs.scalars(select(NotificationDelivery)).one()
    assert d.status == "pending" and d.attempts == 1 and d.next_attempt_at > utcnow() + timedelta(seconds=50)
    for _ in range(4):
        dbs.execute(update(NotificationDelivery).values(next_attempt_at=utcnow() - timedelta(seconds=1)))
        dbs.commit()
        notify_job.run(dbs, settings)
    dbs.expire_all()
    d = dbs.scalars(select(NotificationDelivery)).one()
    assert d.status == "failed" and d.attempts == 5 and "502" in d.error


def test_blocked_bot_unlinks_the_chat(client, owner, hub, alarm, fake, dbs):
    link(client, owner)
    fake.tg_status, fake.tg_desc = 403, "Forbidden: bot was blocked by the user"
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    dbs.expire_all()
    assert dbs.scalars(select(NotificationDelivery)).one().status == "gone"
    assert dbs.scalars(select(TelegramLink)).all() == []


def test_stale_claim_is_retried_but_never_sent_twice(client, owner, hub, alarm, fake, dbs, settings):
    link(client, owner)
    fake.tg_status = 500
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    fake.tg_status = 200
    # A crashed sender left it "sending" 10 minutes ago.
    dbs.execute(update(NotificationDelivery).values(
        status="sending", claimed_at=utcnow() - timedelta(minutes=10),
        next_attempt_at=utcnow() - timedelta(seconds=1)))
    dbs.commit()
    base = len(fake.tg("sendMessage"))
    notify_job.run(dbs, settings)
    notify_job.run(dbs, settings)
    assert len(fake.tg("sendMessage")) == base + 1


# ------------------------------------------------------------------ Web Push


def subscribe(api, endpoint="https://fcm.googleapis.com/fcm/send/abc"):
    key, p256dh, auth = ua_keys()
    r = api.post("/api/v1/notifications/push/subscribe", json={
        "endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}, "user_agent": "iPhone",
        "expirationTime": None})
    return r, key, auth


def test_push_subscribe_deliver_decrypt_and_ack_with_token(client, owner, owner_home, hub, alarm,
                                                           fake, dbs):
    r, key, auth = subscribe(owner)
    assert r.status_code == 201, r.text
    s = owner.get("/api/v1/notifications/settings").json()["data"]["push"]
    assert s["available"] and s["public_key"] == webpush.public_key_b64u(VAPID)
    assert [x["user_agent"] for x in s["subscriptions"]] == ["iPhone"]
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("valve.flow_while_closed",
                                                                    key="front_gate")]})
    # valve event on a gate: rejected by the contract -> no notification at all
    assert fake.pushes() == []
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [
        ev("alarm.triggered", key="security", data={"zone": "front_door"})]})
    req = fake.pushes()[-1]
    assert req.url == "https://fcm.googleapis.com/fcm/send/abc"
    assert req.headers["content-encoding"] == "aes128gcm" and req.headers["urgency"] == "high"
    assert req.headers["authorization"].startswith("vapid t=")
    payload = decrypt(req.content, key, auth)
    assert payload["title"] == "🚨 SIGNAL: Old eshik" and payload["url"] == "/notifications"
    nid = payload["id"]
    bad = {"user_id": payload["ack"]["user_id"], "token": "0" * 32}
    assert client.post(f"/api/v1/notifications/{nid}/ack-token", json=bad).status_code == 404
    other = {"user_id": str(uuid.uuid4()), "token": payload["ack"]["token"]}
    assert client.post(f"/api/v1/notifications/{nid}/ack-token", json=other).status_code == 404
    r = client.post(f"/api/v1/notifications/{nid}/ack-token", json=payload["ack"])
    assert r.status_code == 200 and r.json()["data"]["acked_at"]
    assert owner.get(f"/api/v1/homes/{owner_home}/notifications?unacked=true").json()["data"] == []


def test_expired_push_subscription_is_removed(owner, hub, alarm, fake, dbs):
    subscribe(owner)
    fake.push_status = 410
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    dbs.expire_all()
    assert dbs.scalars(select(NotificationDelivery)).one().status == "gone"
    assert dbs.scalars(select(PushSubscription)).all() == []


@pytest.mark.parametrize("endpoint", [
    "http://fcm.googleapis.com/x", "https://169.254.169.254/latest", "https://evil.example.com/push",
    "https://googleapis.com.evil.uz/x"])
def test_push_endpoint_must_be_a_real_push_service(owner, fake, endpoint):
    assert subscribe(owner, endpoint)[0].status_code == 422


def test_push_resubscribe_moves_to_the_new_user_and_unsubscribe(owner, make_member, fake, dbs):
    subscribe(owner)
    fam = make_member("family")
    r, _, _ = subscribe(fam)
    assert r.status_code == 201
    dbs.expire_all()
    assert len(dbs.scalars(select(PushSubscription)).all()) == 1
    assert owner.get("/api/v1/notifications/settings").json()["data"]["push"]["subscriptions"] == []
    r = fam.post("/api/v1/notifications/push/unsubscribe",
                 json={"endpoint": "https://fcm.googleapis.com/fcm/send/abc"})
    assert r.json()["data"]["deleted"] is True


def test_not_configured_channels_say_so(client, database, owner_home):
    from app.main import create_app
    from fastapi.testclient import TestClient
    from conftest import login
    bare = Settings(_env_file=None, env="test", cookie_secure=False)
    with TestClient(create_app(bare, database)) as c:
        api = Api(c, login(c, "owner@example.com")["access_token"])
        s = api.get("/api/v1/notifications/settings").json()["data"]
        assert s["telegram"]["available"] is False and s["push"]["available"] is False
        assert s["push"]["public_key"] is None
        r = api.post("/api/v1/notifications/telegram/link")
        assert r.status_code == 503 and r.json()["error"]["code"] == "NOT_CONFIGURED"
        assert subscribe(api)[0].status_code == 503
        assert c.post(WEBHOOK, json={}, headers={"X-Telegram-Bot-Api-Secret-Token": ""}).status_code == 404


def test_test_message_reports_real_outcome(client, owner, owner_home, fake):
    r = owner.post(f"/api/v1/homes/{owner_home}/notifications:test")
    assert r.json()["data"]["deliveries"] == []           # no channel linked: says so
    link(client, owner)
    subscribe(owner)
    fake.push_status = 500
    d = owner.post(f"/api/v1/homes/{owner_home}/notifications:test").json()["data"]["deliveries"]
    assert sorted((x["channel"], x["status"]) for x in d) == [("push", "pending"), ("telegram", "sent")]
    assert "Sinov xabari" in fake.tg("sendMessage")[-1]["text"]


# ------------------------------------------------------------------ watchdog / reminders / automation


def _set_last_seen(dbs, delta):
    dbs.execute(update(Hub).values(last_seen=utcnow() - delta))
    dbs.commit()


def test_hub_offline_is_critical_within_3_minutes_once_and_back_online(
        client, owner, owner_home, hub, fake, dbs, settings, make_member):
    link(client, owner)
    viewer = make_member("viewer")
    link(client, viewer, chat_id=444)
    _set_last_seen(dbs, timedelta(seconds=100))
    notify_job.run(dbs, settings)
    assert notes(dbs, "hub.offline") == []                 # 100 s: not yet
    _set_last_seen(dbs, timedelta(seconds=160))
    notify_job.run(dbs, settings)
    off = notes(dbs, "hub.offline")
    assert len(off) == 1 and off[0].severity == "critical"
    msg = fake.tg("sendMessage")[-1]
    assert msg["chat_id"] == "111" and "Hub aloqasiz" in msg["text"]
    assert not [m for m in fake.tg("sendMessage") if m["chat_id"] == "444" and "Hub" in m["text"]]
    notify_job.run(dbs, settings)
    assert len(notes(dbs, "hub.offline")) == 1             # announced once
    hub.post("/api/v1/hub/heartbeat", json={"version": "1"})
    notify_job.run(dbs, settings)
    back = notes(dbs, "hub.online")
    assert len(back) == 1 and back[0].severity == "info"
    assert "Hub qayta ulandi" in fake.tg("sendMessage")[-1]["text"]   # info, but to those who were told
    dbs.expire_all()
    assert dbs.scalars(select(Hub)).one().offline_notified_at is None


def test_device_offline_after_5_minutes_only_while_hub_is_online(
        client, owner, owner_home, hub, light, fake, dbs, settings):
    link(client, owner)
    dbs.execute(update(Device).values(availability="offline", availability_ts=utcnow() - timedelta(minutes=4)))
    dbs.commit()
    notify_job.run(dbs, settings)
    assert notes(dbs, "device.offline") == []
    dbs.execute(update(Device).values(availability_ts=utcnow() - timedelta(minutes=6)))
    _set_last_seen(dbs, timedelta(minutes=10))             # hub itself is gone: one message, not many
    notify_job.run(dbs, settings)
    assert notes(dbs, "device.offline") == [] and len(notes(dbs, "hub.offline")) == 1
    hub.post("/api/v1/hub/heartbeat", json={"version": "1"})
    notify_job.run(dbs, settings)
    off = notes(dbs, "device.offline")
    assert len(off) == 1 and off[0].severity == "warning"
    assert "Qurilma aloqasiz: Bog' chiroqlari" in fake.tg("sendMessage")[-1]["text"]
    dbs.execute(update(Device).values(availability="online", availability_ts=utcnow()))
    dbs.commit()
    notify_job.run(dbs, settings)
    assert len(notes(dbs, "device.online")) == 1
    assert "qayta ulandi" in fake.tg("sendMessage")[-1]["text"]


def test_unacked_critical_is_reminded_once(client, owner, hub, alarm, fake, dbs, settings):
    link(client, owner)
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    base = len(fake.tg("sendMessage"))
    dbs.execute(update(Notification).values(created_at=utcnow() - timedelta(minutes=11)))
    dbs.commit()
    notify_job.run(dbs, settings)
    assert len(fake.tg("sendMessage")) == base + 1
    assert fake.tg("sendMessage")[-1]["text"].startswith("🔁 Eslatma")
    notify_job.run(dbs, settings)
    assert len(fake.tg("sendMessage")) == base + 1         # once


def test_acked_critical_is_not_reminded(client, owner, hub, alarm, fake, dbs, settings):
    link(client, owner)
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    nid = notes(dbs)[0].id
    owner.post(f"/api/v1/notifications/{nid}/ack")
    base = len(fake.tg("sendMessage"))
    dbs.execute(update(Notification).values(created_at=utcnow() - timedelta(minutes=11)))
    dbs.commit()
    notify_job.run(dbs, settings)
    assert len(fake.tg("sendMessage")) == base


def test_automation_notify_action_is_delivered(client, owner, owner_home, hub, light, fake, dbs):
    link(client, owner)
    a = owner.post(f"/api/v1/homes/{owner_home}/automations", json={"name": "Tun nazorati", "definition": {
        "triggers": [{"type": "time", "at": "23:00"}],
        "actions": [{"type": "notify", "severity": "warning", "text": "Bog' chirog'i yoqildi"}]}})
    assert a.status_code == 201, a.text
    run = {"id": str(uuid.uuid4()), "automation_id": a.json()["data"]["id"], "version": 1,
           "ts": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "trigger": "time 23:00", "result": "ok",
           "actions": [{"type": "notify", "outcome": "recorded", "severity": "warning",
                        "text": "Bog' chirog'i yoqildi"}]}
    hub.post("/api/v1/hub/automation-runs", json={"schema": 1, "runs": [run]})
    hub.post("/api/v1/hub/automation-runs", json={"schema": 1, "runs": [run]})   # retry
    got = notes(dbs, "automation.notify")
    assert len(got) == 1 and got[0].body == "⚙️ Tun nazorati"
    msgs = [m for m in fake.tg("sendMessage") if "Bog' chirog'i yoqildi" in m["text"]]
    assert len(msgs) == 1 and msgs[0]["text"].startswith("⚠️")


def test_retention_purges_old_notifications(owner, hub, alarm, fake, dbs):
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev("cover.sensor_conflict")]})
    dbs.execute(update(Notification).values(created_at=utcnow() - timedelta(days=181)))
    dbs.commit()
    from app.jobs import retention
    assert retention.run(dbs)["notifications"] == 1


def test_production_requires_webhook_secret_with_bot_token():
    from app.core.config import ConfigError
    base = dict(_env_file=None, env="production", database_url="postgresql://x/y",
                jwt_secret="a1" * 20, signing_master_key="b2" * 20)
    with pytest.raises(Exception) as e:
        Settings(**base, telegram_bot_token="1:x")
    assert "TELEGRAM_WEBHOOK_SECRET" in str(e.value)
    Settings(**base, telegram_bot_token="1:x", telegram_webhook_secret="c3" * 20)
    with pytest.raises(Exception):
        Settings(**base, public_base_url="http://plain.uz")
    assert ConfigError


def test_telegram_setup_job_registers_webhook_with_secret(settings, fake):
    from app.jobs import telegram_setup
    assert telegram_setup.run(settings) == "webhook set: https://home.example.uz/api/v1/telegram/webhook"
    hook = fake.tg("setWebhook")[-1]
    assert hook["secret_token"] == SECRET and hook["allowed_updates"] == ["message", "callback_query"]
    assert telegram_setup.run(Settings(_env_file=None, env="test")).startswith("skipped")
