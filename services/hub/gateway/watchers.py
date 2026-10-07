"""Hub-side watchers that turn state history into events (ADR 0012).

They never change a device state and never confirm a command: they only warn.
Unknown values are ignored (nothing is invented).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

DEFAULT_LEFT_OPEN_S = 600
DEFAULT_NO_EFFECT_S = 900
MIN_EFFECT_C = 0.5


@dataclass
class GateWatcher:
    """cover.left_open: the gate has not been closed for longer than left_open_after_s.
    Fires once per open period; the reed-confirmed 'closed' state resets it."""
    emit: Callable[[str, str, dict], None]          # (device_key, type, data)
    since: Dict[str, datetime] = field(default_factory=dict)
    fired: Dict[str, bool] = field(default_factory=dict)

    def update(self, key: str, state: Optional[str], now: datetime) -> None:
        if state == "closed":
            self.since.pop(key, None)
            self.fired.pop(key, None)
        elif state in ("open", "opening", "closing", "stopped"):
            self.since.setdefault(key, now)
        # "unknown" (e.g. both reeds active): neither open nor closed - do not guess

    def check(self, now: datetime, threshold_for: Callable[[str], int]) -> None:
        for key, t0 in list(self.since.items()):
            limit = threshold_for(key)
            if not self.fired.get(key) and now - t0 >= timedelta(seconds=limit):
                self.fired[key] = True
                self.emit(key, "cover.left_open", {"open_s": int((now - t0).total_seconds())})


@dataclass
class _Run:
    started: datetime
    start_temp: Optional[float]      # None until the first room temperature arrives
    mode: str
    target: Optional[float]
    done: bool = False


@dataclass
class ClimateWatcher:
    """climate.no_effect: after power on (cool/heat) the room temperature has not moved
    toward the target by MIN_EFFECT_C within no_effect_after_s. A hint only: an IR unit
    gives no feedback, so this is never used to confirm a command."""
    emit: Callable[[str, str, dict], None]
    runs: Dict[str, _Run] = field(default_factory=dict)

    def update(self, key: str, attrs: Dict[str, object], current: Dict[str, object],
               now: datetime) -> None:
        """attrs: the attributes that just changed; current: latest known values."""
        temp = current.get("current_temp")
        temp = float(temp) if isinstance(temp, (int, float)) else None
        if "power" in attrs:
            if attrs["power"] is True and key not in self.runs \
                    and current.get("mode") in ("cool", "heat"):
                self.runs[key] = _Run(now, temp, current["mode"], current.get("target_temp"))
            elif attrs["power"] is False:
                self.runs.pop(key, None)
        elif "mode" in attrs and key in self.runs and attrs["mode"] not in ("cool", "heat"):
            self.runs.pop(key, None)
        run = self.runs.get(key)
        if run is not None and run.start_temp is None and temp is not None:
            # Measure from the first known temperature, never from a guess.
            run.started, run.start_temp = now, temp

    def check(self, now: datetime, current_temp: Callable[[str], Optional[float]],
              threshold_for: Callable[[str], int]) -> None:
        for key, run in list(self.runs.items()):
            if run.done or run.start_temp is None \
                    or now - run.started < timedelta(seconds=threshold_for(key)):
                continue
            t = current_temp(key)
            if t is None:
                continue  # sensor silent: no conclusion
            moved = (run.start_temp - t) if run.mode == "cool" else (t - run.start_temp)
            reached = run.target is not None and (
                t <= run.target if run.mode == "cool" else t >= run.target)
            run.done = True
            if moved < MIN_EFFECT_C and not reached:
                self.emit(key, "climate.no_effect", {
                    "minutes": int((now - run.started).total_seconds() // 60),
                    "start_temp": run.start_temp, "current_temp": t, "mode": run.mode})
