"""Tuya devices on the home LAN (ADR 0016): relays, sockets, breakers, lights, IR remotes.

The hub talks to each device with Tuya's local protocol (tinytuya); no Tuya cloud. Inside
the gateway a Tuya device is a "virtual device" like the alarm (ADR 0012): commands come
from Gateway._run, the bridge answers with an ack, and what the device REPORTS (its data
points, "DPS") becomes an ordinary state message. So confirmation, PIN, automations and
notifications work unchanged.

Nothing is invented: a DPS the device did not send is simply not reported (unknown), an
attribute the profile has no DPS for is listed as unsupported by the backend, and a device
that does not answer is "offline".
"""
from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

log = logging.getLogger("gateway.tuya")

# ---- profiles: which data point means what (defaults; every number can be overridden in
# the device's connection.dps). Scales turn raw integers into the contract's units.
PROFILES: Dict[str, Dict[str, Any]] = {
    "switch": {"switch": 1},
    "plug_meter": {"switch": 1, "current_ma": 18, "power_w10": 19, "voltage_v10": 20, "energy_wh": 17},
    "breaker": {"breaker": 16, "phase_a": 6, "energy_kwh100": 1, "fault": 9},
    "light": {"switch": 20, "brightness_1000": 22},
    "ir": {},
}

# Which contract capabilities a profile provides (the backend builds the device from this).
PROFILE_CAPS: Dict[str, List[str]] = {
    "switch": ["switch"],
    "plug_meter": ["switch", "power_meter"],
    "breaker": ["breaker", "power_meter"],
    "light": ["switch", "dimmer"],
    "ir": ["remote"],
}


def decode_phase(raw: str) -> Optional[Dict[str, float]]:
    """dlq breakers report phase A as base64: voltage 2 B (0.1 V), current 3 B (mA),
    power 3 B (W). [SIM] — the layout is checked on the real breaker (docs/hardware/tests)."""
    try:
        b = base64.b64decode(raw)
    except (ValueError, TypeError):
        return None
    if len(b) < 8:
        return None
    return {"voltage": int.from_bytes(b[0:2], "big") / 10,
            "current": int.from_bytes(b[2:5], "big") / 1000,
            "power": float(int.from_bytes(b[5:8], "big"))}


