"""Phase 11 failure scenarios, full chain [SIM]:
phone -> backend -> hub gateway -> real Mosquitto (ACL) -> simulated devices.

Gate (reed + photocell), IR climate (current sensor), irrigation (flow sensor,
firmware limits), security system on the hub (zones, delays, siren, offline).
"""

import asyncio
from datetime import timedelta

import pytest

from conftest import add_backend_to_path
from test_integration import PIN, Stack, run

add_backend_to_path()

from gateway.timeutil import utcnow  # noqa: E402
from simulator.devices import (  # noqa: E402
    ContactSim, GateSim, IRClimateSim, MotionSim, SirenSim, ValveSim,
)

DEVICES = {
    "front_gate": {"capabilities": {"cover": {"confirm_timeout_s": 4, "left_open_after_s": 600}}},
    "ac_living": {"capabilities": {"climate": {"confirm_timeout_s": 3}}},
    "ac_bedroom": {"capabilities": {"climate": {"confirm_timeout_s": 3}}},
    "garden_valve": {"capabilities": {"valve": {"max_runtime_s": 600, "confirm_timeout_s": 2}}},
    "front_door": {"capabilities": {"contact": {}}},
    "back_window": {"capabilities": {"contact": {}}},
    "hall_motion": {"capabilities": {"motion": {}}},
    "siren": {"capabilities": {"switch": {}}},
    "security": {"adapter": "hub", "protocol": "virtual", "capabilities": {"alarm": {
        "zones": [
            {"device_key": "front_door", "capability": "contact", "mode": "entry"},
            {"device_key": "back_window", "capability": "contact", "mode": "instant"},
            {"device_key": "hall_motion", "capability": "motion", "mode": "instant"},
        ],
        "sirens": ["siren"], "exit_delay_s": 1, "entry_delay_s": 1, "siren_max_s": 60}}},
}


def sims(kw):
    return {
        "front_gate": GateSim("front_gate", travel_time_s=1.0, **kw),
        "ac_living": IRClimateSim("ac_living", current_sensor=True, start_delay_s=0.3, **kw),
        "ac_bedroom": IRClimateSim("ac_bedroom", current_sensor=True, **kw),
        "garden_valve": ValveSim("garden_valve", max_runtime_s=1, no_flow_s=0.5, **kw),
        "front_door": ContactSim("front_door", **kw),
        "back_window": ContactSim("back_window", **kw),
        "hall_motion": MotionSim("hall_motion", **kw),
        "siren": SirenSim("siren", **kw),
    }


@pytest.fixture
def stack(broker, tmp_path):
    return Stack(broker, tmp_path, devices=DEVICES, make_sims=sims)


FINAL = {"confirmed", "failed", "rejected", "timeout", "expired"}


def attr(st, key, cap, a):
    return st.device(key)["capabilities"][cap]["attributes"][a]


def events(st, **params):
    return st.phone.get(f"/api/v1/homes/{st.home_id}/events", params=params).json()["data"]


async def wait_event(st, type_, timeout=10.0):
    return await st.wait(lambda: next((e for e in events(st) if e["type"] == type_), None),
                         f"event {type_} in backend", timeout)


async def cmd(st, key, cap, action, params=None, final=FINAL, timeout=10.0, **extra):
    r = await st.send(key, cap, action, params, **extra)
    assert r.status_code == 201, r.text
    return await st.wait_status(r.json()["data"]["id"], final, timeout)


# ---- gate -------------------------------------------------------------------------------

def test_gate_photocell_reopens_and_blocks_close(stack):
    async def scenario(st):
        gate = st.sims["front_gate"]
        assert (await cmd(st, "front_gate", "cover", "open", confirm_pin=PIN))["status"] == "confirmed"
        gate.travel = 3.0   # slow enough that the beam is surely cut mid-travel on a busy CI
        r = await st.send("front_gate", "cover", "close", confirm_pin=PIN)
        cid = r.json()["data"]["id"]
        await st.wait(lambda: gate.state["cover"]["state"] == "closing", "gate closing")
        await asyncio.to_thread(gate.set_obstructed, True)       # a child walks in
        c = await st.wait_status(cid, FINAL)
        assert (c["status"], c["reason"]) == ("failed", "no_feedback")   # never "closed"
        await st.wait(lambda: gate.state["cover"]["state"] == "open", "controller reopened")
        gate.travel = 1.0
        ev = await wait_event(st, "cover.obstructed")
        assert ev["severity"] == "warning" and ev["device_name"] == "front_gate"
        assert attr(st, "front_gate", "cover", "obstructed")["value"] is True
        # Firmware refuses to close while the beam is interrupted.
        c = await cmd(st, "front_gate", "cover", "close", confirm_pin=PIN)
        assert (c["status"], c["reason"]) == ("rejected", "safety_rule")
        await asyncio.to_thread(gate.set_obstructed, False)
        assert (await cmd(st, "front_gate", "cover", "close", confirm_pin=PIN))["status"] == "confirmed"
    run(stack, scenario)


