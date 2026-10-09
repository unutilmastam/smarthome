"""Alarm engine on the hub (ADR 0012) - pure state machine tests [SIM]."""

from datetime import datetime, timedelta, timezone

import pytest

from gateway.alarm import AlarmEngine
from gateway.watchers import ClimateWatcher, GateWatcher

T0 = datetime(2026, 10, 7, 20, 0, tzinfo=timezone.utc)
CFG = {"zones": [
    {"device_key": "front_door", "capability": "contact", "mode": "entry"},
    {"device_key": "back_window", "capability": "contact", "mode": "instant"},
    {"device_key": "hall_motion", "capability": "motion", "mode": "instant"},
], "sirens": ["siren"], "exit_delay_s": 30, "entry_delay_s": 20, "siren_max_s": 60}


class Rig:
    def __init__(self, cfg=CFG):
        self.states, self.events, self.sirens, self.saved = [], [], [], []
        self.values = {("front_door", "contact", "open"): False,
                       ("back_window", "contact", "open"): False}
        self.e = self.make(cfg)

    def make(self, cfg):
        return AlarmEngine(
            key="security", config=cfg, publish=self.states.append,
            event=lambda t, d: self.events.append((t, d)),
            siren=lambda k, on: self.sirens.append((k, on)),
            zone_value=lambda k, c, a: self.values.get((k, c, a)),
            save=self.saved.append)

    @property
    def state(self):
        return self.e.state

    def types(self):
        return [t for t, _ in self.events]


def test_arm_with_exit_delay_then_armed():
    r = Rig()
    assert r.e.command("arm_away", T0).status == "acked"
    assert r.state == "arming"
    r.e.tick(T0 + timedelta(seconds=29))
    assert r.state == "arming"
    r.e.tick(T0 + timedelta(seconds=30))
    assert r.state == "armed_away"
    assert r.types() == ["alarm.armed"]
    assert r.states[-1] == {"state": "armed_away", "alert_zone": ""}


def test_arming_refused_when_a_zone_is_open():
    r = Rig()
    r.values[("back_window", "contact", "open")] = True
    res = r.e.command("arm_away", T0)
    assert res.status == "rejected" and res.reason == "safety_rule"
    assert "back_window" in res.detail
    assert r.state == "disarmed"
    assert r.types() == ["alarm.arm_refused"]


def test_unknown_zone_does_not_block_but_is_reported():
    r = Rig()
    del r.values[("front_door", "contact", "open")]   # sensor never reported / offline
    assert r.e.command("arm_away", T0).status == "acked"
    assert ("alarm.sensor_offline", {"zone": "front_door", "when": "arming"}) in r.events


def test_entry_delay_then_disarm_in_time_no_siren():
    r = Rig()
    r.e.command("arm_away", T0)
    r.e.tick(T0 + timedelta(seconds=30))
    r.e.on_sensor("front_door", "contact", {"open": True}, T0 + timedelta(seconds=60))
    assert r.state == "pending" and r.e.alert_zone == "front_door"
    r.e.command("disarm", T0 + timedelta(seconds=70))
    r.e.tick(T0 + timedelta(seconds=200))
    assert r.state == "disarmed"
    assert ("siren", True) not in r.sirens
    assert "alarm.triggered" not in r.types()


def test_entry_delay_expires_triggers_sirens_then_siren_timeout():
    r = Rig()
    r.e.command("arm_away", T0)
    r.e.tick(T0 + timedelta(seconds=30))
    r.e.on_sensor("front_door", "contact", {"open": True}, T0 + timedelta(seconds=40))
    r.e.tick(T0 + timedelta(seconds=60))
    assert r.state == "triggered"
    assert r.sirens == [("siren", True)]
    assert ("alarm.triggered", {"zone": "front_door", "mode": "entry"}) in r.events
    r.e.tick(T0 + timedelta(seconds=121))
    assert r.sirens[-1] == ("siren", False)
    assert r.state == "triggered"          # stays triggered until someone disarms
    assert r.types()[-1] == "alarm.siren_timeout"
    r.e.command("disarm", T0 + timedelta(seconds=130))
    assert r.state == "disarmed"


def test_instant_zone_triggers_immediately():
    r = Rig()
    r.e.command("arm_away", T0)
    r.e.tick(T0 + timedelta(seconds=30))
    r.e.on_sensor("hall_motion", "motion", {"detected": True}, T0 + timedelta(seconds=31))
    assert r.state == "triggered" and r.e.alert_zone == "hall_motion"


def test_exit_delay_ignores_entry_route_but_not_instant():
    r = Rig()
    r.e.command("arm_away", T0)
    r.e.on_sensor("front_door", "contact", {"open": True}, T0 + timedelta(seconds=5))
    assert r.state == "arming"
    r.e.on_sensor("back_window", "contact", {"open": True}, T0 + timedelta(seconds=6))
    assert r.state == "triggered"


def test_armed_home_ignores_motion_inside():
    r = Rig()
    r.e.command("arm_home", T0)
    r.e.tick(T0 + timedelta(seconds=30))
    assert r.state == "armed_home"
    r.e.on_sensor("hall_motion", "motion", {"detected": True}, T0 + timedelta(seconds=40))
    assert r.state == "armed_home"
    r.e.on_sensor("back_window", "contact", {"open": True}, T0 + timedelta(seconds=41))
    assert r.state == "triggered"


