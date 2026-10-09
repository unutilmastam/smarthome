"""ADR 0016: Tuya devices — connection settings, sealed Local Key, hub config."""

import pytest

from app.core.secretbox import SecretBoxError, open_, seal
from conftest import Api

LOCAL_KEY = "fakefakefakefake"


def tuya(key, profile="switch", caps=None, **conn):
    return {"key": key, "name": key, "adapter": "tuya", "protocol": "tuya-local",
            "capabilities": caps or {"switch": {}}, "secret": LOCAL_KEY,
            "connection": {"profile": profile, "device_id": "bf1234567890abcdef", "ip": "192.168.1.50",
                           "version": "3.4", **conn}}


@pytest.fixture
def hub(client, owner, owner_home):
    data = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "hub"}).json()["data"]
    return Api(client, data["hub_token"])


def test_secret_box_roundtrip_and_binding():
    t = seal("master", LOCAL_KEY, "device-1")
    assert LOCAL_KEY not in t and t.startswith("v1:")
    assert open_("master", t, "device-1") == LOCAL_KEY
    with pytest.raises(SecretBoxError):
        open_("master", t, "device-2")        # copied to another device: does not open
    with pytest.raises(SecretBoxError):
        open_("other-master", t, "device-1")


def test_relay_is_created_and_the_key_never_comes_back(owner, owner_home, dbs):
    r = owner.post(f"/api/v1/homes/{owner_home}/devices", json=tuya("rele_darvoza"))
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert d["connection"]["profile"] == "switch" and d["has_secret"] is True
    assert LOCAL_KEY not in r.text
    assert LOCAL_KEY not in owner.get(f"/api/v1/devices/{d['id']}").text
    assert LOCAL_KEY not in owner.get(f"/api/v1/homes/{owner_home}/devices").text
    from app.models import Device
    row = dbs.get(Device, __import__("uuid").UUID(d["id"]))
    assert row.secret_enc and LOCAL_KEY not in row.secret_enc
    from app.models import AuditLog
    assert LOCAL_KEY not in str([a.details for a in dbs.query(AuditLog).all()])


def test_breaker_profile_marks_what_it_cannot_measure(owner, owner_home):
    r = owner.post(f"/api/v1/homes/{owner_home}/devices",
                   json=tuya("avtomat_1", "breaker", {"breaker": {"position": 1}, "power_meter": {}}))
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert "power_meter.frequency" in d["unsupported"]
    assert d["capabilities"]["power_meter"]["attributes"]["frequency"]["quality"] == "not_supported"
    assert d["capabilities"]["breaker"]["attributes"]["closed"]["quality"] == "unknown"


@pytest.mark.parametrize("change", [
    {"connection": {"profile": "toaster"}},
    {"connection": {"device_id": "x"}},
    {"connection": {"ip": "8.8.8.8"}},                 # not on the home network
    {"connection": {"ip": "hub.local"}},
    {"connection": {"version": "2.0"}},
    {"connection": {"dps": {"switch": 300}}},
    {"connection": {"dps": {"rocket": 1}}},
    {"connection": {"color": "red"}},
    {"capabilities": {"switch": {}, "dimmer": {}}},    # the profile decides the capabilities
    {"secret": None},
])
def test_bad_tuya_settings_are_refused(owner, owner_home, change):
    body = tuya("rele_x")
    for k, v in change.items():
        if k == "connection":
            body["connection"] = {**body["connection"], **v}
        else:
            body[k] = v
    r = owner.post(f"/api/v1/homes/{owner_home}/devices", json=body)
    assert r.status_code == 422, r.text


def test_esphome_device_takes_no_connection(owner, owner_home):
    r = owner.post(f"/api/v1/homes/{owner_home}/devices",
                   json={"key": "l", "name": "l", "adapter": "esphome", "protocol": "mqtt",
                         "capabilities": {"switch": {}}, "connection": {"profile": "switch"}})
    assert r.status_code == 422


def test_only_the_hub_gets_the_key_and_a_new_key_replaces_it(owner, owner_home, hub):
    d = owner.post(f"/api/v1/homes/{owner_home}/devices", json=tuya("rele_1")).json()["data"]
    cfg = hub.get("/api/v1/hub/config").json()["data"]
    dev = next(x for x in cfg["devices"] if x["key"] == "rele_1")
    assert dev["secret"] == LOCAL_KEY and dev["connection"]["ip"] == "192.168.1.50"
    r = owner.patch(f"/api/v1/devices/{d['id']}", json={"secret": "zzzzzzzzzzzzzzzz",
                                                        "connection": {**dev["connection"], "ip": "192.168.1.51"}})
    assert r.status_code == 200, r.text
    assert "zzzz" not in r.text
    dev = next(x for x in hub.get("/api/v1/hub/config").json()["data"]["devices"] if x["key"] == "rele_1")
    assert dev["secret"] == "zzzzzzzzzzzzzzzz" and dev["connection"]["ip"] == "192.168.1.51"
    # Renaming does not need the key again.
    assert owner.patch(f"/api/v1/devices/{d['id']}", json={"name": "Darvoza relesi"}).status_code == 200


def test_ir_remote_profile(owner, owner_home):
    r = owner.post(f"/api/v1/homes/{owner_home}/devices",
                   json=tuya("pult_zal", "ir", {"remote": {"layout": "tv"}}))
    assert r.status_code == 201, r.text
    cap = r.json()["data"]["capabilities"]["remote"]
    assert cap["config"]["layout"] == "tv" and cap["attributes"]["buttons"]["quality"] == "unknown"
