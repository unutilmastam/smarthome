"""ADR 0016 section 3: Yandex Alisa devices through the Smart Home API, against a fake
Yandex (httpx.MockTransport). Shown = what Yandex reports; confirmed = read back."""

import json
import uuid

import httpx
import pytest

from app.services import yandex

TOKEN = "y0_fakefakefakefakefakefakefake"
LAMP = "11111111-2222-3333-4444-555555555555"
TV = "22222222-2222-3333-4444-555555555555"
AC = "33333333-2222-3333-4444-555555555555"
STATION = "44444444-2222-3333-4444-555555555555"


class FakeYandex:
    def __init__(self):
        self.calls = []
        self.lamp_on = False
        self.ignore = False            # Yandex says DONE but the lamp does not change
        self.token_ok = True
        self.fail = None

    def device(self, yid):
        if yid == LAMP:
            return {"id": LAMP, "name": "Alisa chirog'i", "type": "devices.types.light", "room": "r1", "state": "online",
                    "capabilities": [
                        {"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": self.lamp_on}, "last_updated": 1791500000},
                        {"type": "devices.capabilities.range", "state": {"instance": "brightness", "value": 70}, "last_updated": 1791500000}],
                    "properties": []}
        if yid == TV:
            return {"id": TV, "name": "Yandex TV", "type": "devices.types.media_device.tv", "state": "online",
                    "capabilities": [
                        {"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": True}},
                        {"type": "devices.capabilities.range", "parameters": {"instance": "volume"}, "state": None},
                        {"type": "devices.capabilities.range", "parameters": {"instance": "channel"}, "state": None},
                        {"type": "devices.capabilities.toggle", "parameters": {"instance": "mute"}, "state": None}],
                    "properties": []}
        if yid == AC:
            return {"id": AC, "name": "Konditsioner", "type": "devices.types.thermostat.ac", "state": "offline",
                    "capabilities": [
                        {"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": False}},
                        {"type": "devices.capabilities.range", "state": {"instance": "temperature", "value": 24}},
                        {"type": "devices.capabilities.mode", "state": {"instance": "thermostat", "value": "fan_only"}}],
                    "properties": [{"type": "devices.properties.float", "state": {"instance": "temperature", "value": 27.5}}]}
        return {"id": STATION, "name": "Yandex Stansiya", "type": "devices.types.smart_speaker.yandex.station",
                "capabilities": [], "properties": []}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path, request.content and json.loads(request.content)))
        if request.headers.get("Authorization") != f"Bearer {TOKEN}" or not self.token_ok:
            return httpx.Response(401, json={"status": "error", "message": "unauthorized"})
        if self.fail:
            raise httpx.ConnectError("down")
        path = request.url.path
        if path.endswith("/user/info"):
            return httpx.Response(200, json={"status": "ok", "rooms": [{"id": "r1", "name": "Zal"}],
                                             "devices": [self.device(x) for x in (LAMP, TV, AC, STATION)],
                                             "scenarios": [{"id": "sc1", "name": "Kino rejimi", "is_active": True}]})
        if path.endswith("/devices/actions"):
            body = json.loads(request.content)
            act = body["devices"][0]["actions"][0]
            if not self.ignore and act["type"].endswith("on_off"):
                self.lamp_on = act["state"]["value"]
            return httpx.Response(200, json={"status": "ok", "devices": [{"id": body["devices"][0]["id"], "capabilities": [
                {"type": act["type"], "state": {"instance": act["state"]["instance"], "action_result": {"status": "DONE"}}}]}]})
        if "/devices/" in path:
            return httpx.Response(200, json={"status": "ok", **self.device(path.rsplit("/", 1)[1])})
        if "/scenarios/" in path:
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404, json={"status": "error"})


@pytest.fixture
def fake(monkeypatch):
    f = FakeYandex()
    monkeypatch.setattr(yandex, "TRANSPORT", httpx.MockTransport(f))
    return f


@pytest.fixture
def linked(owner, owner_home, fake):
    owner.post(f"/api/v1/homes/{owner_home}/rooms", json={"name": "Zal"})
    r = owner.put(f"/api/v1/homes/{owner_home}/integrations/yandex", json={"token": TOKEN})
    assert r.status_code == 200, r.text
    return r.json()["data"]


def devices(owner, home):
    return {d["name"]: d for d in owner.get(f"/api/v1/homes/{home}/devices").json()["data"]}