def test_closing_or_unrelated_sensors_do_nothing():
    r = Rig()
    r.e.command("arm_away", T0)
    r.e.tick(T0 + timedelta(seconds=30))
    r.e.on_sensor("front_door", "contact", {"open": False}, T0 + timedelta(seconds=40))
    r.e.on_sensor("garden_lights", "switch", {"on": True}, T0 + timedelta(seconds=40))
    assert r.state == "armed_away"


def test_cannot_arm_while_triggered():
    r = Rig()
    r.e.command("arm_away", T0)
    r.e.tick(T0 + timedelta(seconds=30))
    r.e.on_sensor("back_window", "contact", {"open": True}, T0 + timedelta(seconds=31))
    res = r.e.command("arm_home", T0 + timedelta(seconds=32))
    assert res.status == "rejected" and res.detail == "disarm first"


def test_state_survives_hub_restart():
    r = Rig()
    r.e.command("arm_away", T0)
    r.e.tick(T0 + timedelta(seconds=30))
    r.e.on_sensor("front_door", "contact", {"open": True}, T0 + timedelta(seconds=40))
    snap = r.saved[-1]
    again = r.make(CFG)
    again.restore(snap)
    assert again.state == "pending"
    again.tick(T0 + timedelta(seconds=60))   # entry delay still runs out after a restart
    assert again.state == "triggered"


def test_sensor_offline_while_armed_is_reported():
    r = Rig()
    r.e.command("arm_away", T0)
    r.e.on_offline("front_door")
    r.e.on_offline("not_a_zone")
    assert r.types() == ["alarm.sensor_offline"]


def test_zero_delays():
    cfg = {**CFG, "exit_delay_s": 0, "entry_delay_s": 0}
    r = Rig(cfg)
    r.e.command("arm_away", T0)
    assert r.state == "armed_away"
    r.e.on_sensor("front_door", "contact", {"open": True}, T0)
    assert r.state == "triggered"


# ---- watchers ---------------------------------------------------------------------------

def test_gate_left_open_once_per_open_period():
    out = []
    w = GateWatcher(lambda k, t, d: out.append((k, t, d)))
    w.update("gate", "opening", T0)
    w.update("gate", "open", T0 + timedelta(seconds=15))
    w.check(T0 + timedelta(seconds=599), lambda k: 600)
    assert out == []
    w.check(T0 + timedelta(seconds=600), lambda k: 600)
    w.check(T0 + timedelta(seconds=900), lambda k: 600)
    assert out == [("gate", "cover.left_open", {"open_s": 600})]
    w.update("gate", "closed", T0 + timedelta(seconds=950))
    w.update("gate", "open", T0 + timedelta(seconds=1000))
    w.check(T0 + timedelta(seconds=1700), lambda k: 600)
    assert len(out) == 2


def test_gate_unknown_state_is_not_counted_as_open():
    out = []
    w = GateWatcher(lambda k, t, d: out.append(t))
    w.update("gate", "unknown", T0)
    w.check(T0 + timedelta(hours=2), lambda k: 600)
    assert out == []


@pytest.mark.parametrize("end_temp,expected", [(27.9, ["climate.no_effect"]), (26.0, [])])
def test_climate_no_effect(end_temp, expected):
    out = []
    w = ClimateWatcher(lambda k, t, d: out.append(t))
    cur = {"current_temp": 28.0, "mode": "cool", "target_temp": 22}
    w.update("ac", {"power": True}, cur, T0)
    w.update("ac", {"target_temp": 21, "power": True}, cur, T0 + timedelta(minutes=5))  # no restart
    w.check(T0 + timedelta(minutes=14), lambda k: end_temp, lambda k: 900)
    assert out == []
    w.check(T0 + timedelta(minutes=15), lambda k: end_temp, lambda k: 900)
    w.check(T0 + timedelta(minutes=30), lambda k: end_temp, lambda k: 900)
    assert out == expected


def test_climate_measures_from_first_known_temperature():
    out = []
    w = ClimateWatcher(lambda k, t, d: out.append(t))
    w.update("ac", {"power": True}, {"current_temp": None, "mode": "cool"}, T0)
    w.update("ac", {"current_temp": 28.0}, {"current_temp": 28.0, "mode": "cool"},
             T0 + timedelta(minutes=2))
    w.check(T0 + timedelta(minutes=16), lambda k: 28.0, lambda k: 900)
    assert out == []                     # only 14 min since the first reading
    w.check(T0 + timedelta(minutes=17), lambda k: 28.0, lambda k: 900)
    assert out == ["climate.no_effect"]


def test_climate_without_room_temperature_says_nothing():
    out = []
    w = ClimateWatcher(lambda k, t, d: out.append(t))
    w.update("ac", {"power": True}, {"current_temp": None, "mode": "cool"}, T0)
    w.update("ac2", {"power": True}, {"current_temp": 28.0, "mode": "cool"}, T0)
    w.check(T0 + timedelta(hours=1), lambda k: None, lambda k: 900)
    assert out == []
