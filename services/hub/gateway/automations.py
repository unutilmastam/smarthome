"""Automation engine ON THE HUB (ARCHITECTURE 11, ADR 0013) - works without internet.

Rules come from GET /hub/config (validated by the backend: devices, contracts, no high-risk
actions, no loops). Runtime guards here: cooldown, max_runs_per_hour, manual override,
unknown values never satisfy a condition, commands wait for ack/confirmation like any
other command. Every started run is recorded (outbox -> POST /hub/automation-runs).
"""

import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Awaitable, Callable, Deque, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from gateway.sun import sun_times

log = logging.getLogger("automations")

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_COOLDOWN_S = 60
DEFAULT_MAX_PER_HOUR = 20
DEFAULT_OVERRIDE_S = 1800


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@dataclass
class Rule:
    id: str
    name: str
    version: int
    d: dict
    last_run: Optional[datetime] = None
    runs: Deque[datetime] = field(default_factory=deque)
    rate_limited_reported: bool = False
    fired_marks: Dict[str, str] = field(default_factory=dict)   # time/sun trigger -> last fired key
    holding: Dict[int, datetime] = field(default_factory=dict)  # state trigger idx -> since (for_s)

    @property
    def cooldown(self) -> int:
        return int(self.d.get("cooldown_s", DEFAULT_COOLDOWN_S))

    @property
    def max_per_hour(self) -> int:
        return int(self.d.get("max_runs_per_hour", DEFAULT_MAX_PER_HOUR))

    @property
    def override_s(self) -> int:
        return int(self.d.get("manual_override_s", DEFAULT_OVERRIDE_S))