def test_gate_reed_conflict_and_travel_timeout(stack):
    async def scenario(st):
        gate = st.sims["front_gate"]
        await st.wait(lambda: attr(st, "front_gate", "cover", "state")["value"] == "closed",
                      "initial reed state")
        gate.set_fault("stuck")
        c = await cmd(st, "front_gate", "cover", "open", confirm_pin=PIN)
        assert (c["status"], c["reason"]) == ("failed", "no_feedback")
        assert (await wait_event(st, "cover.travel_timeout"))["data"] == {"target": "open"}
        await asyncio.to_thread(gate.set_fault, "reed_conflict")
        ev = await wait_event(st, "cover.sensor_conflict")
        assert ev["severity"] == "critical"
        await st.wait(lambda: attr(st, "front_gate", "cover", "state")["value"] == "unknown",
                      "state unknown, not guessed")
        c = await cmd(st, "front_gate", "cover", "open", confirm_pin=PIN)
        assert (c["status"], c["reason"]) == ("rejected", "safety_rule")
    run(stack, scenario)


def test_gate_left_open_warning(stack):
    async def scenario(st):
        assert (await cmd(st, "front_gate", "cover", "open", confirm_pin=PIN))["status"] == "confirmed"
        st.gateway.watch_tick(utcnow() + timedelta(seconds=300))
        await asyncio.sleep(0.5)
        assert not [e for e in events(st) if e["type"] == "cover.left_open"]
        st.gateway.watch_tick(utcnow() + timedelta(seconds=620))
        ev = await wait_event(st, "cover.left_open")
        assert ev["severity"] == "warning" and ev["data"]["open_s"] >= 600
    run(stack, scenario)


# ---- climate ------------------------------------------------------------------------------

def test_ir_climate_confirmed_only_by_current_sensor(stack):
    async def scenario(st):
        c = await cmd(st, "ac_living", "climate", "set_power", {"power": True})
        assert c["status"] == "confirmed"
        await st.wait(lambda: attr(st, "ac_living", "climate", "power")["source"] == "assumed",
                      "assumed power reported")
        await st.wait(lambda: attr(st, "ac_living", "climate", "running")["value"] is True,
                      "current sensor reported running")
        assert attr(st, "ac_living", "climate", "running")["source"] == "reported"
        c = await cmd(st, "ac_living", "climate", "set_power", {"power": False})
        assert c["status"] == "confirmed"
    run(stack, scenario)


def test_ir_signal_lost_is_not_confirmed_and_warns(stack):
    async def scenario(st):
        st.sims["ac_bedroom"].set_fault("ir_blocked")
        await cmd(st, "ac_bedroom", "climate", "set_mode", {"mode": "cool"}, final={"acked"})
        r = await st.send("ac_bedroom", "climate", "set_power", {"power": True})
        cid = r.json()["data"]["id"]
        await st.wait_status(cid, {"acked"})
        await asyncio.sleep(3.5)                               # confirm window passes
        assert st.command(cid)["status"] == "acked"            # honest: not confirmed
        assert attr(st, "ac_bedroom", "climate", "power")["value"] is True       # assumed
        assert attr(st, "ac_bedroom", "climate", "running")["value"] is False    # reality
        st.gateway.watch_tick(utcnow() + timedelta(seconds=901))
        ev = await wait_event(st, "climate.no_effect")
        assert ev["data"]["mode"] == "cool"
    run(stack, scenario)


# ---- irrigation ------------------------------------------------------------------------

def test_valve_no_water_fails_and_firmware_closes(stack):
    async def scenario(st):
        valve = st.sims["garden_valve"]
        valve.set_fault("no_water")
        c = await cmd(st, "garden_valve", "valve", "open", {"duration_s": 60})
        assert (c["status"], c["reason"]) == ("failed", "no_feedback")   # open, but no flow
        assert await asyncio.to_thread(valve.closed_by_firmware.wait, 5)
        await wait_event(st, "valve.no_flow")
        await st.wait(lambda: attr(st, "garden_valve", "valve", "open")["value"] is False,
                      "closed state reported")
    run(stack, scenario)


