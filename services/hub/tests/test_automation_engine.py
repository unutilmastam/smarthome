"""Automation engine on the hub (ADR 0013) - unit tests [SIM]."""

import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest

from gateway.automations import AutomationEngine
from gateway.sun import sun_times

T0 = datetime(2026, 10, 7, 15, 0, tzinfo=timezone.utc)      # 20:00 in Tashkent (UTC+5)
HOME = {"timezone": "Asia/Tashkent", "latitude": 41.3111, "longitude": 69.2797}


def motion_rule(**over):
    d = {"triggers": [{"type": "state", "device": "radar", "capability": "motion",
                       "attribute": "detected", "to": True}],
         "actions": [{"type": "command", "device": "lamp", "capability": "switch",
                      "action": "turn_on"},
                     {"type": "notify", "severity": "warning", "text": "Harakat"}],
         "cooldown_s": 60}
    d.update(over)
    return d


class Rig:
    def __init__(self, rules, home=HOME):
        self.values, self.calls, self.runs, self.offline = {}, [], [], set()
        self.manual, self.alarm = {}, []
        self.outcome = "confirmed"

        async def execute(dev, cap, action, params):
            self.calls.append((dev, cap, action, params))
            return self.outcome
        self.e = AutomationEngine(
            known=lambda k, c, a: self.values.get((k, c, a)), execute=execute,
            record=self.runs.append, security_states=lambda: self.alarm,
            is_offline=lambda k: k in self.offline, last_manual=lambda k: self.manual.get(k))
        self.e.load([{"id": f"r{i}", "name": f"r{i}", "version": 1, "definition": d}
                     for i, d in enumerate(rules)], home)

    def motion(self, v, now):
        self.e.on_state("radar", {"motion": {"detected": v}}, now)


def run(coro):
    return asyncio.run(coro)


async def settle():
    for _ in range(5):
        await asyncio.sleep(0)


def test_state_trigger_fires_on_change_only_and_records_the_run():
    async def main():
        r = Rig([motion_rule()])
        r.motion(True, T0)
        await settle()
        r.motion(True, T0 + timedelta(seconds=90))     # same value republished: no new run
        await settle()
        assert r.calls == [("lamp", "switch", "turn_on", {})]
        assert len(r.runs) == 1
        run_ = r.runs[0]
        assert run_["result"] == "ok" and run_["automation_id"] == "r0" and run_["version"] == 1
        assert run_["actions"][0] == {"type": "command", "device": "lamp", "action": "turn_on",
                                      "outcome": "confirmed"}
        assert run_["actions"][1]["outcome"] == "recorded"      # delivery is Phase 13
    run(main())


def test_cooldown_and_max_runs_per_hour():
    async def main():
        r = Rig([motion_rule(cooldown_s=60, max_runs_per_hour=2)])
        for i, t in enumerate([0, 30, 70, 140, 210]):
            r.motion(True, T0 + timedelta(seconds=t))
            r.motion(False, T0 + timedelta(seconds=t + 1))
            await settle()
        # t=0 runs, t=30 cooldown, t=70 runs, t=140 rate limit (reported once), t=210 silent
        assert len(r.calls) == 2
        assert [x["result"] for x in r.runs] == ["ok", "ok", "skipped"]
        assert r.runs[-1]["reason"] == "max_runs_per_hour"
    run(main())


def test_unknown_values_never_satisfy_a_condition():
    async def main():
        cond = [{"type": "state", "device": "door", "capability": "contact", "attribute": "open",
                 "is": False}]
        r = Rig([motion_rule(conditions=cond)])
        r.motion(True, T0)                    # door state unknown -> no run
        await settle()
        assert r.calls == []
        r.values[("door", "contact", "open")] = False
        r.motion(False, T0 + timedelta(seconds=1))
        r.motion(True, T0 + timedelta(seconds=2))
        await settle()
        assert len(r.calls) == 1
    run(main())


def test_manual_override_and_offline_device_are_skipped():
    async def main():
        r = Rig([motion_rule(manual_override_s=600)])
        r.manual["lamp"] = datetime.now(timezone.utc)     # a person just switched the lamp
        r.motion(True, T0)
        await settle()
        assert r.calls == []
        assert (r.runs[0]["result"], r.runs[0]["reason"]) == ("skipped", "manual_override")
        r2 = Rig([motion_rule()])
        r2.offline.add("lamp")
        r2.motion(True, T0)
        await settle()
        assert (r2.runs[0]["result"], r2.runs[0]["reason"]) == ("skipped", "offline")
    run(main())


def test_failed_command_is_reported_as_failed():
    async def main():
        r = Rig([motion_rule()])
        r.outcome = "failed:no_feedback"
        r.motion(True, T0)
        await settle()
        assert r.runs[0]["result"] == "failed"
    run(main())


