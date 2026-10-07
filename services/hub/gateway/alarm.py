"""Security system that runs ON THE HUB (ADR 0012) - works without internet.

A virtual device (adapter "hub") with the `alarm` capability. The gateway hands its
verified commands (signature, expiry, role and PIN already checked) to this engine
instead of MQTT. Zones are contact/motion sensors the gateway already listens to.

States: disarmed -> arming (exit delay) -> armed_away | armed_home
        armed_* --entry zone--> pending (entry delay) --> triggered (sirens on)
        armed_* --instant zone--> triggered
        any --disarm--> disarmed (sirens off)

Pure logic: time is passed in, side effects go through callbacks. State is persisted
so a hub restart does not silently disarm the house.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Tuple

DEFAULT_EXIT_DELAY_S = 30
DEFAULT_ENTRY_DELAY_S = 30
DEFAULT_SIREN_MAX_S = 180


@dataclass
class Zone:
    device_key: str
    capability: str          # contact | motion
    mode: str                # entry | instant
    home: bool               # also active in armed_home

    @property
    def attribute(self) -> str:
        return "open" if self.capability == "contact" else "detected"


def zones_from_config(cfg: dict) -> List[Zone]:
    out = []
    for z in cfg.get("zones") or []:
        cap = z["capability"]
        out.append(Zone(z["device_key"], cap, z["mode"],
                        z.get("home", cap == "contact")))
    return out


@dataclass
class Result:
    status: str                      # acked | rejected
    reason: Optional[str] = None
    detail: Optional[str] = None


@dataclass
class AlarmEngine:
    key: str
    config: dict
    # callbacks
    publish: Callable[[dict], None]                       # {"state":..., "alert_zone":...}
    event: Callable[[str, dict], None]                    # ("alarm.triggered", data)
    siren: Callable[[str, bool], None]                    # (siren_key, on)
    zone_value: Callable[[str, str, str], Optional[object]]  # (key, cap, attr) -> value | None
    save: Callable[[dict], None] = lambda s: None
    state: str = "disarmed"
    target: Optional[str] = None             # armed_away | armed_home while arming
    deadline: Optional[datetime] = None      # end of exit or entry delay
    siren_until: Optional[datetime] = None
    alert_zone: str = ""
    zones: List[Zone] = field(default_factory=list)

    def __post_init__(self):
        self.zones = zones_from_config(self.config)

    # ---- config / persistence ----------------------------------------------------------
    @property
    def exit_delay(self) -> int:
        return int(self.config.get("exit_delay_s", DEFAULT_EXIT_DELAY_S))

    @property
    def entry_delay(self) -> int:
        return int(self.config.get("entry_delay_s", DEFAULT_ENTRY_DELAY_S))

    @property
    def siren_max(self) -> int:
        return int(self.config.get("siren_max_s", DEFAULT_SIREN_MAX_S))

    def reconfigure(self, config: dict) -> None:
        self.config = config
        self.zones = zones_from_config(config)

    def snapshot(self) -> dict:
        iso = lambda d: d.isoformat() if d else None  # noqa: E731
        return {"state": self.state, "target": self.target, "deadline": iso(self.deadline),
                "siren_until": iso(self.siren_until), "alert_zone": self.alert_zone}

    def restore(self, snap: Optional[dict]) -> None:
        if not snap:
            return
        parse = lambda s: datetime.fromisoformat(s) if s else None  # noqa: E731
        self.state = snap.get("state", "disarmed")
        self.target = snap.get("target")
        self.deadline = parse(snap.get("deadline"))
        self.siren_until = parse(snap.get("siren_until"))
        self.alert_zone = snap.get("alert_zone", "")

    def _set(self, state: str, alert_zone: Optional[str] = None) -> None:
        self.state = state
        if alert_zone is not None:
            self.alert_zone = alert_zone
        self.save(self.snapshot())
        self.publish({"state": self.state, "alert_zone": self.alert_zone})

    def announce(self) -> None:
        self.publish({"state": self.state, "alert_zone": self.alert_zone})

    # ---- zones ------------------------------------------------------------------------------
    def _active(self, mode: str) -> List[Zone]:
        return [z for z in self.zones if mode == "armed_away" or z.home]

    def _zone(self, key: str) -> Optional[Zone]:
        return next((z for z in self.zones if z.device_key == key), None)

    def _open_zones(self, mode: str) -> Tuple[List[str], List[str]]:
        """(open contact zones, zones with unknown state). Motion is momentary: not checked."""
        open_, unknown = [], []
        for z in self._active(mode):
            if z.capability != "contact":
                continue
            v = self.zone_value(z.device_key, z.capability, z.attribute)
            if v is None:
                unknown.append(z.device_key)
            elif v is True:
                open_.append(z.device_key)
        return open_, unknown

    # ---- commands -----------------------------------------------------------------------------
    def command(self, action: str, now: datetime) -> Result:
        if action == "disarm":
            was = self.state
            self._sirens(False)
            self.deadline = self.target = self.siren_until = None
            self._set("disarmed", "")
            if was != "disarmed":
                self.event("alarm.disarmed", {"from": was})
            return Result("acked")
        if action in ("arm_away", "arm_home"):
            mode = "armed_away" if action == "arm_away" else "armed_home"
            if self.state in ("pending", "triggered"):
                return Result("rejected", "safety_rule", "disarm first")
            open_, unknown = self._open_zones(mode)
            if open_:
                self.event("alarm.arm_refused", {"open_zones": open_})
                return Result("rejected", "safety_rule", "open zones: " + ", ".join(open_))
            for k in unknown:
                self.event("alarm.sensor_offline", {"zone": k, "when": "arming"})
            if self.exit_delay > 0:
                self.target = mode
                self.deadline = now + timedelta(seconds=self.exit_delay)
                self._set("arming", "")
            else:
                self._armed(mode)
            return Result("acked")
        return Result("rejected", "invalid_params", f"unknown action {action}")

    def _armed(self, mode: str) -> None:
        self.target = self.deadline = None
        self._set(mode, "")
        self.event("alarm.armed", {"mode": mode})

    # ---- sensor input ----------------------------------------------------------------------
    def on_sensor(self, key: str, capability: str, attrs: Dict[str, object],
                  now: datetime) -> None:
        z = self._zone(key)
        if z is None or z.capability != capability or attrs.get(z.attribute) is not True:
            return
        if self.state == "arming":
            if z.mode == "instant" and (self.target == "armed_away" or z.home):
                self._trigger(z, now)
            return  # entry/exit route zones are expected to open while leaving
        if self.state in ("armed_away", "armed_home"):
            if z not in self._active(self.state):
                return
            if z.mode == "entry" and self.entry_delay > 0:
                self.deadline = now + timedelta(seconds=self.entry_delay)
                self._set("pending", z.device_key)
                self.event("alarm.entry_delay", {"zone": z.device_key,
                                                 "seconds": self.entry_delay})
            else:
                self._trigger(z, now)
            return
        if self.state == "pending" and z.mode == "instant":
            self._trigger(z, now)

    def on_offline(self, key: str) -> None:
        z = self._zone(key)
        if z and self.state in ("armed_away", "armed_home", "arming", "pending"):
            self.event("alarm.sensor_offline", {"zone": key})

    def _trigger(self, z: Zone, now: datetime) -> None:
        self.deadline = None
        self.siren_until = now + timedelta(seconds=self.siren_max)
        self._set("triggered", z.device_key)
        self._sirens(True)
        self.event("alarm.triggered", {"zone": z.device_key, "mode": z.mode})

    def _sirens(self, on: bool) -> None:
        if not on and self.siren_until is None and self.state != "triggered":
            return
        for s in self.config.get("sirens") or []:
            self.siren(s, on)

    # ---- timers ----------------------------------------------------------------------------
    def tick(self, now: datetime) -> None:
        if self.state == "arming" and self.deadline and now >= self.deadline:
            self._armed(self.target or "armed_away")
        elif self.state == "pending" and self.deadline and now >= self.deadline:
            z = self._zone(self.alert_zone) or Zone(self.alert_zone, "contact", "entry", True)
            self._trigger(z, now)
        if self.state == "triggered" and self.siren_until and now >= self.siren_until:
            for s in self.config.get("sirens") or []:
                self.siren(s, False)
            self.siren_until = None
            self.save(self.snapshot())
            self.event("alarm.siren_timeout", {"seconds": self.siren_max})
