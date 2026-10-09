"""What state proves that a command really happened (ARCHITECTURE 4.3).

`confirmed` is only sent when a state report received AFTER the command matches.
Capabilities with `confirm_attribute` (cover, lock, contactor, breaker, valve, alarm) fail with
no_feedback when the state does not arrive in time. Others stay `acked`.
IR devices (source=assumed) are never confirmed by their assumed values; an IR climate
unit with a current sensor (`climate.running`, ADR 0012) is confirmed by that sensor.
A valve with a flow sensor is only confirmed open when water really flows.
"""

from typing import Callable, Dict, FrozenSet, Optional

Check = Callable[[Dict[str, object]], Optional[bool]]


def _eq(attr: str, value) -> Check:
    def check(attrs):
        if attr not in attrs:
            return None
        return attrs[attr] == value
    return check


def _in(attr: str, values) -> Check:
    def check(attrs):
        if attr not in attrs:
            return None
        return attrs[attr] in values
    return check


def _all(*checks: Check) -> Check:
    def check(attrs):
        results = [c(attrs) for c in checks]
        if any(r is False for r in results):
            return False
        return None if any(r is None for r in results) else True
    return check


def _flowing(attrs):
    if "flow" not in attrs:
        return None
    return isinstance(attrs["flow"], (int, float)) and attrs["flow"] > 0


def expectation(capability: str, action: str, params: dict,
                previous: Optional[dict] = None,
                unsupported: FrozenSet[str] = frozenset()) -> Optional[Check]:
    if capability == "switch":
        if action == "turn_on":
            return _eq("on", True)
        if action == "turn_off":
            return _eq("on", False)
        if action == "toggle":
            prev = (previous or {}).get("on")
            return _eq("on", not prev) if isinstance(prev, bool) else None
    if capability == "dimmer" and action == "set_brightness":
        return _eq("brightness", params["brightness"])
    if capability == "color":
        if action == "set_rgb":
            return _eq("rgb", list(params["rgb"]))
        if action == "set_color_temp":
            return _eq("color_temp", params["color_temp"])
    if capability == "cover":
        return {"open": _eq("state", "open"), "close": _eq("state", "closed"),
                "stop": _in("state", ("stopped", "open", "closed"))}.get(action)
    if capability == "lock":
        return {"lock": _eq("locked", True), "unlock": _eq("locked", False)}.get(action)
    if capability == "contactor":
        return {"close": _eq("aux_contact_closed", True),
                "open": _eq("aux_contact_closed", False)}.get(action)
    if capability == "breaker":
        return {"close": _eq("closed", True), "open": _eq("closed", False)}.get(action)
    if capability == "valve":
        if action == "open":
            return _eq("open", True) if "valve.flow" in unsupported \
                else _all(_eq("open", True), _flowing)
        return {"close": _eq("open", False)}.get(action)
    if capability == "climate" and action == "set_power" and "climate.running" not in unsupported:
        return _eq("running", params["power"])
    if capability == "alarm":
        return {"arm_away": _eq("state", "armed_away"), "arm_home": _eq("state", "armed_home"),
                "disarm": _eq("state", "disarmed")}.get(action)
    if capability == "remote" and action in ("learn", "forget"):
        # IR has no feedback, but a learned code is real: the hub lists it only once captured.
        want = action == "learn"

        def has_button(attrs):
            if "buttons" not in attrs or not isinstance(attrs["buttons"], list):
                return None
            return (params["button"] in attrs["buttons"]) == want
        return has_button
    if capability == "media":
        return {"turn_on": _eq("on", True), "turn_off": _eq("on", False)}.get(action) \
            or ({"set_volume": _eq("volume", params.get("volume")), "set_mute": _eq("muted", params.get("muted")),
                 "set_channel": _eq("channel", params.get("channel"))}.get(action))
    return None  # other climate actions (IR, assumed) and anything unknown: no confirmation
