import uuid
from datetime import timedelta

import pytest

from app.db.types import utcnow
from conftest import LIGHT, Api

TS = lambda d=timedelta(0): (utcnow() + d).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731

RADAR = {"key": "garden_radar", "name": "Radar", "adapter": "esphome", "protocol": "mqtt",
         "capabilities": {"motion": {}}}
GATE = {"key": "front_gate", "name": "Darvoza", "adapter": "esphome", "protocol": "mqtt",
        "capabilities": {"cover": {}}}
VALVE = {"key": "garden_valve", "name": "Klapan", "adapter": "esphome", "protocol": "mqtt",
         "capabilities": {"valve": {"max_runtime_s": 900}}}


def rule(**over):
    d = {"triggers": [{"type": "state", "device": "garden_radar", "capability": "motion",
                       "attribute": "detected", "to": True}],
         "actions": [{"type": "command", "device": "garden_lights", "capability": "switch",
                      "action": "turn_on", "auto_off_after_s": 300},
                     {"type": "notify", "severity": "warning", "text": "Bog'da harakat"}],
         "cooldown_s": 120}
    d.update(over)
    return d


@pytest.fixture
def home(owner, owner_home, light):
    for body in (RADAR, GATE, VALVE):
        assert owner.post(f"/api/v1/homes/{owner_home}/devices", json=body).status_code == 201
    return owner_home


def post(owner, home, definition, name="Bog' chirog'i", enabled=True):
    return owner.post(f"/api/v1/homes/{home}/automations",
                      json={"name": name, "enabled": enabled, "definition": definition})


def errors(r):
    return " | ".join(str(x) for x in (r.json()["error"].get("details") or []))


def test_create_list_and_hub_config(owner, home, client, owner_home):
    r = post(owner, home, rule())
    assert r.status_code == 201, r.text
    a = r.json()["data"]
    assert a["version"] == 1 and a["enabled"] is True and a["last_run"] is None
    lst = owner.get(f"/api/v1/homes/{home}/automations").json()["data"]
    assert [x["name"] for x in lst] == ["Bog' chirog'i"]
    hub = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "h"}).json()["data"]
    cfg = Api(client, hub["hub_token"]).get("/api/v1/hub/config").json()["data"]
    assert [x["id"] for x in cfg["automations"]] == [a["id"]]
    assert cfg["automations"][0]["definition"]["cooldown_s"] == 120


@pytest.mark.parametrize("definition,needle", [
    (rule(triggers=[{"type": "state", "device": "nope", "capability": "motion",
                     "attribute": "detected", "to": True}]), "unknown device"),
    (rule(triggers=[{"type": "state", "device": "garden_radar", "capability": "motion",
                     "attribute": "detected", "to": "yes"}]), "not a valid motion.detected"),
    (rule(actions=[{"type": "command", "device": "front_gate", "capability": "cover",
                    "action": "open"}]), "high risk"),
    (rule(actions=[{"type": "command", "device": "garden_lights", "capability": "switch",
                    "action": "explode"}]), "no action"),
    (rule(actions=[{"type": "command", "device": "garden_valve", "capability": "valve",
                    "action": "open", "params": {}}]), "duration_s"),
    (rule(actions=[{"type": "command", "device": "garden_valve", "capability": "valve",
                    "action": "open", "params": {"duration_s": 1800}}]), "max_runtime_s"),
    (rule(actions=[{"type": "command", "device": "garden_lights", "capability": "dimmer",
                    "action": "set_brightness", "params": {"brightness": 50},
                    "auto_off_after_s": 60}]), "only for switch.turn_on"),
    (rule(conditions=[{"type": "sun", "is": "night"}]), "coordinates"),
    (rule(conditions=[{"type": "security_mode", "is": ["armed_away"]}]), "no security system"),
    ({"triggers": [], "actions": []}, ""),
])
def test_invalid_rules_are_refused(owner, home, definition, needle):
    r = post(owner, home, definition)
    assert r.status_code == 422, r.text
    assert needle in errors(r) or needle in r.json()["error"]["message"]


