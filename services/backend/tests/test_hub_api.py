from datetime import timedelta

import pytest

from app.db.types import utcnow
from conftest import Api

TS = lambda d=timedelta(0): (utcnow() + d).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731


@pytest.fixture
def hub(client, owner, owner_home):
    data = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "hub"}).json()["data"]
    api = Api(client, data["hub_token"])
    api.info = data
    return api


def val(v, q="good", src="reported", ts=None):
    return {"value": v, "source": src, "quality": q, "ts": ts or TS()}


def test_heartbeat_marks_hub_online(owner, owner_home, hub):
    hubs = owner.get(f"/api/v1/homes/{owner_home}/hubs").json()["data"]
    assert hubs[0]["online"] is False
    r = hub.post("/api/v1/hub/heartbeat", json={"version": "0.4.0"})
    assert r.status_code == 200 and r.json()["data"]["server_time"].endswith("Z")
    hubs = owner.get(f"/api/v1/homes/{owner_home}/hubs").json()["data"]
    assert hubs[0]["online"] is True and hubs[0]["version"] == "0.4.0"


def test_config_lists_devices(hub, light):
    data = hub.get("/api/v1/hub/config").json()["data"]
    assert data["home"]["timezone"] == "Asia/Tashkent"
    assert [d["key"] for d in data["devices"]] == ["garden_lights"]
    assert set(data["devices"][0]["capabilities"]) == {"switch", "dimmer"}
    assert "hub_token" not in str(data)


def test_report_updates_state_and_availability(owner, hub, light):
    report = {"schema": 1, "ts": TS(), "devices": [{
        "device_key": "garden_lights", "availability": "online",
        "states": {"switch": {"on": val(True)}, "dimmer": {"brightness": val(40)}}}]}
    r = hub.post("/api/v1/hub/report", json=report)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["devices"] == [{"device_key": "garden_lights", "result": "ok"}]
    d = owner.get(f"/api/v1/devices/{light['id']}").json()["data"]
    assert d["availability"]["status"] == "online"
    assert d["capabilities"]["switch"]["attributes"]["on"]["value"] is True
    assert d["capabilities"]["switch"]["attributes"]["on"]["quality"] == "good"
    assert d["capabilities"]["dimmer"]["attributes"]["brightness"]["value"] == 40


def test_report_rejects_bad_values(owner, hub, light):
    report = {"schema": 1, "ts": TS(), "devices": [
        {"device_key": "garden_lights", "states": {
            "dimmer": {"brightness": val(500)},
            "switch": {"on": val("yes")},
            "climate": {"power": val(True)},
        }},
        {"device_key": "ghost", "availability": "online"},
    ]}
    r = hub.post("/api/v1/hub/report", json=report).json()["data"]["devices"]
    assert r[0]["result"] == "error" and len(r[0]["errors"]) == 3
    assert r[1] == {"device_key": "ghost", "result": "unknown_device"}
    d = owner.get(f"/api/v1/devices/{light['id']}").json()["data"]
    assert d["capabilities"]["dimmer"]["attributes"]["brightness"]["quality"] == "unknown"


def test_report_schema_violations_are_422(hub, light):
    bad = {"schema": 1, "ts": TS(), "devices": [{"device_key": "garden_lights", "states": {
        "switch": {"on": {"value": 1, "source": "reported", "quality": "unknown", "ts": None}}}}]}
    assert hub.post("/api/v1/hub/report", json=bad).status_code == 422
    assert hub.post("/api/v1/hub/report", json={"devices": []}).status_code == 422


def test_report_future_ts_and_older_values(owner, hub, light):
    hub.post("/api/v1/hub/report", json={"schema": 1, "ts": TS(), "devices": [
        {"device_key": "garden_lights", "states": {"switch": {"on": val(True)}}}]})
    r = hub.post("/api/v1/hub/report", json={"schema": 1, "ts": TS(), "devices": [
        {"device_key": "garden_lights",
         "states": {"switch": {"on": val(False, ts=TS(timedelta(minutes=10)))}}}]})
    assert r.json()["data"]["devices"][0]["result"] == "error"
    hub.post("/api/v1/hub/report", json={"schema": 1, "ts": TS(), "devices": [
        {"device_key": "garden_lights",
         "states": {"switch": {"on": val(False, ts=TS(-timedelta(minutes=5)))}}}]})
    d = owner.get(f"/api/v1/devices/{light['id']}").json()["data"]
    assert d["capabilities"]["switch"]["attributes"]["on"]["value"] is True


def test_report_cannot_override_not_supported(owner, owner_home, hub):
    body = {"key": "main_meter", "name": "M", "adapter": "esphome", "protocol": "mqtt",
            "capabilities": {"power_meter": {}}, "unsupported": ["power_meter.frequency"]}
    dev = owner.post(f"/api/v1/homes/{owner_home}/devices", json=body).json()["data"]
    r = hub.post("/api/v1/hub/report", json={"schema": 1, "ts": TS(), "devices": [
        {"device_key": "main_meter", "states": {"power_meter": {
            "frequency": val(50.0), "voltage": val(229.8)}}}]})
    assert r.json()["data"]["devices"][0]["result"] == "error"
    d = owner.get(f"/api/v1/devices/{dev['id']}").json()["data"]
    attrs = d["capabilities"]["power_meter"]["attributes"]
    assert attrs["frequency"]["quality"] == "not_supported"
    assert attrs["voltage"]["value"] == 229.8


def test_report_for_other_home_device_key_is_unknown(hub, outsider, client):
    other_home = outsider.get("/api/v1/homes").json()["data"][0]["id"]
    outsider.post(f"/api/v1/homes/{other_home}/devices", json={
        "key": "their_lamp", "name": "x", "adapter": "esphome", "protocol": "mqtt",
        "capabilities": {"switch": {}}})
    r = hub.post("/api/v1/hub/report", json={"schema": 1, "ts": TS(), "devices": [
        {"device_key": "their_lamp", "availability": "online"}]})
    assert r.json()["data"]["devices"][0]["result"] == "unknown_device"
