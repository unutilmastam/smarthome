import json
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.signing import canonical_json, derive_home_key, sign, verify
from app.db.types import utcnow
from app.models import Command, Hub
from conftest import PASSWORD, Api, login

VECTORS = Path(__file__).resolve().parents[3] / "packages/contracts/test-vectors/signing.json"
GATE = {"key": "front_gate", "name": "Darvoza", "adapter": "esphome", "protocol": "mqtt",
        "capabilities": {"cover": {"confirm_timeout_s": 30}}}
VALVE = {"key": "garden_valve", "name": "Sug'orish", "adapter": "esphome", "protocol": "mqtt",
         "capabilities": {"valve": {"max_runtime_s": 600}}}


@pytest.fixture
def hub(client, owner, owner_home):
    data = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "hub"}).json()["data"]
    api = Api(client, data["hub_token"])
    assert api.post("/api/v1/hub/heartbeat", json={"version": "0.1.0"}).status_code == 200
    api.info = data
    return api


def cmd(device_id, capability="switch", action="turn_on", params=None, key=None, **extra):
    body = {"device_id": device_id, "capability": capability, "action": action,
            "params": params or {}, "idempotency_key": key or uuid.uuid4().hex}
    body.update(extra)
    return body


def ack(command_id, status, reason=None):
    a = {"schema": 1, "command_id": command_id, "status": status,
         "ts": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
    if reason:
        a["reason"] = reason
    return a


# ---- signing vectors -----------------------------------------------------------------

def test_signing_vectors():
    v = json.loads(VECTORS.read_text(encoding="utf-8"))
    key = derive_home_key(v["master_key"], uuid.UUID(v["home_id"]))
    assert key.hex() == v["home_signing_key_hex"]
    for case in v["cases"]:
        assert canonical_json(case["payload"]).decode() == case["canonical"], case["name"]
        assert sign(key, case["payload"]) == case["signature"], case["name"]
    for case in v["negative"]:
        assert verify(key, case["payload"], case["signature"]) is case["valid"]


# ---- full lifecycle --------------------------------------------------------------------

def test_full_cycle_queued_sent_acked_confirmed(owner, light, hub, settings, owner_home):
    r = owner.post("/api/v1/commands", json=cmd(light["id"]))
    assert r.status_code == 201, r.text
    c = r.json()["data"]
    assert c["status"] == "queued"

    got = hub.get("/api/v1/hub/commands").json()["data"]
    assert len(got) == 1
    env = got[0]
    assert env["schema"] == 1
    p = env["payload"]
    assert p["command_id"] == c["id"] and p["device_key"] == "garden_lights"
    assert p["issued_by"]["role"] == "owner"
    key = bytes.fromhex(hub.info["signing_key_hex"])
    assert verify(key, p, env["signature"])
    assert key == derive_home_key(settings.signing_master_key, owner_home)

    r = hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "acked")]})
    assert r.json()["data"]["results"][0]["result"] == "applied"
    r = hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "confirmed")]})
    assert r.json()["data"]["results"][0]["status"] == "confirmed"

    full = owner.get(f"/api/v1/commands/{c['id']}").json()["data"]
    assert full["status"] == "confirmed"
    assert [e["status"] for e in full["events"]] == ["queued", "sent", "acked", "confirmed"]
    assert full["sent_at"] and full["acked_at"] and full["finished_at"]


def test_envelope_matches_contract_schema(owner, light, hub):
    from jsonschema import Draft202012Validator
    schema_path = VECTORS.parents[1] / "schemas/command-envelope.schema.json"
    schema = json.loads(schema_path.read_text())
    owner.post("/api/v1/commands", json=cmd(light["id"]))
    env = hub.get("/api/v1/hub/commands").json()["data"][0]
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER
                         ).validate(env)


def test_command_is_claimed_only_once(owner, light, hub):
    owner.post("/api/v1/commands", json=cmd(light["id"]))
    assert len(hub.get("/api/v1/hub/commands").json()["data"]) == 1
    assert hub.get("/api/v1/hub/commands").json()["data"] == []


def test_late_ack_does_not_undo_confirmed(owner, light, hub):
    c = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    hub.get("/api/v1/hub/commands")
    hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "confirmed")]})
    r = hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "acked")]})
    assert r.json()["data"]["results"][0] == {"command_id": c["id"], "result": "ignored",
                                              "status": "confirmed"}
    r = hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "failed", "device_error")]})
    assert r.json()["data"]["results"][0]["status"] == "confirmed"
    full = owner.get(f"/api/v1/commands/{c['id']}").json()["data"]
    assert full["status"] == "confirmed"
    assert [e["applied"] for e in full["events"]][-2:] == [False, False]