def test_firmware_runtime_limit_wins_over_cloud_config(stack):
    async def scenario(st):
        valve = st.sims["garden_valve"]                         # firmware max_runtime = 1 s
        c = await cmd(st, "garden_valve", "valve", "open", {"duration_s": 300})
        assert c["status"] == "confirmed"   # confirmed = the hub saw open AND flow > 0
        assert await asyncio.to_thread(valve.closed_by_firmware.wait, 5)
        ev = await wait_event(st, "valve.runtime_limit")
        assert ev["data"] == {"max_runtime_s": 1}
    run(stack, scenario)


def test_leak_and_emergency_stop_events(stack):
    async def scenario(st):
        valve = st.sims["garden_valve"]
        await asyncio.to_thread(valve.set_fault, "leaking")
        assert (await wait_event(st, "valve.flow_while_closed"))["severity"] == "critical"
        valve.set_fault(None)
        r = await st.send("garden_valve", "valve", "open", {"duration_s": 60})
        await st.wait(lambda: valve.state.get("valve", {}).get("open") is True, "valve open")
        await asyncio.to_thread(valve.emergency_stop)
        await wait_event(st, "valve.emergency_stop")
        await st.wait(lambda: attr(st, "garden_valve", "valve", "open")["value"] is False,
                      "closed by the button")
        assert r.status_code == 201
    run(stack, scenario)


# ---- security system on the hub --------------------------------------------------------

def test_alarm_arm_entry_delay_trigger_siren_disarm(stack):
    async def scenario(st):
        siren, door = st.sims["siren"], st.sims["front_door"]
        await st.wait(lambda: attr(st, "front_door", "contact", "open")["quality"] == "good",
                      "zones reported")
        # Arming is high risk: PIN required.
        r = await st.send("security", "alarm", "arm_away")
        assert r.status_code == 403 or r.json()["error"]["code"] in ("PIN_REQUIRED", "FORBIDDEN"), r.text
        c = await cmd(st, "security", "alarm", "arm_away", confirm_pin=PIN)
        assert c["status"] == "confirmed"                 # only after the exit delay
        # The ack and the state report are separate uploads: the state follows shortly.
        await st.wait(lambda: attr(st, "security", "alarm", "state")["value"] == "armed_away",
                      "armed_away reported")
        await asyncio.to_thread(door.set_open, True)
        await st.wait(lambda: attr(st, "security", "alarm", "state")["value"] == "pending",
                      "entry delay")
        await st.wait(lambda: siren.on, "siren on after entry delay", timeout=5)
        ev = await wait_event(st, "alarm.triggered")
        assert ev["severity"] == "critical" and ev["data"]["zone"] == "front_door"
        assert attr(st, "security", "alarm", "alert_zone")["value"] == "front_door"
        c = await cmd(st, "security", "alarm", "disarm", confirm_pin=PIN)
        assert c["status"] == "confirmed"
        await st.wait(lambda: not siren.on, "siren off")
        await wait_event(st, "alarm.disarmed")
        types = [e["type"] for e in events(st, capability="alarm")]
        assert {"alarm.armed", "alarm.entry_delay", "alarm.triggered", "alarm.disarmed"} <= set(types)
    run(stack, scenario)


def test_alarm_refuses_to_arm_with_open_window(stack):
    async def scenario(st):
        await asyncio.to_thread(st.sims["back_window"].set_open, True)
        await st.wait(lambda: attr(st, "back_window", "contact", "open")["value"] is True,
                      "window open reported")
        c = await cmd(st, "security", "alarm", "arm_home", confirm_pin=PIN)
        assert (c["status"], c["reason"]) == ("rejected", "safety_rule")
        assert "back_window" in (c.get("detail") or str(c["events"]))
        await st.wait(lambda: attr(st, "security", "alarm", "state")["value"] == "disarmed",
                      "still disarmed")
        await wait_event(st, "alarm.arm_refused")
    run(stack, scenario)


def test_alarm_works_without_internet(stack):
    async def scenario(st):
        siren = st.sims["siren"]
        assert (await cmd(st, "security", "alarm", "arm_away", confirm_pin=PIN))["status"] == "confirmed"
        st.transport.down = True                                  # internet gone
        await asyncio.to_thread(st.sims["hall_motion"].trigger, True)
        await st.wait(lambda: siren.on, "siren on while offline")
        assert st.gateway.alarms["security"].state == "triggered"
        await asyncio.sleep(0.5)
        assert st.gateway.store.outbox_size() > 0                 # event + state buffered
        st.transport.down = False
        ev = await wait_event(st, "alarm.triggered")
        assert ev["data"]["zone"] == "hall_motion"
        await st.wait(lambda: attr(st, "security", "alarm", "state")["value"] == "triggered",
                      "backend sees triggered after reconnect")
    run(stack, scenario)