def dps_to_states(profile: str, dps_map: Dict[str, int], dps: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Raw DPS -> {capability: {attribute: value}} with ONLY what the device actually sent."""
    g = lambda name: dps.get(str(dps_map[name])) if name in dps_map else None  # noqa: E731
    out: Dict[str, Dict[str, Any]] = {}

    def put(cap: str, attr: str, value: Any) -> None:
        if value is not None:
            out.setdefault(cap, {})[attr] = value

    if profile in ("switch", "plug_meter", "light"):
        v = g("switch")
        put("switch", "on", v if isinstance(v, bool) else None)
    if profile == "plug_meter":
        for name, attr, scale in (("current_ma", "current", 1000), ("power_w10", "power", 10),
                                  ("voltage_v10", "voltage", 10), ("energy_wh", "energy", 1000)):
            v = g(name)
            put("power_meter", attr, round(v / scale, 3) if isinstance(v, (int, float)) and not isinstance(v, bool) else None)
    if profile == "light":
        v = g("brightness_1000")
        if isinstance(v, int) and not isinstance(v, bool):
            put("dimmer", "brightness", max(0, min(100, round(v / 10))))
    if profile == "breaker":
        closed = g("breaker")
        put("breaker", "closed", closed if isinstance(closed, bool) else None)
        if "fault" in dps_map:
            fault = g("fault")
            if isinstance(fault, int) and not isinstance(fault, bool) and isinstance(closed, bool):
                # A protection fault with the contacts open = tripped (needs a reset on site).
                put("breaker", "tripped", fault != 0 and not closed)
        ph = g("phase_a")
        if isinstance(ph, str):
            for attr, value in (decode_phase(ph) or {}).items():
                put("power_meter", attr, value)
        e = g("energy_kwh100")
        put("power_meter", "energy", round(e / 100, 2) if isinstance(e, int) and not isinstance(e, bool) else None)
    return out


@dataclass
class TuyaConfig:
    key: str
    profile: str
    device_id: str
    ip: str
    local_key: str
    version: float = 3.3
    dps: Dict[str, int] = field(default_factory=dict)
    poll_s: float = 5.0

    @staticmethod
    def from_device(d: dict) -> Optional["TuyaConfig"]:
        conn = d.get("connection") or {}
        profile = conn.get("profile")
        if d.get("adapter") != "tuya" or profile not in PROFILES:
            return None
        if not (conn.get("device_id") and conn.get("ip") and d.get("secret")):
            log.warning("tuya %s: device_id, ip or local key missing", d.get("key"))
            return None
        dps = dict(PROFILES[profile])
        dps.update({k: int(v) for k, v in (conn.get("dps") or {}).items() if k in dps or k in PROFILES[profile]})
        return TuyaConfig(key=d["key"], profile=profile, device_id=str(conn["device_id"]), ip=str(conn["ip"]),
                          local_key=str(d["secret"]), version=float(conn.get("version") or 3.3), dps=dps,
                          poll_s=float(conn.get("poll_s") or 5.0))


def default_client(cfg: TuyaConfig):  # pragma: no cover - real network, see docs/hardware/tests/tuya.md
    import tinytuya
    if cfg.profile == "ir":
        from tinytuya.Contrib import IRRemoteControlDevice
        dev = IRRemoteControlDevice(cfg.device_id, cfg.ip, cfg.local_key, version=cfg.version)
    else:
        dev = tinytuya.Device(cfg.device_id, cfg.ip, cfg.local_key, version=cfg.version)
    dev.set_socketTimeout(4)
    dev.set_socketRetryLimit(1)
    return dev


class TuyaDevice:
    """One device: polls its DPS, turns commands into DPS writes / IR sends."""

    def __init__(self, cfg: TuyaConfig, client, publish: Callable[[str, dict], None],
                 availability: Callable[[str, str], None], codes: Dict[str, str],
                 save_codes: Callable[[Dict[str, str]], None]):
        self.cfg = cfg
        self.client = client
        self.publish = publish            # (key, state message)
        self.availability = availability  # (key, "online"/"offline")
        self.codes = codes                # IR: button -> base64 code (kept on the hub only)
        self.save_codes = save_codes
        self.online: Optional[bool] = None
        self.last: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()        # one conversation with the device at a time
        self.wake = asyncio.Event()
        self.task: Optional[asyncio.Task] = None
        self.learning = False

    # ---- reading ----
    async def refresh(self) -> None:
        if self.learning:
            return  # the blaster is busy listening for the original remote
        async with self.lock:
            res = await asyncio.to_thread(self.client.status)
        if not isinstance(res, dict) or "dps" not in res:
            log.info("tuya %s: no answer (%s)", self.cfg.key, (res or {}).get("Error") if isinstance(res, dict) else res)
            self._mark(False)
            return
        self._mark(True)
        if self.cfg.profile == "ir":
            # An IR blaster has no state of its own; what it "has" is the learned buttons.
            self._publish({"remote": {"buttons": sorted(self.codes)}})
            return
        dps = {str(k): v for k, v in res["dps"].items()}
        log.debug("tuya %s dps %s", self.cfg.key, dps)
        states = dps_to_states(self.cfg.profile, self.cfg.dps, dps)
        if states:
            self.last = {c: {**self.last.get(c, {}), **a} for c, a in states.items()}
            # The retained-state rule (local-mqtt schema): always the FULL known state.
            self._publish(self.last)

    def _publish(self, states: Dict[str, Dict[str, Any]]) -> None:
        self.publish(self.cfg.key, {"schema": 1, "source": "reported", "states": states})

    def _mark(self, online: bool) -> None:
        if online != self.online:
            self.online = online
            self.availability(self.cfg.key, "online" if online else "offline")

    async def run(self) -> None:
        while True:
            try:
                await self.refresh()
            except Exception:   # a broken device must not stop the others
                log.exception("tuya %s: refresh failed", self.cfg.key)
                self._mark(False)
            self.wake.clear()
            try:
                await asyncio.wait_for(self.wake.wait(), self.cfg.poll_s)
            except asyncio.TimeoutError:
                pass

    # ---- writing ----
    async def command(self, cap: str, action: str, params: dict) -> dict:
        if self.online is False:
            return {"status": "failed", "detail": "tuya device does not answer on the LAN"}
        if cap == "remote":
            return await self._remote(action, params)
        dp, value = self._write_for(cap, action, params)
        if dp is None:
            return {"status": "rejected", "reason": "invalid_params", "detail": f"{cap}.{action} not in profile {self.cfg.profile}"}
        if cap == "breaker" and action == "close":
            tripped = self.last.get("breaker", {}).get("tripped")
            if tripped is True:
                return {"status": "rejected", "reason": "safety_rule", "detail": "breaker tripped: reset it on site"}
        async with self.lock:
            res = await asyncio.to_thread(self.client.set_value, dp, value)
        if isinstance(res, dict) and res.get("Error"):
            return {"status": "failed", "detail": str(res.get("Error"))[:200]}
        self.wake.set()   # read back now: only the device's own answer confirms
        return {"status": "acked"}

    def _write_for(self, cap: str, action: str, params: dict):
        d = self.cfg.dps
        if cap == "switch" and "switch" in d:
            on = {"turn_on": True, "turn_off": False}.get(action)
            if action == "toggle":
                cur = self.last.get("switch", {}).get("on")
                on = None if cur is None else not cur
            return (d["switch"], on) if on is not None else (None, None)
        if cap == "breaker" and "breaker" in d and action in ("close", "open"):
            return d["breaker"], action == "close"
        if cap == "dimmer" and "brightness_1000" in d and action == "set_brightness":
            return d["brightness_1000"], max(10, min(1000, int(params["brightness"]) * 10))
        return None, None

    async def _remote(self, action: str, params: dict) -> dict:
        button = params["button"]
        if action == "press":
            code = self.codes.get(button)
            if code is None:
                return {"status": "rejected", "reason": "invalid_params", "detail": f"button '{button}' is not learned"}
            async with self.lock:
                await asyncio.to_thread(self.client.send_button, code)
            return {"status": "acked"}   # IR: sent, never "confirmed" (no feedback)
        if action == "forget":
            self.codes.pop(button, None)
            self.save_codes(self.codes)
            self.wake.set()
            return {"status": "acked"}
        if action == "learn":
            if self.learning:
                return {"status": "rejected", "reason": "invalid_params", "detail": "already learning a button"}
            self.learning = True
            asyncio.get_running_loop().create_task(self._learn(button))
            return {"status": "acked"}   # confirmed later, when the code is really captured
        return {"status": "rejected", "reason": "invalid_params", "detail": action}

    async def _learn(self, button: str) -> None:
        try:
            async with self.lock:
                code = await asyncio.to_thread(self.client.receive_button, 25)
            if code:
                self.codes[button] = code
                self.save_codes(self.codes)
                log.info("tuya %s: learned '%s'", self.cfg.key, button)
            else:
                log.info("tuya %s: nothing received for '%s'", self.cfg.key, button)
        finally:
            self.learning = False
            self.wake.set()


class TuyaBridge:
    """All Tuya devices of the home. `sync(devices)` follows the cloud config."""

    def __init__(self, publish, availability, store_get, store_put, client_factory=default_client):
        self.publish = publish
        self.availability = availability
        self.store_get = store_get
        self.store_put = store_put
        self.client_factory = client_factory
        self.devices: Dict[str, TuyaDevice] = {}
        self._sigs: Dict[str, tuple] = {}

    def has(self, key: str) -> bool:
        return key in self.devices

    def sync(self, devices: Dict[str, dict]) -> None:
        wanted = {}
        for key, d in devices.items():
            cfg = TuyaConfig.from_device(d) if d.get("enabled", True) else None
            if cfg:
                wanted[key] = cfg
        for key in list(self.devices):
            if key not in wanted or self._sig(wanted[key]) != self._sigs.get(key):
                self._drop(key)
        for key, cfg in wanted.items():
            if key in self.devices:
                continue
            codes = dict(self.store_get(f"ir:{key}") or {})
            dev = TuyaDevice(cfg, self.client_factory(cfg), self.publish, self.availability, codes,
                             save_codes=lambda c, k=key: self.store_put(f"ir:{k}", dict(c)))
            self.devices[key] = dev
            self._sigs[key] = self._sig(cfg)
            try:
                dev.task = asyncio.get_running_loop().create_task(dev.run())
            except RuntimeError:
                pass  # no loop (config applied at import/test time): started by start()
            log.info("tuya %s: %s at %s (v%s)", key, cfg.profile, cfg.ip, cfg.version)

    def start(self) -> None:
        for dev in self.devices.values():
            if dev.task is None:
                dev.task = asyncio.get_running_loop().create_task(dev.run())

    @staticmethod
    def _sig(cfg: TuyaConfig) -> tuple:
        return (cfg.profile, cfg.device_id, cfg.ip, cfg.local_key, cfg.version, tuple(sorted(cfg.dps.items())), cfg.poll_s)

    def _drop(self, key: str) -> None:
        dev = self.devices.pop(key)
        self._sigs.pop(key, None)
        if dev.task:
            dev.task.cancel()

    async def command(self, key: str, cap: str, action: str, params: dict) -> dict:
        return await self.devices[key].command(cap, action, params)

    async def stop(self) -> None:
        for key in list(self.devices):
            self._drop(key)
        await asyncio.sleep(0)