def test_time_trigger_once_per_minute_and_days():
    async def main():
        rule = {"triggers": [{"type": "time", "at": "20:00", "days": ["wed"]}],   # 2026-10-07 = Wed
                "actions": [{"type": "command", "device": "lamp", "capability": "switch",
                             "action": "turn_off"}], "cooldown_s": 0}
        r = Rig([rule])
        for s in (0, 20, 59):
            r.e.tick(T0 + timedelta(seconds=s))
        await settle()
        assert len(r.calls) == 1
        r.e.tick(T0 + timedelta(days=1))          # Thursday 20:00: not in days
        await settle()
        assert len(r.calls) == 1
    run(main())


def test_sun_trigger_fires_once_and_not_for_old_sunsets():
    async def main():
        rule = {"triggers": [{"type": "sun", "event": "sunset", "offset_min": 10}],
                "actions": [{"type": "command", "device": "lamp", "capability": "switch",
                             "action": "turn_on"}], "cooldown_s": 0}
        r = Rig([rule])
        _, sset = sun_times(date(2026, 10, 7), HOME["latitude"], HOME["longitude"])
        at = sset + timedelta(minutes=10)
        r.e.tick(at - timedelta(seconds=1))
        r.e.tick(at)
        r.e.tick(at + timedelta(seconds=30))
        await settle()
        assert len(r.calls) == 1
        late = Rig([rule])                        # hub booted 3 hours after sunset
        late.e.tick(at + timedelta(hours=3))
        await settle()
        assert late.calls == []
    run(main())


def test_sun_condition_and_missing_coordinates():
    async def main():
        night = [{"type": "sun", "is": "night"}]
        r = Rig([motion_rule(conditions=night)])
        r.motion(True, T0)                         # 20:00 local in October: night
        await settle()
        assert len(r.calls) == 1
        noon = T0 - timedelta(hours=8)             # 12:00 local
        r2 = Rig([motion_rule(conditions=night)])
        r2.motion(True, noon)
        await settle()
        assert r2.calls == []
        r3 = Rig([motion_rule(conditions=night)], home={"timezone": "Asia/Tashkent"})
        r3.motion(True, T0)                        # no coordinates: never guessed
        await settle()
        assert r3.calls == []
    run(main())


def test_security_condition_and_for_s():
    async def main():
        rule = motion_rule(conditions=[{"type": "security_mode", "is": ["armed_away"]}])
        rule["triggers"][0]["for_s"] = 30
        r = Rig([rule])
        r.alarm = ["armed_away"]
        r.motion(True, T0)
        r.e.tick(T0 + timedelta(seconds=10))
        await settle()
        assert r.calls == []
        r.e.tick(T0 + timedelta(seconds=31))
        await settle()
        assert len(r.calls) == 1
        r.alarm = ["disarmed"]
        r.motion(False, T0 + timedelta(seconds=100))
        r.motion(True, T0 + timedelta(seconds=101))
        r.e.tick(T0 + timedelta(seconds=200))
        await settle()
        assert len(r.calls) == 1
    run(main())


def test_auto_off_and_respects_a_person():
    async def main():
        rule = motion_rule()
        rule["actions"][0]["auto_off_after_s"] = 5
        r = Rig([rule])
        r.e.rules["r0"].d["actions"][0]["auto_off_after_s"] = 0.05   # speed up the test
        r.motion(True, T0)
        await asyncio.sleep(0.2)
        assert r.calls[-1] == ("lamp", "switch", "turn_off", {})
        r2 = Rig([rule])
        r2.e.rules["r0"].d["actions"][0]["auto_off_after_s"] = 0.05
        r2.motion(True, T0)
        await settle()
        r2.manual["lamp"] = datetime.now(timezone.utc)   # someone took over the lamp
        await asyncio.sleep(0.2)
        assert ("lamp", "switch", "turn_off", {}) not in r2.calls
    run(main())


def test_reload_keeps_history_and_bumps_version():
    async def main():
        r = Rig([motion_rule(max_runs_per_hour=1)])
        r.motion(True, T0)
        await settle()
        r.e.load([{"id": "r0", "name": "r0", "version": 2,
                   "definition": motion_rule(max_runs_per_hour=1, cooldown_s=0)}], HOME)
        r.motion(False, T0 + timedelta(seconds=5))
        r.motion(True, T0 + timedelta(seconds=6))
        await settle()
        assert len(r.calls) == 1                       # an edit does not reset the hourly cap
        assert r.runs[-1]["version"] == 2 and r.runs[-1]["result"] == "skipped"
    run(main())


@pytest.mark.parametrize("place,lat,lon,d,rise,sset", [
    ("London", 51.5074, -0.1278, date(2026, 6, 21), "03:43", "20:21"),
    ("London", 51.5074, -0.1278, date(2026, 12, 21), "08:04", "15:53"),
])
def test_sun_times_match_published_tables(place, lat, lon, d, rise, sset):
    r, s = sun_times(d, lat, lon)

    def close(dt, hhmm):
        h, m = map(int, hhmm.split(":"))
        return abs((dt.hour * 60 + dt.minute) - (h * 60 + m)) <= 3
    assert close(r, rise) and close(s, sset), (place, r, s)