def test_rejected_by_hub(owner, light, hub):
    c = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    hub.get("/api/v1/hub/commands")
    hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "rejected", "bad_signature")]})
    full = owner.get(f"/api/v1/commands/{c['id']}").json()["data"]
    assert (full["status"], full["reason"]) == ("rejected", "bad_signature")


def test_invalid_ack_documents(owner, light, hub):
    c = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    hub.get("/api/v1/hub/commands")
    for bad in (ack(c["id"], "rejected"), ack(c["id"], "done"),
                {**ack(c["id"], "acked"), "ts": "yesterday"}):
        r = hub.post("/api/v1/hub/acks", json={"acks": [bad]})
        assert r.status_code == 422
    assert hub.post("/api/v1/hub/acks", json={"acks": []}).status_code == 422


def test_ack_for_command_delivered_via_broker(owner, light, hub):
    """ADR 0008: the hub may get a command from the realtime broker before any poll."""
    c = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    r = hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "confirmed")]})
    assert r.json()["data"]["results"][0] == {"command_id": c["id"], "result": "applied",
                                              "status": "confirmed"}
    full = owner.get(f"/api/v1/commands/{c['id']}").json()["data"]
    assert [e["status"] for e in full["events"] if e["applied"]] == \
        ["queued", "sent", "confirmed"]
    assert full["sent_at"] is not None
    # A poll afterwards must not deliver it again.
    assert hub.get("/api/v1/hub/commands").json()["data"] == []


# ---- expiry / timeout ------------------------------------------------------------------

def _age(dbs, command_id, seconds):
    c = dbs.get(Command, uuid.UUID(command_id))
    delta = timedelta(seconds=seconds)
    c.created_at -= delta
    c.expires_at -= delta
    if c.sent_at:
        c.sent_at -= delta
    if c.acked_at:
        c.acked_at -= delta
    dbs.commit()


def test_unclaimed_command_expires_and_is_never_delivered(owner, light, hub, dbs):
    c = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    _age(dbs, c["id"], 11)
    assert hub.get("/api/v1/hub/commands").json()["data"] == []
    full = owner.get(f"/api/v1/commands/{c['id']}").json()["data"]
    assert full["status"] == "expired"


def test_sent_without_ack_times_out(owner, light, hub, dbs):
    c = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    hub.get("/api/v1/hub/commands")
    _age(dbs, c["id"], 10 + 31)
    full = owner.get(f"/api/v1/commands/{c['id']}").json()["data"]
    assert (full["status"], full["reason"]) == ("timeout", "no_ack")
    # A very late ack cannot revive it.
    r = hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "confirmed")]})
    assert r.json()["data"]["results"][0]["status"] == "timeout"


def test_acked_gate_without_confirmation_times_out(owner, owner_home, hub, dbs):
    gate = owner.post(f"/api/v1/homes/{owner_home}/devices", json=GATE).json()["data"]
    owner.post("/api/v1/auth/pin", json={"password": PASSWORD, "pin": "4821"})
    c = owner.post("/api/v1/commands", json=cmd(gate["id"], "cover", "open",
                                                 confirm_pin="4821")).json()["data"]
    assert c["risk"] == "high"
    hub.get("/api/v1/hub/commands")
    hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "acked")]})
    _age(dbs, c["id"], 60 + 31)
    full = owner.get(f"/api/v1/commands/{c['id']}").json()["data"]
    assert (full["status"], full["reason"]) == ("timeout", "no_feedback")


def test_acked_switch_stays_acked(owner, light, hub, dbs):
    c = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    hub.get("/api/v1/hub/commands")
    hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "acked")]})
    _age(dbs, c["id"], 3600)
    assert owner.get(f"/api/v1/commands/{c['id']}").json()["data"]["status"] == "acked"


def test_expiry_durations(owner, owner_home, light, hub):
    owner.post("/api/v1/auth/pin", json={"password": PASSWORD, "pin": "4821"})
    gate = owner.post(f"/api/v1/homes/{owner_home}/devices", json=GATE).json()["data"]
    from datetime import datetime
    def life(c):
        f = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
        return round((f(c["expires_at"]) - f(c["created_at"])).total_seconds())
    low = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    high = owner.post("/api/v1/commands", json=cmd(gate["id"], "cover", "open",
                                                    confirm_pin="4821")).json()["data"]
    assert (life(low), life(high)) == (10, 5)


# ---- validation chain ------------------------------------------------------------------

