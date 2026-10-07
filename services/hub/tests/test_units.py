import copy
import json
import uuid
from datetime import timedelta

import pytest

from gateway.expectations import expectation
from gateway.signing import canonical_json, sign, verify
from gateway.store import Store
from gateway.timeutil import iso, utcnow
from gateway.verifier import verify_envelope

from conftest import CONTRACTS

KEY = bytes(range(32))
DEVICE = {"id": str(uuid.uuid4()), "key": "garden_lights", "enabled": True,
          "capabilities": {"switch": {}, "dimmer": {}}, "unsupported": []}
VALVE = {"id": str(uuid.uuid4()), "key": "garden_valve", "enabled": True,
         "capabilities": {"valve": {"max_runtime_s": 600}}, "unsupported": []}


def test_signing_vectors_match_backend():
    v = json.loads((CONTRACTS / "test-vectors" / "signing.json").read_text(encoding="utf-8"))
    key = bytes.fromhex(v["home_signing_key_hex"])
    for case in v["cases"]:
        assert canonical_json(case["payload"]).decode() == case["canonical"]
        assert sign(key, case["payload"]) == case["signature"]
        assert verify(key, case["payload"], case["signature"])
    for case in v["negative"]:
        assert verify(key, case["payload"], case["signature"]) is case["valid"]


def envelope(device=DEVICE, capability="switch", action="turn_on", params=None,
             role="owner", age_s=0, ttl_s=10, key=KEY):
    now = utcnow() - timedelta(seconds=age_s)
    payload = {
        "command_id": str(uuid.uuid4()), "device_id": device["id"], "device_key": device["key"],
        "capability": capability, "action": action, "params": params or {},
        "issued_at": iso(now), "expires_at": iso(now + timedelta(seconds=ttl_s)),
        "issued_by": {"user_id": str(uuid.uuid4()), "role": role},
    }
    return {"schema": 1, "payload": payload, "signature": sign(key, payload)}


@pytest.fixture
def check(contracts, tmp_path):
    store = Store(str(tmp_path / "hub.sqlite3"))

    def run(env, availability=None, devices=None):
        return verify_envelope(env, key=KEY, contracts=contracts, store=store,
                               devices=devices or {"garden_lights": DEVICE, "garden_valve": VALVE},
                               availability=availability or {}, now=utcnow(), skew_s=5)
    run.store = store
    return run


def test_valid_command_passes(check):
    v = check(envelope())
    assert v.ok and v.payload["device_key"] == "garden_lights"


def test_tampered_payload_is_bad_signature(check):
    env = envelope()
    env["payload"]["action"] = "turn_off"
    v = check(env)
    assert (v.ok, v.reason) == (False, "bad_signature")


def test_wrong_key_and_missing_signature(check):
    assert check(envelope(key=bytes(32))).reason == "bad_signature"
    env = envelope()
    del env["signature"]
    assert check(env).reason == "bad_signature"
    assert check({"garbage": True}).reason == "bad_signature"


def test_expired_and_future(check):
    assert check(envelope(age_s=16)).reason == "expired"       # 10 s ttl + 5 s skew
    assert check(envelope(age_s=12)).ok                        # within skew
    assert check(envelope(age_s=-10)).reason == "expired"      # issued in the future


def test_replay_is_rejected(check):
    env = envelope()
    assert check(env).ok
    v = check(copy.deepcopy(env))
    assert (v.ok, v.reason) == (False, "replay")


def test_replay_survives_restart(check, contracts, tmp_path):
    env = envelope()
    assert check(env).ok
    check.store.close()
    store2 = Store(str(tmp_path / "hub.sqlite3"))
    v = verify_envelope(env, key=KEY, contracts=contracts, store=store2,
                        devices={"garden_lights": DEVICE}, availability={}, now=utcnow(), skew_s=5)
    assert v.reason == "replay"


def test_unknown_device_and_id_mismatch(check):
    other = dict(DEVICE, id=str(uuid.uuid4()))
    assert check(envelope(device=other)).reason == "unknown_device"
    ghost = dict(DEVICE, key="ghost")
    assert check(envelope(device=ghost)).reason == "unknown_device"


def test_params_and_capability(check):
    assert check(envelope(capability="dimmer", action="set_brightness",
                          params={"brightness": 101})).reason == "invalid_params"
    assert check(envelope(capability="climate", action="set_power",
                          params={"power": True})).reason == "invalid_params"
    assert check(envelope(action="explode")).reason == "invalid_params"


def test_role_checked_again_on_hub(check):
    assert check(envelope(role="viewer")).reason == "forbidden"
    assert check(envelope(role="guest")).reason == "forbidden"
    assert check(envelope(role="family")).ok


def test_local_safety_rules(check):
    assert check(envelope(device=VALVE, capability="valve", action="open",
                          params={"duration_s": 900})).reason == "safety_rule"
    assert check(envelope(device=VALVE, capability="valve", action="open",
                          params={"duration_s": 300})).ok
    disabled = dict(DEVICE, enabled=False)
    assert check(envelope(device=disabled), devices={"garden_lights": disabled}
                 ).reason == "safety_rule"
    assert check(envelope(), availability={"garden_lights": "offline"}).reason == "device_offline"


def test_expectations():
    assert expectation("switch", "turn_on", {})({"on": True}) is True
    assert expectation("switch", "turn_on", {})({"on": False}) is False
    assert expectation("switch", "toggle", {}, {"on": True})({"on": False}) is True
    assert expectation("switch", "toggle", {}, {"on": None}) is None
    assert expectation("cover", "open", {})({"state": "opening"}) is False
    assert expectation("cover", "open", {})({"state": "open"}) is True
    assert expectation("cover", "open", {})({"position": 50}) is None
    assert expectation("contactor", "close", {})({"aux_contact_closed": True}) is True
    assert expectation("climate", "set_power", {"power": True}) is None


def test_store_outbox_order_and_state(tmp_path):
    s = Store(str(tmp_path / "x.sqlite3"))
    for i in range(3):
        s.enqueue("ack", {"n": i})
    items = s.peek("ack")
    assert [p["n"] for _, p in items] == [0, 1, 2]
    s.ack_outbox([items[0][0]])
    assert s.outbox_size() == 2
    s.put_state("k", "switch", "on", True, "reported", iso(utcnow()))
    s.put_state("k", "switch", "on", False, "reported", iso(utcnow()))
    assert s.get_state("k", "switch", "on")["value"] is False
    s.put_kv("config", {"devices": []})
    assert s.get_kv("config") == {"devices": []}