def test_link_imports_what_maps_and_never_returns_the_token(owner, owner_home, linked, fake):
    assert linked["status"] == "ok" and TOKEN not in json.dumps(linked)
    assert linked["scenarios"] == [{"id": "sc1", "name": "Kino rejimi"}]
    assert [s["name"] for s in linked["skipped"]] == ["Yandex Stansiya"]   # nothing we can control honestly
    ds = devices(owner, owner_home)
    lamp = ds["Alisa chirog'i"]
    assert lamp["adapter"] == "yandex" and lamp["hub_online"] is True and lamp["room_id"]
    assert lamp["capabilities"]["switch"]["attributes"]["on"]["value"] is False
    assert lamp["capabilities"]["switch"]["attributes"]["on"]["quality"] == "good"
    assert lamp["capabilities"]["dimmer"]["attributes"]["brightness"]["value"] == 70
    tv = ds["Yandex TV"]["capabilities"]["media"]["attributes"]
    assert tv["on"]["value"] is True and tv["volume"]["quality"] == "unknown"   # Yandex gave no value
    ac = ds["Konditsioner"]
    assert ac["availability"]["status"] == "offline"
    assert ac["capabilities"]["climate"]["attributes"]["mode"]["value"] == "fan"
    assert ac["capabilities"]["climate"]["attributes"]["current_temp"]["value"] == 27.5
    assert TOKEN not in owner.get(f"/api/v1/homes/{owner_home}/integrations/yandex").text


def command(owner, device, cap, action, params=None):
    r = owner.post("/api/v1/commands", json={"device_id": device["id"], "capability": cap, "action": action,
                                              "params": params or {}, "idempotency_key": str(uuid.uuid4())})
    assert r.status_code in (200, 201), r.text
    return r.json()["data"]


def test_command_confirmed_only_when_yandex_shows_the_new_state(owner, owner_home, linked, fake):
    lamp = devices(owner, owner_home)["Alisa chirog'i"]
    c = command(owner, lamp, "switch", "turn_on")
    assert c["status"] == "confirmed"
    sent = [b for m, pth, b in fake.calls if pth.endswith("/devices/actions")][-1]
    assert sent["devices"][0]["actions"][0]["state"] == {"instance": "on", "value": True}
    fake.ignore = True
    c = command(owner, lamp, "switch", "turn_off")
    assert c["status"] == "acked"       # Yandex said DONE, but the lamp still reports "on"


def test_tv_relative_volume_and_failures(owner, owner_home, linked, fake):
    tv = devices(owner, owner_home)["Yandex TV"]
    c = command(owner, tv, "media", "volume_up")
    sent = [b for m, pth, b in fake.calls if pth.endswith("/devices/actions")][-1]
    assert sent["devices"][0]["actions"][0]["state"] == {"instance": "volume", "value": 1, "relative": True}
    assert c["status"] == "acked"        # nothing to read back for a relative step
    fake.fail = True
    c = command(owner, tv, "media", "turn_off")
    assert c["status"] == "failed" and c["reason"] == "device_offline"


def test_bad_token_is_reported_not_hidden(owner, owner_home, fake):
    r = owner.put(f"/api/v1/homes/{owner_home}/integrations/yandex", json={"token": "y0_wrongwrongwrongwrongwrong"})
    assert r.json()["data"]["status"] == "error" and "token_invalid" in r.json()["data"]["error"]


def test_scenario_run_and_disconnect(owner, owner_home, linked, fake, make_member):
    assert owner.post(f"/api/v1/homes/{owner_home}/integrations/yandex/scenarios/sc1/run").status_code == 200
    assert owner.post(f"/api/v1/homes/{owner_home}/integrations/yandex/scenarios/nope/run").status_code == 404
    viewer = make_member("viewer")
    assert viewer.post(f"/api/v1/homes/{owner_home}/integrations/yandex/scenarios/sc1/run").status_code == 403
    assert viewer.put(f"/api/v1/homes/{owner_home}/integrations/yandex", json={"token": TOKEN}).status_code == 403
    assert owner.delete(f"/api/v1/homes/{owner_home}/integrations/yandex").status_code == 200
    lamp = devices(owner, owner_home)["Alisa chirog'i"]
    assert lamp["hub_online"] is False                    # not reachable any more, never "fresh"
    assert lamp["capabilities"]["switch"]["attributes"]["on"]["quality"] == "stale"


def test_yandex_devices_cannot_be_created_by_hand(owner, owner_home):
    r = owner.post(f"/api/v1/homes/{owner_home}/devices", json={
        "key": "ya_x", "name": "x", "adapter": "yandex", "protocol": "cloud", "capabilities": {"switch": {}}})
    assert r.status_code == 422
