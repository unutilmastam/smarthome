import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import Device, DeviceState, Hub
from conftest import LIGHT


def _home(owner_home):
    return f"/api/v1/homes/{owner_home}"


def test_new_device_has_every_attribute_unknown(light):
    caps = light["capabilities"]
    assert set(caps) == {"switch", "dimmer"}
    assert set(caps["switch"]["attributes"]) == {"on"}
    for cap in caps.values():
        for v in cap["attributes"].values():
            assert v["value"] is None
            assert v["quality"] == "unknown"
            assert v["ts"] is None
    assert caps["dimmer"]["attributes"]["brightness"]["unit"] == "%"
    assert light["availability"]["status"] == "unknown"
    assert light["hub_online"] is False


def test_unsupported_attributes_are_marked(owner, owner_home):
    body = {"key": "main_meter", "name": "Hisoblagich", "adapter": "esphome",
            "protocol": "mqtt", "capabilities": {"power_meter": {"report_interval_s": 10}},
            "unsupported": ["power_meter.frequency", "power_meter.power_factor"]}
    r = owner.post(f"{_home(owner_home)}/devices", json=body)
    assert r.status_code == 201, r.text
    attrs = r.json()["data"]["capabilities"]["power_meter"]["attributes"]
    assert attrs["frequency"] == {"value": None, "unit": "Hz", "source": "reported",
                                  "quality": "not_supported", "ts": None}
    assert attrs["power_factor"]["quality"] == "not_supported"
    assert attrs["voltage"]["quality"] == "unknown"


def test_validation_against_contracts(owner, owner_home):
    url = f"{_home(owner_home)}/devices"
    bad = [
        {**LIGHT, "capabilities": {"teleporter": {}}},
        {**LIGHT, "capabilities": {}},
        {**LIGHT, "unsupported": ["switch.brightness"]},
        {**LIGHT, "unsupported": ["climate.mode"]},
        {**LIGHT, "capabilities": {"switch": {"report_interval_s": -5}}},
        {**LIGHT, "capabilities": {"switch": {"colour": "red"}}},
        {**LIGHT, "key": "Bad Key"},
    ]
    for body in bad:
        r = owner.post(url, json=body)
        assert r.status_code == 422, body
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_duplicate_key_conflict(owner, owner_home, light):
    r = owner.post(f"{_home(owner_home)}/devices", json=LIGHT)
    assert r.status_code == 409


def _set_state(dbs, device_id, cap, attr, value, quality="good", source="reported", ts=None):
    dbs.merge(DeviceState(device_id=uuid.UUID(device_id), capability=cap, attribute=attr,
                          value_json=value, source=source, quality=quality,
                          ts=ts or datetime.now(timezone.utc)))
    dbs.commit()


def _online_hub(owner, owner_home, dbs):
    hub = owner.post(f"{_home(owner_home)}/hubs", json={"name": "hub"}).json()["data"]
    h = dbs.get(Hub, uuid.UUID(hub["id"]))
    h.last_seen = datetime.now(timezone.utc)
    dbs.commit()
    return h


def test_states_good_when_hub_online(owner, owner_home, light, dbs):
    _online_hub(owner, owner_home, dbs)
    d = dbs.get(Device, uuid.UUID(light["id"]))
    d.availability = "online"
    dbs.commit()
    _set_state(dbs, light["id"], "switch", "on", True)
    r = owner.get(f"/api/v1/devices/{light['id']}").json()["data"]
    assert r["hub_online"] is True
    assert r["availability"]["status"] == "online"
    on = r["capabilities"]["switch"]["attributes"]["on"]
    assert on["value"] is True and on["quality"] == "good" and on["ts"].endswith("Z")
    assert r["capabilities"]["dimmer"]["attributes"]["brightness"]["quality"] == "unknown"


def test_hub_offline_makes_values_stale_and_availability_unknown(owner, owner_home, light, dbs):
    hub = _online_hub(owner, owner_home, dbs)
    hub.last_seen = datetime.now(timezone.utc) - timedelta(minutes=10)
    d = dbs.get(Device, uuid.UUID(light["id"]))
    d.availability = "online"
    dbs.commit()
    _set_state(dbs, light["id"], "switch", "on", True)
    r = owner.get(f"/api/v1/devices/{light['id']}").json()["data"]
    assert r["hub_online"] is False
    assert r["availability"]["status"] == "unknown"
    on = r["capabilities"]["switch"]["attributes"]["on"]
    assert on["quality"] == "stale" and on["value"] is True


def test_no_hub_at_all_is_unknown_availability(owner, light, dbs):
    _set_state(dbs, light["id"], "switch", "on", False)
    r = owner.get(f"/api/v1/devices/{light['id']}").json()["data"]
    assert r["availability"]["status"] == "unknown"
    assert r["capabilities"]["switch"]["attributes"]["on"]["quality"] == "stale"