def test_gate_without_pin_is_refused(owner, owner_home, hub):
    gate = owner.post(f"/api/v1/homes/{owner_home}/devices", json=GATE).json()["data"]
    r = owner.post("/api/v1/commands", json=cmd(gate["id"], "cover", "open"))
    assert (r.status_code, r.json()["error"]["code"]) == (403, "PIN_REQUIRED")
    owner.post("/api/v1/auth/pin", json={"password": PASSWORD, "pin": "4821"})
    r = owner.post("/api/v1/commands", json=cmd(gate["id"], "cover", "open", confirm_pin="0000"))
    assert (r.status_code, r.json()["error"]["code"]) == (403, "PIN_INVALID")
    r = owner.post("/api/v1/commands", json=cmd(gate["id"], "cover", "open", confirm_pin="4821"))
    assert r.status_code == 201


def test_pin_bruteforce_is_limited(owner, owner_home, hub):
    gate = owner.post(f"/api/v1/homes/{owner_home}/devices", json=GATE).json()["data"]
    owner.post("/api/v1/auth/pin", json={"password": PASSWORD, "pin": "4821"})
    codes = [owner.post("/api/v1/commands", json=cmd(gate["id"], "cover", "open",
                                                     confirm_pin=f"{i:04d}")).status_code
             for i in range(5)]
    assert codes == [403] * 5
    # Even the right PIN is refused now.
    r = owner.post("/api/v1/commands", json=cmd(gate["id"], "cover", "open", confirm_pin="4821"))
    assert r.status_code == 429


@pytest.mark.parametrize("role", ["guest", "viewer"])
def test_guest_and_viewer_cannot_control(role, make_member, light, hub):
    api = make_member(role)
    r = api.post("/api/v1/commands", json=cmd(light["id"]))
    assert (r.status_code, r.json()["error"]["code"]) == (403, "FORBIDDEN")


def test_family_can_use_light_but_not_contactor(make_member, owner, owner_home, light, hub):
    fam = make_member("family")
    assert fam.post("/api/v1/commands", json=cmd(light["id"])).status_code == 201
    body = {"key": "line_boiler", "name": "Kontaktor", "adapter": "esphome", "protocol": "mqtt",
            "capabilities": {"contactor": {}}}
    k = owner.post(f"/api/v1/homes/{owner_home}/devices", json=body).json()["data"]
    r = fam.post("/api/v1/commands", json=cmd(k["id"], "contactor", "open", confirm_pin="1234"))
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"


def test_bad_params_and_unknown_action(owner, light, hub):
    r = owner.post("/api/v1/commands",
                   json=cmd(light["id"], "dimmer", "set_brightness", {"brightness": 150}))
    assert (r.status_code, r.json()["error"]["code"]) == (422, "VALIDATION_ERROR")
    r = owner.post("/api/v1/commands", json=cmd(light["id"], "dimmer", "set_brightness", {}))
    assert r.status_code == 422
    r = owner.post("/api/v1/commands", json=cmd(light["id"], "switch", "turn_on", {"x": 1}))
    assert r.status_code == 422
    r = owner.post("/api/v1/commands", json=cmd(light["id"], "switch", "explode"))
    assert r.status_code == 422
    r = owner.post("/api/v1/commands", json=cmd(light["id"], "climate", "set_power"))
    assert (r.status_code, r.json()["error"]["code"]) == (422, "CAPABILITY_NOT_SUPPORTED")


def test_valve_requires_duration_within_device_limit(owner, owner_home, hub):
    v = owner.post(f"/api/v1/homes/{owner_home}/devices", json=VALVE).json()["data"]
    assert owner.post("/api/v1/commands", json=cmd(v["id"], "valve", "open")).status_code == 422
    r = owner.post("/api/v1/commands",
                   json=cmd(v["id"], "valve", "open", {"duration_s": 900}))
    assert r.status_code == 422 and "max_runtime_s" in r.json()["error"]["message"]
    r = owner.post("/api/v1/commands", json=cmd(v["id"], "valve", "open", {"duration_s": 300}))
    assert r.status_code == 201


def test_offline_hub_returns_503_and_creates_nothing(owner, light, hub, dbs):
    h = dbs.get(Hub, uuid.UUID(hub.info["id"]))
    h.last_seen = utcnow() - timedelta(minutes=5)
    dbs.commit()
    r = owner.post("/api/v1/commands", json=cmd(light["id"]))
    assert (r.status_code, r.json()["error"]["code"]) == (503, "HUB_UNREACHABLE")
    assert dbs.scalars(select(Command)).all() == []


def test_no_hub_returns_503(owner, light):
    r = owner.post("/api/v1/commands", json=cmd(light["id"]))
    assert r.status_code == 503


