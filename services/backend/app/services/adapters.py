"""Devices that are not ours (ADR 0016): which connection settings each adapter needs.

Tuya profiles must match the hub's (services/hub/gateway/tuya.py PROFILE_CAPS): a profile
decides the capabilities, and attributes it has no data point for are listed as
unsupported, so they show as "not supported" instead of a made-up value.
"""
import ipaddress
import re
from typing import Dict, List, Optional, Tuple

from app.core.errors import validation_error

TUYA_PROFILES: Dict[str, Tuple[List[str], List[str]]] = {
    # profile: (capabilities, unsupported attributes)
    "switch": (["switch"], []),
    "plug_meter": (["switch", "power_meter"], ["power_meter.power_factor", "power_meter.frequency"]),
    "breaker": (["breaker", "power_meter"], ["power_meter.power_factor", "power_meter.frequency"]),
    "light": (["switch", "dimmer"], []),
    "ir": (["remote"], []),
}
TUYA_DPS_NAMES = {"switch", "current_ma", "power_w10", "voltage_v10", "energy_wh", "breaker",
                  "phase_a", "energy_kwh100", "fault", "brightness_1000"}
TUYA_VERSIONS = {"3.1", "3.2", "3.3", "3.4", "3.5"}


def check_connection(adapter: str, connection: Optional[dict], capabilities: Dict[str, dict],
                     unsupported: List[str], has_secret: bool) -> List[str]:
    """Validates the connection for the adapter; returns the unsupported list to store."""
    if adapter != "tuya":
        if connection:
            raise validation_error(f"adapter '{adapter}' takes no connection settings")
        return unsupported
    c = connection or {}
    allowed = {"profile", "device_id", "ip", "version", "dps", "poll_s"}
    extra = set(c) - allowed
    if extra:
        raise validation_error(f"unknown connection fields: {sorted(extra)}")
    profile = c.get("profile")
    if profile not in TUYA_PROFILES:
        raise validation_error(f"connection.profile must be one of {sorted(TUYA_PROFILES)}")
    if not re.fullmatch(r"[A-Za-z0-9]{10,32}", str(c.get("device_id") or "")):
        raise validation_error("connection.device_id: the Device ID from Tuya (10-32 letters/digits)")
    try:
        ip = ipaddress.ip_address(str(c.get("ip") or ""))
    except ValueError:
        raise validation_error("connection.ip: the device's address on the home network, e.g. 192.168.1.50")
    if not ip.is_private:
        raise validation_error("connection.ip must be a home-network (private) address")
    if str(c.get("version", "3.3")) not in TUYA_VERSIONS:
        raise validation_error(f"connection.version must be one of {sorted(TUYA_VERSIONS)}")
    for name, dp in (c.get("dps") or {}).items():
        if name not in TUYA_DPS_NAMES or not isinstance(dp, int) or not 1 <= dp <= 255:
            raise validation_error(f"connection.dps.{name}: a data point number 1-255")
    poll = c.get("poll_s", 5)
    if not isinstance(poll, (int, float)) or not 2 <= poll <= 60:
        raise validation_error("connection.poll_s must be 2-60")
    caps, missing = TUYA_PROFILES[profile]
    if sorted(capabilities) != sorted(caps):
        raise validation_error(f"tuya profile '{profile}' provides exactly {caps}")
    if not has_secret:
        raise validation_error("the device's Local Key is required (secret)")
    return sorted(set(unsupported) | set(missing))
