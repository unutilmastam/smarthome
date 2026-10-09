"""Yandex Alisa devices through the Yandex Smart Home API (ADR 0016, section 3).

Alisa devices live in Yandex's cloud, so the hub cannot reach them: our cloud talks to
api.iot.yandex.net with the owner's OAuth token (sealed in the integrations table).

- sync(): cron, every minute — devices and their states. What Yandex reports becomes
  source="reported" with Yandex's own last_updated time. Nothing is guessed: a capability we
  cannot map is left out, a value Yandex does not give stays unknown.
- execute(): a command for a Yandex device is run by the cloud itself (no hub, no HMAC to a
  hub): Yandex "DONE" -> acked, then the device is read back and the command is confirmed
  only if the device REALLY shows the requested value.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.contracts import Contracts
from app.core.secretbox import SecretBoxError, open_ as open_secret
from app.db.types import utcnow
from app.models import Command, Device, DeviceCapability, DeviceState, Integration, Room

log = logging.getLogger("app.yandex")
API = "https://api.iot.yandex.net/v1.0"
TRANSPORT: Optional[httpx.BaseTransport] = None   # tests put an httpx.MockTransport here
CAP = "devices.capabilities."
PROP = "devices.properties."
MODE_TO_CLIMATE = {"cool": "cool", "heat": "heat", "dry": "dry", "fan_only": "fan", "auto": "auto"}
CLIMATE_TO_MODE = {v: k for k, v in MODE_TO_CLIMATE.items()}
FAN = {"auto", "low", "medium", "high"}


class YandexError(Exception):
    def __init__(self, message: str, code: str = "yandex_error"):
        super().__init__(message)
        self.code = code


def _client(token: str, base: str) -> httpx.Client:
    return httpx.Client(base_url=base, timeout=10.0, transport=TRANSPORT,
                        headers={"Authorization": f"Bearer {token}"})


def _call(token: str, method: str, path: str, body: Optional[dict] = None, base: str = API) -> dict:
    try:
        with _client(token, base) as c:
            r = c.request(method, path, json=body)
    except httpx.HTTPError as exc:
        raise YandexError(f"Yandex is not reachable: {exc}", "unreachable")
    if r.status_code == 401:
        raise YandexError("Yandex token is invalid or expired", "token_invalid")
    try:
        data = r.json()
    except ValueError:
        raise YandexError(f"Yandex answered {r.status_code} without JSON")
    if r.status_code >= 400 or data.get("status") not in (None, "ok"):
        raise YandexError(str(data.get("message") or data.get("status") or r.status_code)[:200])
    return data


def token_for(integration: Integration, settings: Settings) -> str:
    try:
        return open_secret(settings.signing_master_key, integration.secret_enc, str(integration.id))
    except SecretBoxError as exc:
        raise YandexError(str(exc), "token_invalid")


# ---- mapping Yandex -> our contract ------------------------------------------------------

def _ts(value) -> Optional[datetime]:
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return None


def device_key(yandex_id: str) -> str:
    return "ya_" + uuid.UUID(yandex_id).hex if _is_uuid(yandex_id) else \
        "ya_" + "".join(ch for ch in yandex_id.lower() if ch.isalnum())[:60]


def _is_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except ValueError:
        return False


def map_device(y: dict) -> Optional[Tuple[Dict[str, dict], Dict[str, Dict[str, Tuple[Any, Optional[datetime]]]], str]]:
    """Returns (capabilities config, states {cap: {attr: (value, ts)}}, icon) or None if
    nothing of the device fits our contract."""
    ytype = str(y.get("type") or "")
    caps: Dict[str, dict] = {}
    states: Dict[str, Dict[str, Tuple[Any, Optional[datetime]]]] = {}

    def put(cap: str, attr: str, value, ts) -> None:
        caps.setdefault(cap, {})
        if value is not None:
            states.setdefault(cap, {})[attr] = (value, ts)

    is_tv = ytype.startswith("devices.types.media_device")
    is_ac = ytype.startswith("devices.types.thermostat")
    for c in y.get("capabilities") or []:
        t = str(c.get("type") or "").replace(CAP, "")
        st = c.get("state") or {}
        inst, val, ts = st.get("instance") or (c.get("parameters") or {}).get("instance"), st.get("value"), _ts(c.get("last_updated"))
        if t == "on_off":
            cap = "media" if is_tv else "climate" if is_ac else "switch"
            put(cap, "power" if cap == "climate" else "on", val if isinstance(val, bool) else None, ts)
        elif t == "range" and inst == "brightness" and not is_tv:
            put("dimmer", "brightness", int(val) if isinstance(val, (int, float)) else None, ts)
        elif t == "range" and inst == "temperature" and is_ac:
            put("climate", "target_temp", val if isinstance(val, (int, float)) and 16 <= val <= 30 else None, ts)
        elif t == "range" and inst in ("volume", "channel") and is_tv:
            ok = isinstance(val, (int, float)) and not isinstance(val, bool)
            put("media", inst, (int(val) if inst == "channel" else val) if ok else None, ts)
        elif t == "toggle" and inst == "mute" and is_tv:
            put("media", "muted", val if isinstance(val, bool) else None, ts)
        elif t == "mode" and inst == "thermostat" and is_ac:
            put("climate", "mode", MODE_TO_CLIMATE.get(val) if isinstance(val, str) else None, ts)
        elif t == "mode" and inst == "fan_speed" and is_ac:
            put("climate", "fan", val if val in FAN else None, ts)
        elif t == "mode" and inst == "input_source" and is_tv:
            put("media", "input", str(val)[:40] if val is not None else None, ts)
    for p in y.get("properties") or []:
        t = str(p.get("type") or "").replace(PROP, "")
        st = p.get("state") or {}
        inst = st.get("instance") or (p.get("parameters") or {}).get("instance")
        val, ts = st.get("value"), _ts(p.get("last_updated"))
        num = val if isinstance(val, (int, float)) and not isinstance(val, bool) else None
        if t == "float":
            if inst == "temperature":
                put("climate" if is_ac else "environment", "current_temp" if is_ac else "temperature", num, ts)
            elif inst == "humidity":
                put("environment", "humidity", num, ts)
            elif inst in ("power", "voltage", "amperage"):
                put("power_meter", {"amperage": "current"}.get(inst, inst), num, ts)
        elif t == "event":
            if inst == "motion":
                put("motion", "detected", None if val is None else val == "detected", ts)
            elif inst == "open":
                put("contact", "open", None if val is None else val == "opened", ts)
            elif inst == "water_leak":
                put("leak", "wet", None if val is None else val == "leak", ts)
    if not caps:
        return None
    icon = "tv" if is_tv else "ac" if is_ac else "bulb" if "light" in ytype else \
        "socket" if "socket" in ytype else "speaker" if "speaker" in ytype else "devices"
    return caps, states, icon


# ---- sync ---------------------------------------------------------------------------------

def sync(db: Session, integration: Integration, contracts: Contracts, settings: Settings) -> dict:
    now = utcnow()
    try:
        data = _call(token_for(integration, settings), "GET", "/user/info", base=settings.yandex_api_base)
    except YandexError as exc:
        integration.status, integration.error = "error", f"{exc.code}: {exc}"[:300]
        db.commit()
        return {"ok": False, "error": integration.error}
    rooms = {r["id"]: r.get("name") for r in data.get("rooms") or []}
    ours = {r.name.strip().lower(): r.id for r in db.scalars(select(Room).where(Room.home_id == integration.home_id))}
    existing = {d.key: d for d in db.scalars(select(Device).where(Device.home_id == integration.home_id,
                                                                    Device.adapter == "yandex"))}
    seen, skipped = set(), []
    for y in data.get("devices") or []:
        mapped = map_device(y)
        if mapped is None:
            skipped.append({"name": y.get("name"), "type": y.get("type")})
            continue
        caps, states, icon = mapped
        key = device_key(str(y["id"]))
        seen.add(key)
        d = existing.get(key)
        if d is None:
            room_name = (rooms.get(y.get("room")) or "").strip().lower()
            d = Device(id=uuid.uuid4(), home_id=integration.home_id, key=key, name=str(y.get("name") or key)[:120],
                       adapter="yandex", protocol="cloud", icon=icon, unsupported=[], availability="unknown",
                       room_id=ours.get(room_name), connection={"yandex_id": str(y["id"]), "type": y.get("type")})
            d.capabilities = [DeviceCapability(capability=c, config_json={}) for c in caps]
            db.add(d)
            existing[key] = d
        else:
            have = {c.capability for c in d.capabilities}
            for c in set(caps) - have:
                d.capabilities.append(DeviceCapability(capability=c, config_json={}))
        state = y.get("state")
        d.availability = state if state in ("online", "offline") else d.availability
        d.availability_ts = now        # "Yandex answered for this device just now"
        _write_states(d, contracts, states)
    for key, d in existing.items():
        if key not in seen:            # removed in Yandex: kept, but honestly unreachable
            d.availability, d.availability_ts = "offline", now
    integration.status, integration.error, integration.last_sync_at = "ok", None, now
    integration.data = {"scenarios": [{"id": s["id"], "name": s.get("name")} for s in data.get("scenarios") or []
                                      if s.get("is_active", True)],
                        "skipped": skipped[:50]}
    db.commit()
    return {"ok": True, "devices": len(seen), "skipped": len(skipped)}


def _write_states(d: Device, contracts: Contracts, states: Dict[str, Dict[str, Tuple[Any, Optional[datetime]]]]) -> None:
    current = {(s.capability, s.attribute): s for s in d.states}
    for cap, attrs in states.items():
        for attr, (value, ts) in attrs.items():
            if list(contracts.attribute_validator(cap, attr).iter_errors(value)):
                continue          # outside the contract: not shown rather than shown wrong
            st = current.get((cap, attr))
            if st is None:
                st = DeviceState(device_id=d.id, capability=cap, attribute=attr)
                d.states.append(st)
                current[(cap, attr)] = st
            st.value_json, st.source, st.quality, st.ts = value, "reported", "good", ts or utcnow()


# ---- commands -----------------------------------------------------------------------------

def _actions(cap: str, action: str, params: dict) -> List[dict]:
    def a(t, inst, value, relative=False):
        st = {"instance": inst, "value": value}
        if relative:
            st["relative"] = True
        return {"type": CAP + t, "state": st}
    if cap in ("switch", "media") and action in ("turn_on", "turn_off"):
        return [a("on_off", "on", action == "turn_on")]
    if cap == "climate":
        if action == "set_power":
            return [a("on_off", "on", bool(params["power"]))]
        if action == "set_target_temp":
            return [a("range", "temperature", params["target_temp"])]
        if action == "set_mode":
            return [a("on_off", "on", False)] if params["mode"] == "off" else [a("mode", "thermostat", CLIMATE_TO_MODE[params["mode"]])]
        if action == "set_fan":
            return [a("mode", "fan_speed", params["fan"])]
    if cap == "dimmer" and action == "set_brightness":
        return [a("range", "brightness", params["brightness"])]
    if cap == "media":
        return {"set_volume": [a("range", "volume", params.get("volume"))],
                "volume_up": [a("range", "volume", 1, True)], "volume_down": [a("range", "volume", -1, True)],
                "set_channel": [a("range", "channel", params.get("channel"))],
                "channel_up": [a("range", "channel", 1, True)], "channel_down": [a("range", "channel", -1, True)],
                "set_mute": [a("toggle", "mute", params.get("muted"))]}.get(action, [])
    return []


def _expected(cap: str, action: str, params: dict) -> Optional[Tuple[str, Any]]:
    """The attribute value that proves the command happened (None = cannot be proven)."""
    return {("switch", "turn_on"): ("on", True), ("switch", "turn_off"): ("on", False),
            ("media", "turn_on"): ("on", True), ("media", "turn_off"): ("on", False),
            ("climate", "set_power"): ("power", params.get("power")),
            ("climate", "set_target_temp"): ("target_temp", params.get("target_temp")),
            ("dimmer", "set_brightness"): ("brightness", params.get("brightness")),
            ("media", "set_volume"): ("volume", params.get("volume")),
            ("media", "set_mute"): ("muted", params.get("muted")),
            ("media", "set_channel"): ("channel", params.get("channel"))}.get((cap, action))


def execute(db: Session, settings: Settings, contracts: Contracts, cmd: Command, device: Device) -> None:
    from app.services.commands import transition   # circular at import time
    integration = db.scalar(select(Integration).where(Integration.home_id == device.home_id,
                                                      Integration.kind == "yandex"))
    actions = _actions(cmd.capability, cmd.action, cmd.params or {})
    if integration is None or not actions:
        transition(db, cmd, "rejected", "backend", reason="safety_rule" if integration else "device_offline",
                   detail="this action is not available for a Yandex device" if integration else "Yandex is not connected")
        db.commit()
        return
    yid = (device.connection or {}).get("yandex_id")
    transition(db, cmd, "sent", "backend", detail="sent to Yandex")
    try:
        token = token_for(integration, settings)
        res = _call(token, "POST", "/devices/actions", {"devices": [{"id": yid, "actions": actions}]},
                    base=settings.yandex_api_base)
        results = [c.get("state", {}).get("action_result", {}) for dev in res.get("devices") or [] for c in dev.get("capabilities") or []]
        bad = [r for r in results if r.get("status") != "DONE"]
        if not results or bad:
            msg = (bad[0].get("error_message") or bad[0].get("error_code")) if bad else "no result"
            transition(db, cmd, "failed", "backend", reason="device_error", detail=f"Yandex: {msg}"[:300])
            db.commit()
            return
        transition(db, cmd, "acked", "backend", detail="Yandex: DONE")
        db.commit()
        # Read back: only the device's own state confirms.
        y = _call(token, "GET", f"/devices/{yid}", base=settings.yandex_api_base)
        mapped = map_device(y)
        if mapped:
            _write_states(device, contracts, mapped[1])
            device.availability_ts = utcnow()
        want = _expected(cmd.capability, cmd.action, cmd.params or {})
        if want and mapped:
            got = mapped[1].get(cmd.capability, {}).get(want[0])
            if got is not None and got[0] == want[1]:
                transition(db, cmd, "confirmed", "backend", detail="Yandex reports the new state")
        db.commit()
    except YandexError as exc:
        transition(db, cmd, "failed", "backend", reason="device_offline" if exc.code == "unreachable" else "device_error",
                   detail=str(exc)[:300])
        db.commit()


def run_scenario(integration: Integration, settings: Settings, scenario_id: str) -> None:
    _call(token_for(integration, settings), "POST", f"/scenarios/{scenario_id}/actions", base=settings.yandex_api_base)