def test_old_telemetry_becomes_stale(owner, owner_home, dbs):
    body = {"key": "temp1", "name": "Harorat", "adapter": "esphome", "protocol": "mqtt",
            "capabilities": {"environment": {"report_interval_s": 60}}}
    dev = owner.post(f"{_home(owner_home)}/devices", json=body).json()["data"]
    _online_hub(owner, owner_home, dbs)
    d = dbs.get(Device, uuid.UUID(dev["id"]))
    d.availability = "online"
    dbs.commit()
    now = datetime.now(timezone.utc)
    _set_state(dbs, dev["id"], "environment", "temperature", 21.5, ts=now - timedelta(seconds=30))
    _set_state(dbs, dev["id"], "environment", "humidity", 40, ts=now - timedelta(seconds=200))
    attrs = owner.get(f"/api/v1/devices/{dev['id']}").json()["data"][
        "capabilities"]["environment"]["attributes"]
    assert attrs["temperature"]["quality"] == "good"
    assert attrs["humidity"]["quality"] == "stale"
    assert attrs["soil_moisture"]["quality"] == "unknown"


def test_assumed_source_preserved(owner, owner_home, dbs):
    body = {"key": "ac_bedroom", "name": "Konditsioner", "adapter": "esphome",
            "protocol": "mqtt", "capabilities": {"climate": {}}}
    dev = owner.post(f"{_home(owner_home)}/devices", json=body).json()["data"]
    _online_hub(owner, owner_home, dbs)
    d = dbs.get(Device, uuid.UUID(dev["id"]))
    d.availability = "online"
    dbs.commit()
    _set_state(dbs, dev["id"], "climate", "power", True, source="assumed")
    p = owner.get(f"/api/v1/devices/{dev['id']}").json()["data"]["capabilities"][
        "climate"]["attributes"]["power"]
    assert p["source"] == "assumed" and p["quality"] == "good"


def test_list_filters_and_pagination(owner, owner_home, light):
    url = f"{_home(owner_home)}/devices"
    room = owner.post(f"{_home(owner_home)}/rooms", json={"name": "Bog'", "type": "outdoor"}
                      ).json()["data"]
    for i in range(3):
        body = {"key": f"sensor_{i}", "name": f"Sensor {i}", "adapter": "esphome",
                "protocol": "mqtt", "capabilities": {"motion": {}}, "room_id": room["id"]}
        assert owner.post(url, json=body).status_code == 201
    all_ = owner.get(url).json()
    assert all_["meta"]["total"] == 4
    assert owner.get(url, params={"room_id": room["id"]}).json()["meta"]["total"] == 3
    assert owner.get(url, params={"capability": "switch"}).json()["meta"]["total"] == 1
    assert owner.get(url, params={"q": "SENSOR"}).json()["meta"]["total"] == 3
    page = owner.get(url, params={"limit": 2, "offset": 2}).json()
    assert len(page["data"]) == 2 and page["meta"] == {"limit": 2, "offset": 2, "total": 4}
    assert owner.get(url, params={"availability": "unknown"}).json()["meta"]["total"] == 4
    assert owner.get(url, params={"limit": 500}).status_code == 422


def test_patch_device_capabilities_and_room(owner, owner_home, light, dbs):
    _set_state(dbs, light["id"], "dimmer", "brightness", 50)
    room = owner.post(f"{_home(owner_home)}/rooms", json={"name": "Zal"}).json()["data"]
    r = owner.patch(f"/api/v1/devices/{light['id']}",
                    json={"capabilities": {"switch": {}}, "room_id": room["id"]})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert set(data["capabilities"]) == {"switch"}
    assert data["room_id"] == room["id"]
    assert dbs.scalars(select(DeviceState).where(DeviceState.capability == "dimmer")).all() == []
    r = owner.patch(f"/api/v1/devices/{light['id']}", json={"room_id": None})
    assert r.json()["data"]["room_id"] is None
    r = owner.patch(f"/api/v1/devices/{light['id']}", json={"unsupported": ["dimmer.brightness"]})
    assert r.status_code == 422


def test_delete_device(owner, light):
    assert owner.delete(f"/api/v1/devices/{light['id']}").status_code == 200
    assert owner.get(f"/api/v1/devices/{light['id']}").status_code == 404


def test_rooms_and_floors_crud(owner, owner_home):
    h = _home(owner_home)
    floor = owner.post(f"{h}/floors", json={"name": "1-qavat", "level": 1}).json()["data"]
    room = owner.post(f"{h}/rooms", json={"name": "Yotoqxona", "floor_id": floor["id"]}
                      ).json()["data"]
    assert room["floor_id"] == floor["id"] and room["type"] == "indoor"
    assert owner.post(f"{h}/rooms", json={"name": "X", "type": "attic"}).status_code == 422
    r = owner.patch(f"/api/v1/rooms/{room['id']}", json={"type": "outdoor"})
    assert r.json()["data"]["type"] == "outdoor"
    assert owner.delete(f"/api/v1/floors/{floor['id']}").status_code == 200
    assert owner.get(f"/api/v1/rooms/{room['id']}").json()["data"]["floor_id"] is None
    assert owner.get(f"{h}/floors").json()["meta"]["total"] == 0


def test_home_patch_and_validation(owner, owner_home):
    h = _home(owner_home)
    assert owner.patch(h, json={"timezone": "Mars/Base"}).status_code == 422
    assert owner.patch(h, json={"latitude": 41.3}).status_code == 422
    r = owner.patch(h, json={"latitude": 41.31, "longitude": 69.28, "name": "Uyim"})
    assert r.status_code == 200
    d = r.json()["data"]
    assert (d["latitude"], d["longitude"], d["name"]) == (41.31, 69.28, "Uyim")
    assert d["timezone"] == "Asia/Tashkent"
    assert owner.post("/api/v1/homes", json={"name": "X", "latitude": 1}).status_code == 422
