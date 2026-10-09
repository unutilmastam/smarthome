"""In-process fake Tuya devices [SIM] (ADR 0016): the same calls tinytuya makes
(status / set_value / send_button / receive_button), with Tuya-like DPS.

Not a protocol emulator: the real local protocol is tinytuya's job and is checked on real
devices (docs/hardware/tests/tuya.md). This fakes the DEVICE behind it.
"""
import base64
import threading
import time
from typing import Dict, List, Optional


def phase_raw(volts: float, amps: float, watts: float) -> str:
    b = int(round(volts * 10)).to_bytes(2, "big") + int(round(amps * 1000)).to_bytes(3, "big") \
        + int(round(watts)).to_bytes(3, "big")
    return base64.b64encode(b).decode()


class FakeTuya:
    """profile: switch | plug_meter | breaker | light | ir."""

    def __init__(self, profile: str, online: bool = True, ignore_writes: bool = False):
        self.profile = profile
        self.online = online
        self.ignore_writes = ignore_writes   # a device that answers but does not switch
        self.lock = threading.Lock()
        self.sent: List[str] = []            # IR codes sent
        self.next_ir: Optional[str] = None   # what the "original remote" sends during learning
        self.dps: Dict[str, object] = {
            "switch": {"1": False},
            "plug_meter": {"1": False, "17": 1234, "18": 0, "19": 0, "20": 2301},
            "breaker": {"16": True, "6": phase_raw(229.8, 1.25, 280), "1": 12345, "9": 0},
            "light": {"20": False, "22": 500},
            "ir": {"1": "study_exit"},
        }[profile]

    # ---- tinytuya API ----
    def status(self, nowait=False):
        if not self.online:
            return {"Error": "Network Error: Device Unreachable", "Err": "905"}
        with self.lock:
            return {"dps": dict(self.dps)}

    def set_value(self, index, value, nowait=False):
        if not self.online:
            return {"Error": "Network Error: Device Unreachable", "Err": "905"}
        with self.lock:
            if not self.ignore_writes:
                self.dps[str(index)] = value
                if self.profile == "plug_meter" and str(index) == "1":
                    self.dps["19"] = 1205 if value else 0
                    self.dps["18"] = 530 if value else 0
            return {"dps": {str(index): value}}

    def send_button(self, base64_code):
        if not self.online:
            raise OSError("unreachable")
        self.sent.append(base64_code)

    def receive_button(self, timeout=30):
        deadline = time.time() + min(timeout, 2)
        while time.time() < deadline:
            if self.next_ir:
                code, self.next_ir = self.next_ir, None
                return code
            time.sleep(0.02)
        return None

    # ---- what happens in the real world ----
    def trip(self) -> None:
        """Overcurrent: the breaker opens itself and reports a fault."""
        with self.lock:
            self.dps["16"] = False
            self.dps["9"] = 1

    def reset_on_site(self) -> None:
        with self.lock:
            self.dps["9"] = 0
