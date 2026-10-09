"""Phase 12: automations on the hub, full chain [SIM].
Rule stored and validated by the backend -> hub config -> motion sensor -> light confirmed;
works with the internet down; a person's command wins over the automation."""

import asyncio

import pytest

from conftest import add_backend_to_path
from test_integration import Stack, run

add_backend_to_path()

from simulator.devices import LightSim, MotionSim  # noqa: E402

DEVICES = {
    "garden_lights": {"capabilities": {"switch": {}, "dimmer": {}}},
    "garden_radar": {"capabilities": {"motion": {}}},
}
RULE = {"triggers": [{"type": "state", "device": "garden_radar", "capability": "motion",
                      "attribute": "detected", "to": True}],
        "actions": [{"type": "command", "device": "garden_lights", "capability": "switch",
                     "action": "turn_on"},
                    {"type": "notify", "severity": "warning", "text": "Bog'da harakat"}],
        "cooldown_s": 0, "manual_override_s": 600}


def sims(kw):
    return {"garden_lights": LightSim("garden_lights", **kw),
            "garden_radar": MotionSim("garden_radar", **kw)}


@pytest.fixture
def stack(broker, tmp_path):
    st = Stack(broker, tmp_path, devices=DEVICES, make_sims=sims)
    r = st.phone.post(f"/api/v1/homes/{st.home_id}/automations",
                      json={"name": "Bog' chirog'i", "definition": RULE})
    assert r.status_code == 201, r.text
    st.automation_id = r.json()["data"]["id"]
    return st


def runs(st):
    return st.phone.get(f"/api/v1/automations/{st.automation_id}/runs").json()["data"]


def test_motion_turns_light_on_offline_and_history_arrives_later(stack):
    async def scenario(st):
        light, radar = st.sims["garden_lights"], st.sims["garden_radar"]
        await st.wait(lambda: st.gateway.automations.rules, "rules loaded on the hub")
        await st.wait(lambda: ("garden_radar", "motion", "detected") in st.gateway.automations.seen,
                      "radar state seen")
        st.transport.down = True                       # internet gone
        await asyncio.to_thread(radar.trigger, True)
        await st.wait(lambda: light.state.get("switch", {}).get("on") is True,
                      "light switched on by the hub, offline")
        await st.wait(lambda: st.gateway.store.peek("automation_run", 1), "run buffered")
        assert runs(st) == []                          # cloud does not know yet
        st.transport.down = False
        await st.wait(lambda: runs(st), "run history uploaded after reconnect")
        r = runs(st)[0]
        assert r["result"] == "ok" and r["version"] == 1
        assert r["actions"][0] == {"type": "command", "device": "garden_lights",
                                   "action": "turn_on", "outcome": "confirmed"}
        assert r["actions"][1]["outcome"] == "recorded"
        # The hub-local command never shows up as a cloud command.
        cmds = st.phone.get(f"/api/v1/devices/{st.ids['garden_lights']}/commands").json()["data"]
        assert cmds == []
    run(stack, scenario)


def test_a_persons_command_wins_over_the_automation(stack):
    async def scenario(st):
        light, radar = st.sims["garden_lights"], st.sims["garden_radar"]
        await st.wait(lambda: st.gateway.automations.rules, "rules loaded on the hub")
        r = await st.send("garden_lights", "switch", "turn_off")       # a person decides
        await st.wait_status(r.json()["data"]["id"], {"confirmed"})
        await asyncio.to_thread(radar.trigger, True)
        await st.wait(lambda: runs(st), "run recorded")
        rr = runs(st)[0]
        assert (rr["result"], rr["reason"]) == ("skipped", "manual_override")
        await asyncio.sleep(0.5)
        assert light.state["switch"]["on"] is False
    run(stack, scenario)


def test_disabling_the_rule_stops_it_on_the_hub(stack):
    async def scenario(st):
        radar, light = st.sims["garden_radar"], st.sims["garden_lights"]
        await st.wait(lambda: st.gateway.automations.rules, "rules loaded")
        st.phone.patch(f"/api/v1/automations/{st.automation_id}", json={"enabled": False})
        await st.wait(lambda: not st.gateway.automations.rules, "rule removed on next config sync")
        await asyncio.to_thread(radar.trigger, True)
        await asyncio.sleep(1.0)
        assert light.state["switch"]["on"] is False
        assert runs(st) == []
    run(stack, scenario)