def test_sun_works_once_the_home_has_coordinates(owner, home):
    assert owner.patch(f"/api/v1/homes/{home}", json={"latitude": 41.31, "longitude": 69.28}).status_code == 200
    r = post(owner, home, rule(conditions=[{"type": "sun", "is": "night"}]))
    assert r.status_code == 201, r.text


def test_loops_are_refused(owner, home):
    # A: light on -> radar? (no). Build: A light.switch -> turns on light; B triggers on light.
    a = rule(triggers=[{"type": "state", "device": "garden_lights", "capability": "switch",
                        "attribute": "on", "to": True}],
             actions=[{"type": "command", "device": "garden_lights", "capability": "switch",
                       "action": "turn_off"}])
    r = post(owner, home, a, name="O'zini o'zi")
    assert r.status_code == 422 and "loop" in r.json()["error"]["message"]
    first = rule(triggers=[{"type": "state", "device": "garden_lights", "capability": "switch",
                            "attribute": "on", "to": True}],
                 actions=[{"type": "command", "device": "garden_lights", "capability": "dimmer",
                           "action": "set_brightness", "params": {"brightness": 30}}])
    assert post(owner, home, first, name="A").status_code == 201
    second = rule(triggers=[{"type": "state", "device": "garden_lights", "capability": "dimmer",
                             "attribute": "brightness", "to": 30}],
                  actions=[{"type": "command", "device": "garden_lights", "capability": "switch",
                            "action": "turn_on"}])
    r = post(owner, home, second, name="B")
    assert r.status_code == 422
    assert "A" in errors(r) and "B" in errors(r)
    # Disabled rules do not count: disable A, then B is fine.
    a_id = owner.get(f"/api/v1/homes/{home}/automations").json()["data"][0]["id"]
    assert owner.patch(f"/api/v1/automations/{a_id}", json={"enabled": False}).status_code == 200
    assert post(owner, home, second, name="B").status_code == 201
    # ...and re-enabling A would close the loop again.
    r = owner.patch(f"/api/v1/automations/{a_id}", json={"enabled": True})
    assert r.status_code == 422


def test_patch_bumps_version_and_permissions(owner, home, make_member):
    a = post(owner, home, rule()).json()["data"]
    r = owner.patch(f"/api/v1/automations/{a['id']}", json={"name": "Yangi nom"})
    assert r.json()["data"]["version"] == 2
    family = make_member("family")
    assert family.get(f"/api/v1/homes/{home}/automations").status_code == 200
    assert family.patch(f"/api/v1/automations/{a['id']}", json={"enabled": False}).status_code == 403
    assert post(family, home, rule()).status_code == 403
    assert family.delete(f"/api/v1/automations/{a['id']}").status_code == 403
    assert owner.delete(f"/api/v1/automations/{a['id']}").status_code == 200


def test_runs_from_hub_are_idempotent(owner, home, client, owner_home, outsider):
    a = post(owner, home, rule()).json()["data"]
    hub = Api(client, owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "h"}).json()["data"]["hub_token"])
    run = {"id": str(uuid.uuid4()), "automation_id": a["id"], "version": 1, "ts": TS(),
           "trigger": "garden_radar motion.detected = true", "result": "ok",
           "actions": [{"type": "command", "device": "garden_lights", "action": "turn_on",
                        "outcome": "confirmed"}]}
    r = hub.post("/api/v1/hub/automation-runs", json={"schema": 1, "runs": [run]})
    assert r.json()["data"] == {"accepted": 1, "duplicates": 0, "rejected": []}
    r = hub.post("/api/v1/hub/automation-runs", json={"schema": 1, "runs": [
        run, {**run, "id": str(uuid.uuid4()), "automation_id": str(uuid.uuid4())}]})
    assert r.json()["data"]["duplicates"] == 1 and len(r.json()["data"]["rejected"]) == 1
    runs = owner.get(f"/api/v1/automations/{a['id']}/runs").json()["data"]
    assert len(runs) == 1 and runs[0]["actions"][0]["outcome"] == "confirmed"
    got = owner.get(f"/api/v1/automations/{a['id']}").json()["data"]
    assert got["last_run"]["result"] == "ok"
    assert outsider.get(f"/api/v1/automations/{a['id']}").status_code == 404