class AutomationEngine:
    def __init__(self,
                 known: Callable[[str, str, str], Optional[object]],
                 execute: Callable[[str, str, str, dict], Awaitable[str]],
                 record: Callable[[dict], None],
                 security_states: Callable[[], List[str]],
                 is_offline: Callable[[str], bool],
                 last_manual: Callable[[str], Optional[datetime]]):
        self.known = known                  # latest REPORTED value or None
        self.execute = execute              # (device, cap, action, params) -> outcome
        self.record = record                # run record -> outbox
        self.security_states = security_states
        self.is_offline = is_offline
        self.last_manual = last_manual      # when a PERSON last commanded this device
        self.rules: Dict[str, Rule] = {}
        self.tz = ZoneInfo("Asia/Tashkent")
        self.lat: Optional[float] = None
        self.lon: Optional[float] = None
        self.seen: Dict[Tuple[str, str, str], object] = {}
        self.tasks: set = set()
        self._sun_cache: Dict[date, Tuple[Optional[datetime], Optional[datetime]]] = {}

    # ---- config -------------------------------------------------------------------------
    def load(self, automations: List[dict], home: Optional[dict]) -> None:
        home = home or {}
        try:
            self.tz = ZoneInfo(home.get("timezone") or "Asia/Tashkent")
        except Exception:  # unknown zone name: keep the previous one
            log.warning("unknown timezone %r", home.get("timezone"))
        if (home.get("latitude"), home.get("longitude")) != (self.lat, self.lon):
            self._sun_cache.clear()
        self.lat, self.lon = home.get("latitude"), home.get("longitude")
        new: Dict[str, Rule] = {}
        for a in automations:
            old = self.rules.get(a["id"])
            if old and old.version == a["version"]:
                new[a["id"]] = old          # keep cooldown / rate history
                continue
            r = Rule(a["id"], a.get("name", ""), a["version"], a["definition"])
            if old:                         # edited: keep the history that protects the house
                r.last_run, r.runs = old.last_run, old.runs
            new[a["id"]] = r
        self.rules = new

    # ---- time helpers ---------------------------------------------------------------------
    def _local(self, now: datetime) -> datetime:
        return now.astimezone(self.tz)

    def _sun(self, d: date) -> Tuple[Optional[datetime], Optional[datetime]]:
        if self.lat is None or self.lon is None:
            return None, None
        if d not in self._sun_cache:
            self._sun_cache[d] = sun_times(d, self.lat, self.lon)
            if len(self._sun_cache) > 8:
                self._sun_cache.pop(min(self._sun_cache))
        return self._sun_cache[d]

    @staticmethod
    def _day_ok(spec: dict, local: datetime) -> bool:
        days = spec.get("days")
        return not days or DAYS[local.weekday()] in days

    # ---- conditions (unknown -> False, never guessed) --------------------------------------
    def _condition(self, c: dict, now: datetime) -> bool:
        local = self._local(now)
        t = c["type"]
        if t == "state":
            v = self.known(c["device"], c["capability"], c["attribute"])
            return v is not None and v == c["is"]
        if t == "time":
            if not self._day_ok(c, local):
                return False
            hm = local.strftime("%H:%M")
            a, b = c["after"], c["before"]
            return a <= hm < b if a <= b else (hm >= a or hm < b)   # may wrap midnight
        if t == "sun":
            rise, sset = self._sun(local.date())
            if rise is None or sset is None:
                return False
            off = timedelta(minutes=c.get("offset_min", 0))
            is_day = rise + off <= now < sset + off
            return is_day if c["is"] == "day" else not is_day
        if t == "security_mode":
            states = self.security_states()
            return bool(states) and any(s in c["is"] for s in states)
        return False

    # ---- triggers ----------------------------------------------------------------------------
    def on_state(self, key: str, accepted: Dict[str, Dict[str, object]], now: datetime) -> None:
        """Called with REPORTED values only. Fires on a CHANGE to the trigger value."""
        changed = set()
        for cap, attrs in accepted.items():
            for attr, value in attrs.items():
                k = (key, cap, attr)
                if k in self.seen and self.seen[k] == value:
                    continue
                self.seen[k] = value
                changed.add(k)
        if not changed:
            return
        for r in list(self.rules.values()):
            for i, t in enumerate(r.d["triggers"]):
                if t["type"] != "state" or (t["device"], t["capability"], t["attribute"]) not in changed:
                    continue
                if self.seen[(t["device"], t["capability"], t["attribute"])] == t["to"]:
                    if t.get("for_s"):
                        r.holding[i] = now
                    else:
                        self._fire(r, self._describe(t), now)
                else:
                    r.holding.pop(i, None)

    @staticmethod
    def _describe(t: dict) -> str:
        if t["type"] == "state":
            return f"{t['device']} {t['capability']}.{t['attribute']} = {t['to']}"[:160]
        if t["type"] == "time":
            return f"time {t['at']}"
        return f"{t['event']} {t.get('offset_min', 0):+d} min"

    def tick(self, now: datetime) -> None:
        local = self._local(now)
        hm = local.strftime("%H:%M")
        today = local.date().isoformat()
        for r in list(self.rules.values()):
            for i, t in enumerate(r.d["triggers"]):
                mark = f"{i}"
                if t["type"] == "time":
                    if t["at"] == hm and self._day_ok(t, local) and r.fired_marks.get(mark) != f"{today} {hm}":
                        r.fired_marks[mark] = f"{today} {hm}"
                        self._fire(r, self._describe(t), now)
                elif t["type"] == "sun":
                    rise, sset = self._sun(local.date())
                    at = rise if t["event"] == "sunrise" else sset
                    if at is None or not self._day_ok(t, local):
                        continue
                    at += timedelta(minutes=t.get("offset_min", 0))
                    # Fire once per day, within 2 minutes after the moment (a hub that was
                    # off for hours does not replay old sunsets).
                    if at <= now < at + timedelta(minutes=2) and r.fired_marks.get(mark) != today:
                        r.fired_marks[mark] = today
                        self._fire(r, self._describe(t), now)
                elif t["type"] == "state" and i in r.holding:
                    if now - r.holding[i] >= timedelta(seconds=t["for_s"]):
                        r.holding.pop(i)
                        self._fire(r, self._describe(t) + f" for {t['for_s']}s", now)

    # ---- running ------------------------------------------------------------------------------
    def _fire(self, r: Rule, trigger: str, now: datetime) -> None:
        if r.last_run and (now - r.last_run).total_seconds() < r.cooldown:
            return
        if not all(self._condition(c, now) for c in r.d.get("conditions", [])):
            return
        while r.runs and now - r.runs[0] >= timedelta(hours=1):
            r.runs.popleft()
        if len(r.runs) >= r.max_per_hour:
            if not r.rate_limited_reported:   # report once per saturated window, not every time
                r.rate_limited_reported = True
                self._record(r, trigger, now, "skipped", [], "max_runs_per_hour")
            return
        r.rate_limited_reported = False
        r.last_run = now
        r.runs.append(now)
        task = asyncio.get_running_loop().create_task(self._run(r, trigger, now))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def _overridden(self, r: Rule, device: str, now: datetime) -> bool:
        t = self.last_manual(device)
        return t is not None and (now - t).total_seconds() < r.override_s

    async def _run(self, r: Rule, trigger: str, started: datetime) -> None:
        out: List[dict] = []
        for a in r.d["actions"]:
            if a["type"] == "delay":
                await asyncio.sleep(a["seconds"])
                out.append({"type": "delay", "outcome": f"{a['seconds']}s"})
            elif a["type"] == "notify":
                # Delivery (Telegram/Push) is Phase 13: recorded in the run history for now.
                out.append({"type": "notify", "outcome": "recorded",
                            "severity": a.get("severity", "info"), "text": a["text"]})
            elif a["type"] == "command":
                out.append(await self._command(r, a, started))
        commands = [x for x in out if x["type"] == "command"]
        good = [x for x in commands if x["outcome"] in ("confirmed", "acked")]
        skipped = [x for x in commands if x["outcome"].startswith("skipped")]
        if commands and len(skipped) == len(commands):
            result, reason = "skipped", skipped[0]["outcome"].split(":", 1)[1]
        elif len(good) == len(commands) - len(skipped):
            result, reason = "ok", None
        elif good:
            result, reason = "partial", None
        else:
            result, reason = "failed", None
        self._record(r, trigger, started, result, out, reason)

    async def _command(self, r: Rule, a: dict, started: datetime) -> dict:
        item = {"type": "command", "device": a["device"], "action": a["action"]}
        now = datetime.now(timezone.utc)
        if self._overridden(r, a["device"], now):
            return {**item, "outcome": "skipped:manual_override"}
        if self.is_offline(a["device"]):
            return {**item, "outcome": "skipped:offline"}
        try:
            outcome = await self.execute(a["device"], a["capability"], a["action"], a.get("params") or {})
        except Exception as exc:  # never let one action kill the engine
            log.exception("automation %s action failed", r.id)
            outcome = f"failed:{type(exc).__name__}"[:48]
        if a.get("auto_off_after_s") and outcome in ("confirmed", "acked"):
            task = asyncio.get_running_loop().create_task(
                self._auto_off(r, a, a["auto_off_after_s"]))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)
        return {**item, "outcome": outcome[:48]}

    async def _auto_off(self, r: Rule, a: dict, seconds: float) -> None:
        scheduled = datetime.now(timezone.utc)
        await asyncio.sleep(seconds)
        # A person touched the device after the automation switched it on: leave it as
        # they set it (manual override wins).
        t = self.last_manual(a["device"])
        if t is not None and t >= scheduled:
            return
        if not self.is_offline(a["device"]):
            await self.execute(a["device"], "switch", "turn_off", {})

    def _record(self, r: Rule, trigger: str, ts: datetime, result: str, actions: List[dict],
                reason: Optional[str]) -> None:
        run = {"id": str(uuid.uuid4()), "automation_id": r.id, "version": r.version,
               "ts": _iso(ts), "trigger": trigger[:160], "result": result, "actions": actions[:12]}
        if reason:
            run["reason"] = reason[:64]
        log.info("automation %s (%s): %s %s", r.name or r.id, trigger, result, reason or "")
        self.record(run)