def test_disabled_and_offline_device(owner, light, hub, dbs):
    from app.models import Device
    owner.patch(f"/api/v1/devices/{light['id']}", json={"enabled": False})
    r = owner.post("/api/v1/commands", json=cmd(light["id"]))
    assert (r.status_code, r.json()["error"]["code"]) == (409, "DEVICE_DISABLED")
    owner.patch(f"/api/v1/devices/{light['id']}", json={"enabled": True})
    d = dbs.get(Device, uuid.UUID(light["id"]))
    d.availability = "offline"
    dbs.commit()
    r = owner.post("/api/v1/commands", json=cmd(light["id"]))
    assert (r.status_code, r.json()["error"]["code"]) == (409, "DEVICE_OFFLINE")


def test_outsider_gets_404(outsider, light, hub):
    r = outsider.post("/api/v1/commands", json=cmd(light["id"]))
    assert r.status_code == 404


# ---- idempotency / rate limit ---------------------------------------------------------

def test_idempotency_returns_original(owner, light, hub, dbs):
    body = cmd(light["id"], key="tap-1234567")
    a = owner.post("/api/v1/commands", json=body)
    b = owner.post("/api/v1/commands", json=body)
    assert (a.status_code, b.status_code) == (201, 200)
    assert a.json()["data"]["id"] == b.json()["data"]["id"]
    assert b.json()["meta"]["idempotent_replay"] is True
    assert len(dbs.scalars(select(Command)).all()) == 1
    other = cmd(light["id"], action="turn_off", key="tap-1234567")
    assert owner.post("/api/v1/commands", json=other).status_code == 409


def test_command_rate_limit(owner, light, hub, settings):
    settings.command_rate_limit_per_min = 3
    codes = [owner.post("/api/v1/commands", json=cmd(light["id"])).status_code for _ in range(4)]
    assert codes == [201, 201, 201, 429]


# ---- hub isolation ----------------------------------------------------------------------

def test_other_homes_hub_cannot_see_or_ack(owner, light, hub, outsider, client):
    other_home = outsider.get("/api/v1/homes").json()["data"][0]["id"]
    other = outsider.post(f"/api/v1/homes/{other_home}/hubs", json={"name": "x"}).json()["data"]
    other_hub = Api(client, other["hub_token"])
    c = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    assert other_hub.get("/api/v1/hub/commands").json()["data"] == []
    r = other_hub.post("/api/v1/hub/acks", json={"acks": [ack(c["id"], "confirmed")]})
    assert r.json()["data"]["results"][0]["result"] == "not_found"
    assert owner.get(f"/api/v1/commands/{c['id']}").json()["data"]["status"] == "queued"
    # And the other home's signing key cannot produce this home's signature.
    env = hub.get("/api/v1/hub/commands").json()["data"][0]
    assert not verify(bytes.fromhex(other["signing_key_hex"]), env["payload"], env["signature"])


def test_hub_auth(client, owner, owner_home, hub):
    assert client.get("/api/v1/hub/commands").status_code == 401
    assert Api(client, "hub_wrong").get("/api/v1/hub/commands").status_code == 401
    # A user token is not a hub token.
    assert owner.get("/api/v1/hub/commands").status_code == 401
    owner.post(f"/api/v1/hubs/{hub.info['id']}/revoke")
    assert hub.get("/api/v1/hub/commands").status_code == 401


def test_command_history(owner, light, hub):
    for _ in range(3):
        owner.post("/api/v1/commands", json=cmd(light["id"]))
    r = owner.get(f"/api/v1/devices/{light['id']}/commands", params={"limit": 2})
    assert r.json()["meta"]["total"] == 3 and len(r.json()["data"]) == 2


def test_expire_due_never_judges_a_stale_status(owner, light, hub, dbs, database, settings):
    """Race seen in the hub integration test: the phone's status poll had the command loaded
    as 'sent' while the hub's ack committed 'acked'; expire_due then saw the stale 'sent'
    object and wrongly timed it out (no_ack) seconds after creation."""
    from app.core.contracts import load_contracts
    from app.services.commands import expire_due
    c = owner.post("/api/v1/commands", json=cmd(light["id"])).json()["data"]
    hub.get("/api/v1/hub/commands")
    cid = uuid.UUID(c["id"])
    stale = dbs.get(Command, cid)              # this session now caches status 'sent'
    assert stale.status == "sent"
    with database.sessionmaker() as other:     # ack arrives through another request
        row = other.get(Command, cid)
        row.status, row.acked_at = "acked", utcnow()
        other.commit()
    assert expire_due(dbs, settings, load_contracts(str(settings.contracts_dir))) == 0
    dbs.refresh(stale)
    assert stale.status == "acked"
