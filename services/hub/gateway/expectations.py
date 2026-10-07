"""What state proves that a command really happened (ARCHITECTURE 4.3).

`confirmed` is only sent when a state report received AFTER the command matches.
Capabilities with `confirm_attribute` (cover, lock, contactor, valve) fail with
no_feedback when the state does not arrive in time. Others stay `acked`.
IR devices (source=assumed) are never confirmed.
"""

from typing import Callable, Dict, Optional

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


def expectation(capability: str, action: str, params: dict,
                previous: Optional[dict] = None) -> Optional[Check]:
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
    if capability == "valve":
        return {"open": _eq("open", True), "close": _eq("open", False)}.get(action)
    return None  # climate (IR, assumed) and anything unknown: no confirmation
