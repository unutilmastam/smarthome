"""Virtual devices speaking the local MQTT contract (ARCHITECTURE 5).

Each device has its own MQTT connection with a retained LWT on
home/{key}/availability, exactly like an ESP32 would. Safety limits that real
firmware must enforce (valve max_runtime) are enforced HERE, not by the gateway.

Fault modes: "offline" (connection dropped -> broker publishes LWT),
"unresponsive" (connected, ignores commands), "bad_values" (publishes values
outside the contract), "stuck" (accepts commands, physical state never changes).
Device-specific faults (Phase 11): gate "reed_conflict", climate "ir_blocked",
valve "no_water" / "leaking". Events go to home/{key}/event (ADR 0012).
"""

import json
import random
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class SimDevice:
    capabilities: tuple = ()
    source = "reported"

    def __init__(self, key: str, host: str = "localhost", port: int = 1883,
                 username: Optional[str] = None, password: Optional[str] = None,
                 report_interval_s: Optional[float] = None, **_):
        self.key = key
        self.host, self.port = host, port
        self.username = username if username is not None else key
        self.password = password
        self.report_interval_s = report_interval_s
        self.fault: Optional[str] = None
        self.state: Dict[str, Dict[str, object]] = {}
        self.lock = threading.RLock()
        self.client: Optional[mqtt.Client] = None
        self._timer_stop = threading.Event()
        self._threads: list = []
        self.connected = threading.Event()
        self.commands_seen: list = []

    # ---- connection -------------------------------------------------------------------
    def topic(self, kind: str) -> str:
        return f"home/{self.key}/{kind}"

    def start(self) -> None:
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-{self.key}",
                        protocol=mqtt.MQTTv5)
        if self.username:
            c.username_pw_set(self.username, self.password)
        c.will_set(self.topic("availability"), "offline", qos=1, retain=True)
        c.on_connect = self._on_connect
        c.on_subscribe = self._on_subscribe
        c.on_message = self._on_message
        c.on_disconnect = lambda *a, **k: self.connected.clear()
        self.client = c
        c.connect(self.host, self.port, keepalive=10)
        c.loop_start()
        if not self.connected.wait(10):
            raise RuntimeError(f"{self.key}: could not connect to MQTT")
        if self.report_interval_s:
            t = threading.Thread(target=self._periodic, daemon=True)
            t.start()
            self._threads.append(t)

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code.is_failure:
            return
        client.subscribe(self.topic("cmd"), qos=1)

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties=None):
        # Only "online" once the broker confirmed the cmd subscription (SUBACK);
        # otherwise a command sent in that gap would be lost (seen on slow CI runners).
        client.publish(self.topic("availability"), "online", qos=1, retain=True)
        self.connected.set()
        self.on_online()

    def stop(self, graceful: bool = True) -> None:
        self._timer_stop.set()
        if self.client is None:
            return
        if graceful:
            self.client.publish(self.topic("availability"), "offline", qos=1, retain=True)
            time.sleep(0.05)
            self.client.disconnect()
        else:
            # "Power loss": MQTT v5 reason 0x04 makes the broker publish our LWT.
            self.client.disconnect(reasoncode=ReasonCode(PacketTypes.DISCONNECT,
                                                         "Disconnect with will message"))
        self.client.loop_stop()
        self.client = None

    def set_fault(self, fault: Optional[str]) -> None:
        if fault == "offline":
            self.stop(graceful=False)
        self.fault = fault

    # ---- publishing -----------------------------------------------------------------------
    def publish_state(self, states: Dict[str, Dict[str, object]], source: Optional[str] = None,
                      kind: str = "state") -> None:
        if self.client is None:
            return
        msg = {"schema": 1, "ts": now_iso(), "source": source or self.source, "states": states}
        self.client.publish(self.topic(kind), json.dumps(msg), qos=1, retain=(kind == "state"))

    def set_and_publish(self, cap: str, values: Dict[str, object],
                        source: Optional[str] = None) -> None:
        """Update one capability and publish the device's FULL state: home/{key}/state is
        retained, so a partial message would erase the other capabilities."""
        with self.lock:
            self.state.setdefault(cap, {}).update(values)
            full = {c: dict(v) for c, v in self.state.items()}
            if self.fault == "bad_values":
                full = {c: self.corrupt(c, v) for c, v in full.items()}
        self.publish_state(full, source)

    def corrupt(self, cap: str, values: dict) -> dict:
        for k, v in values.items():
            if isinstance(v, bool):
                values[k] = "maybe"
            elif isinstance(v, (int, float)):
                values[k] = -9999
        return values

    def publish_event(self, type_: str, data: Optional[dict] = None) -> None:
        if self.client is None:
            return
        msg = {"schema": 1, "ts": now_iso(), "type": type_}
        if data:
            msg["data"] = data
        self.client.publish(self.topic("event"), json.dumps(msg), qos=1)

    def ack(self, cid: str, status: str = "acked", reason: Optional[str] = None,
            detail: Optional[str] = None) -> None:
        if self.client is None:
            return
        msg = {"schema": 1, "command_id": cid, "status": status}
        if reason:
            msg["reason"] = reason
        if detail:
            msg["detail"] = detail
        self.client.publish(self.topic("ack"), json.dumps(msg), qos=1)

    # ---- commands ---------------------------------------------------------------------------
    def _on_message(self, client, userdata, message):
        try:
            cmd = json.loads(message.payload)
        except ValueError:
            return
        self.commands_seen.append(cmd)
        if self.fault in ("unresponsive", "offline"):
            return
        cap, action, params = cmd.get("capability"), cmd.get("action"), cmd.get("params") or {}
        if cap not in self.capabilities:
            self.ack(cmd["command_id"], "rejected", "invalid_params", "unknown capability")
            return
        try:
            handler: Callable = getattr(self, f"do_{cap}_{action}")
        except AttributeError:
            self.ack(cmd["command_id"], "rejected", "invalid_params", "unknown action")
            return
        handler(cmd["command_id"], params)

    # ---- hooks ---------------------------------------------------------------------------
    def on_online(self) -> None:
        """Publish the initial (retained) state."""

    def tick(self) -> None:
        """Periodic telemetry."""

    def _periodic(self) -> None:
        while not self._timer_stop.wait(self.report_interval_s):
            if self.client is not None and self.fault not in ("offline", "unresponsive"):
                self.tick()


class LightSim(SimDevice):
    capabilities = ("switch", "dimmer")

    def on_online(self):
        with self.lock:
            on = self.state.get("switch", {}).get("on", False)
            br = self.state.get("dimmer", {}).get("brightness", 100)
        self.set_and_publish("switch", {"on": on})
        self.set_and_publish("dimmer", {"brightness": br})

    def _switch(self, cid, on):
        self.ack(cid)
        if self.fault != "stuck":
            self.set_and_publish("switch", {"on": on})

    def do_switch_turn_on(self, cid, p):
        self._switch(cid, True)

    def do_switch_turn_off(self, cid, p):
        self._switch(cid, False)

    def do_switch_toggle(self, cid, p):
        with self.lock:
            cur = self.state.get("switch", {}).get("on", False)
        self._switch(cid, not cur)

    def do_dimmer_set_brightness(self, cid, p):
        self.ack(cid)
        if self.fault != "stuck":
            self.set_and_publish("dimmer", {"brightness": p["brightness"]})


class PowerMeterSim(SimDevice):
    """PZEM-004T-like meter with realistic noise. Energy only grows."""
    capabilities = ("power_meter",)

    def __init__(self, key, base_current_a: float = 2.0, measures_frequency: bool = True, **kw):
        kw.setdefault("report_interval_s", 2.0)
        super().__init__(key, **kw)
        self.base_current = base_current_a
        self.energy = 0.0
        self.measures_frequency = measures_frequency
        self._last = time.monotonic()

    def reading(self) -> dict:
        v = round(random.gauss(229.5, 1.5), 1)
        i = max(0.0, round(random.gauss(self.base_current, self.base_current * 0.05), 3))
        pf = round(min(1.0, max(0.0, random.gauss(0.95, 0.01))), 2)
        p = round(v * i * pf, 1)
        now = time.monotonic()
        self.energy += p * (now - self._last) / 3_600_000.0
        self._last = now
        out = {"voltage": v, "current": i, "power": p, "energy": round(self.energy, 4),
               "power_factor": pf}
        if self.measures_frequency:
            out["frequency"] = round(random.gauss(50.0, 0.03), 2)
        return out

    def on_online(self):
        self.tick()

    def tick(self):
        values = self.reading()
        if self.fault == "bad_values":
            values = self.corrupt("power_meter", values)
        self.publish_state({"power_meter": values}, kind="telemetry")


class EnvironmentSim(SimDevice):
    capabilities = ("environment",)

    def __init__(self, key, temperature: float = 22.0, humidity: float = 45.0, **kw):
        kw.setdefault("report_interval_s", 5.0)
        super().__init__(key, **kw)
        self.t, self.h = temperature, humidity

    def on_online(self):
        self.tick()

    def tick(self):
        self.t += random.gauss(0, 0.05)
        self.h = min(100.0, max(0.0, self.h + random.gauss(0, 0.2)))
        values = {"temperature": round(self.t, 1), "humidity": round(self.h, 1)}
        if self.fault == "bad_values":
            values = self.corrupt("environment", values)
        self.publish_state({"environment": values}, kind="telemetry")


class MotionSim(SimDevice):
    capabilities = ("motion",)

    def on_online(self):
        self.set_and_publish("motion", {"detected": False})

    def trigger(self, detected: bool = True):
        self.set_and_publish("motion", {"detected": detected})


class LeakSim(SimDevice):
    capabilities = ("leak",)

    def on_online(self):
        self.set_and_publish("leak", {"wet": False})

    def set_wet(self, wet: bool):
        self.set_and_publish("leak", {"wet": wet})


class GateSim(SimDevice):
    """Gate: motor travel + reed switches. 'open'/'closed' only when the reed says so.

    Like the firmware (devices/esphome/gate.yaml): a photocell interruption while closing
    makes the gate controller stop and reopen (hardware); 'close' is refused while the beam
    is interrupted; both reeds active ("reed_conflict") -> state unknown, commands refused;
    no end reed within 2 x travel time -> 'stopped' + cover.travel_timeout."""
    capabilities = ("cover",)

    def __init__(self, key, travel_time_s: float = 15.0, photocell: bool = True, **kw):
        super().__init__(key, **kw)
        self.travel = travel_time_s
        self.photocell = photocell
        self._move: Optional[threading.Thread] = None
        self._abort = threading.Event()

    def on_online(self):
        with self.lock:
            st = dict(self.state.get("cover", {"position": 0, "state": "closed"}))
        if self.photocell:
            st.setdefault("obstructed", False)
        self.set_and_publish("cover", st)

    def set_fault(self, fault):
        super().set_fault(fault)
        if fault == "reed_conflict":
            self._abort.set()
            self.set_and_publish("cover", {"state": "unknown"})
            self.publish_event("cover.sensor_conflict")

    def set_obstructed(self, blocked: bool):
        """Someone/something is in the photocell beam."""
        self.set_and_publish("cover", {"obstructed": blocked})
        if not blocked:
            return
        self.publish_event("cover.obstructed")
        with self.lock:
            closing = self.state.get("cover", {}).get("state") == "closing"
        if closing:  # the gate controller (hardware) stops and reopens by itself
            self._abort.set()
            if self._move and self._move.is_alive():
                self._move.join(2)
            self._abort = threading.Event()
            self._move = threading.Thread(target=self._run, args=(100,), daemon=True)
            self._move.start()

    def _run(self, target: int):
        with self.lock:
            pos = self.state.get("cover", {}).get("position", 0)
        moving = "opening" if target > pos else "closing"
        self.set_and_publish("cover", {"state": moving, "position": pos})
        steps = 10
        for _ in range(steps):
            if self._abort.wait(self.travel / steps):
                with self.lock:
                    p = self.state["cover"]["position"]
                    st = self.state["cover"].get("state")
                if st != "unknown":
                    self.set_and_publish("cover", {"state": "stopped", "position": p})
                return
            if self.fault == "stuck":
                continue  # motor runs, gate does not move, reed never closes
            pos = max(0, min(100, pos + (10 if target > pos else -10)))
            self.set_and_publish("cover", {"position": pos, "state": moving})
        if self.fault == "stuck":
            # Firmware: end reed not reached within max travel time.
            if not self._abort.wait(self.travel):
                self.set_and_publish("cover", {"state": "stopped"})
                self.publish_event("cover.travel_timeout", {"target": "open" if target else "closed"})
            return
        self.set_and_publish("cover", {"state": "open" if target == 100 else "closed",
                                       "position": target})

    def _refuse(self, cid) -> bool:
        if self.fault == "reed_conflict":
            self.ack(cid, "rejected", "safety_rule", "reed sensor conflict")
            return True
        return False

    def _start(self, cid, target):
        if self._refuse(cid):
            return
        with self.lock:
            blocked = self.state.get("cover", {}).get("obstructed") is True
        if target == 0 and blocked:
            self.ack(cid, "rejected", "safety_rule", "photocell interrupted")
            return
        self.ack(cid)
        self._abort.set()
        if self._move and self._move.is_alive():
            self._move.join(1)
        self._abort = threading.Event()
        self._move = threading.Thread(target=self._run, args=(target,), daemon=True)
        self._move.start()

    def do_cover_open(self, cid, p):
        self._start(cid, 100)

    def do_cover_close(self, cid, p):
        self._start(cid, 0)

    def do_cover_stop(self, cid, p):
        if self._refuse(cid):
            return
        self.ack(cid)
        self._abort.set()


class IRClimateSim(SimDevice):
    """IR air conditioner: no feedback. Commanded values are published as 'assumed';
    only the room temperature sensor and (if fitted) the current sensor are 'reported'.

    current_sensor=True: a CT clamp on the unit's supply reports climate.running
    (ADR 0012). Fault "ir_blocked": the IR code never reaches the unit (nothing runs,
    the room does not cool) - exactly the case 'assumed' can not see."""
    capabilities = ("climate",)

    def __init__(self, key, room_temp: float = 27.0, current_sensor: bool = False,
                 start_delay_s: float = 0.5, cool_rate_c_per_s: float = 0.0, **kw):
        kw.setdefault("report_interval_s", 1.0)
        super().__init__(key, **kw)
        self.room = room_temp
        self.current_sensor = current_sensor
        self.start_delay = start_delay_s
        self.rate = cool_rate_c_per_s
        self.running = False

    def _reported(self):
        vals = {"current_temp": round(self.room, 2)}
        if self.current_sensor:
            vals["running"] = self.running
        self.publish_state({"climate": vals}, source="reported", kind="telemetry")

    def on_online(self):
        self._reported()

    def tick(self):
        with self.lock:
            st = dict(self.state.get("climate", {}))
        if self.running and self.rate:
            target = st.get("target_temp", 24)
            if st.get("mode", "cool") == "heat":
                self.room = min(target, self.room + self.rate)
            else:
                self.room = max(target, self.room - self.rate)
        self._reported()

    def _assumed(self, cid, values):
        self.ack(cid)
        with self.lock:
            self.state.setdefault("climate", {}).update(values)
            full = dict(self.state["climate"])
        self.publish_state({"climate": full}, source="assumed")
        if "power" in values and self.fault != "ir_blocked":
            def switch():
                self.running = bool(values["power"])
                self._reported()
            t = threading.Timer(self.start_delay, switch)
            t.daemon = True
            t.start()

    def do_climate_set_power(self, cid, p):
        self._assumed(cid, {"power": p["power"]})

    def do_climate_set_target_temp(self, cid, p):
        self._assumed(cid, {"target_temp": p["target_temp"]})

    def do_climate_set_mode(self, cid, p):
        self._assumed(cid, {"mode": p["mode"]})

    def do_climate_set_fan(self, cid, p):
        self._assumed(cid, {"fan": p["fan"]})


class ValveSim(SimDevice):
    """Irrigation valve. max_runtime_s is FIRMWARE-enforced: the valve closes on its own
    even if the hub, the internet or the broker disappear.

    Like devices/esphome/irrigation-valve.yaml: flow sensor; "no_water" -> no flow while
    open -> closed after no_flow_s (dry-run protection) + valve.no_flow; "leaking" -> flow
    while closed -> valve.flow_while_closed; physical emergency button -> emergency_stop()."""
    capabilities = ("valve",)

    def __init__(self, key, max_runtime_s: int = 1800, flow_l_min: float = 12.0,
                 no_flow_s: float = 30.0, **kw):
        super().__init__(key, **kw)
        if not max_runtime_s or max_runtime_s <= 0:
            raise ValueError("valve simulator requires max_runtime_s")
        self.max_runtime_s = max_runtime_s
        self.flow = flow_l_min
        self.no_flow_s = no_flow_s
        self._closer: Optional[threading.Timer] = None
        self._dry: Optional[threading.Timer] = None
        self.closed_by_firmware = threading.Event()

    def _flow(self, is_open: bool) -> float:
        if self.fault == "no_water":
            return 0.0
        if self.fault == "leaking" and not is_open:
            return 2.5
        return self.flow if is_open else 0.0

    def on_online(self):
        with self.lock:
            is_open = self.state.get("valve", {}).get("open", False)
        self.set_and_publish("valve", {"open": is_open, "flow": self._flow(is_open),
                                       "remaining_s": 0})

    def set_fault(self, fault):
        super().set_fault(fault)
        if fault == "leaking":
            with self.lock:
                is_open = self.state.get("valve", {}).get("open", False)
            if not is_open:
                self.publish_state({"valve": {"open": False, "flow": self._flow(False),
                                              "remaining_s": 0}})
                self.publish_event("valve.flow_while_closed", {"flow": self._flow(False)})

    def _cancel(self):
        for t in (self._closer, self._dry):
            if t:
                t.cancel()
        self._closer = self._dry = None

    def _close(self, by_firmware: bool, event: Optional[str] = None, data: Optional[dict] = None):
        self._cancel()
        flow = self._flow(False)
        with self.lock:
            self.state.setdefault("valve", {}).update({"open": False, "flow": flow,
                                                       "remaining_s": 0})
        if by_firmware:
            self.closed_by_firmware.set()
        self.publish_state({"valve": {"open": False, "flow": flow, "remaining_s": 0}})
        if event:
            self.publish_event(event, data)

    def emergency_stop(self):
        """Physical emergency button on the controller."""
        self._close(True, "valve.emergency_stop")

    def do_valve_open(self, cid, p):
        asked = int(p["duration_s"])
        run = min(asked, self.max_runtime_s)
        self.ack(cid)
        self._cancel()
        self.closed_by_firmware.clear()
        limited = asked > self.max_runtime_s
        self._closer = threading.Timer(
            run, self._close, args=(True, "valve.runtime_limit" if limited else None,
                                    {"max_runtime_s": self.max_runtime_s} if limited else None))
        self._closer.daemon = True
        self._closer.start()
        if self.fault == "no_water":
            self._dry = threading.Timer(self.no_flow_s, self._close,
                                        args=(True, "valve.no_flow", {"after_s": self.no_flow_s}))
            self._dry.daemon = True
            self._dry.start()
        with self.lock:
            self.state.setdefault("valve", {}).update({"open": True})
        self.publish_state({"valve": {"open": True, "flow": self._flow(True), "remaining_s": run}})

    def do_valve_close(self, cid, p):
        self.ack(cid)
        self._close(by_firmware=False)

    def stop(self, graceful: bool = True):
        # Power is still on for the valve controller: the timer keeps running.
        super().stop(graceful)


class ContactSim(SimDevice):
    """Door/window reed sensor (security zone)."""
    capabilities = ("contact",)

    def on_online(self):
        with self.lock:
            is_open = self.state.get("contact", {}).get("open", False)
        self.set_and_publish("contact", {"open": is_open})

    def set_open(self, is_open: bool):
        self.set_and_publish("contact", {"open": is_open})


class SirenSim(SimDevice):
    """Siren on a relay. Its firmware switches it off after max_on_s on its own."""
    capabilities = ("switch",)

    def __init__(self, key, max_on_s: float = 180.0, **kw):
        super().__init__(key, **kw)
        self.max_on_s = max_on_s
        self._off: Optional[threading.Timer] = None

    def on_online(self):
        self.set_and_publish("switch", {"on": False})

    @property
    def on(self) -> bool:
        with self.lock:
            return bool(self.state.get("switch", {}).get("on"))

    def _set(self, on: bool):
        if self._off:
            self._off.cancel()
            self._off = None
        if on:
            self._off = threading.Timer(self.max_on_s, self._set, args=(False,))
            self._off.daemon = True
            self._off.start()
        self.set_and_publish("switch", {"on": on})

    def do_switch_turn_on(self, cid, p):
        self.ack(cid)
        self._set(True)

    def do_switch_turn_off(self, cid, p):
        self.ack(cid)
        self._set(False)


class ContactorSim(SimDevice):
    """DIN contactor on a circuit (ARCHITECTURE 10). The coil command and the auxiliary
    contact are separate: only the aux contact proves the line really switched.
    Faults: "welded" (contacts stuck closed), "aux_broken" (aux never changes)."""
    capabilities = ("contactor",)

    def __init__(self, key, switch_time_s: float = 0.1, closed: bool = True, **kw):
        super().__init__(key, **kw)
        self.switch_time = switch_time_s
        self.initial = closed

    def on_online(self):
        with self.lock:
            st = self.state.get("contactor", {"commanded_closed": self.initial,
                                              "aux_contact_closed": self.initial})
        self.set_and_publish("contactor", dict(st))

    def _drive(self, cid, closed: bool):
        self.ack(cid)
        self.set_and_publish("contactor", {"commanded_closed": closed})

        def settle():
            if self.fault == "aux_broken":
                return  # aux contact never changes
            # Welded main contacts: the line stays closed whatever the coil does.
            self.set_and_publish("contactor", {"aux_contact_closed": True if self.fault == "welded" else closed})
        t = threading.Timer(self.switch_time, settle)
        t.daemon = True
        t.start()

    def do_contactor_close(self, cid, p):
        self._drive(cid, True)

    def do_contactor_open(self, cid, p):
        self._drive(cid, False)


class BreakerSim(SimDevice):
    """Smart circuit breaker in the panel (ADR 0015). `closed` comes from the breaker's own
    contact; `trip()` simulates the protection (overcurrent): contacts open, `tripped` stays
    set and a remote close is refused (safety_rule) until `reset_on_site()`.
    Faults: "aux_broken" (position contact never changes -> no_feedback)."""
    capabilities = ("breaker",)

    def __init__(self, key, switch_time_s: float = 0.2, closed: bool = True,
                 tripped: bool = False, **kw):
        super().__init__(key, **kw)
        self.switch_time = switch_time_s
        self.initial = closed and not tripped
        self.initial_tripped = tripped

    def on_online(self):
        with self.lock:
            st = self.state.get("breaker", {"closed": self.initial, "tripped": self.initial_tripped})
        self.set_and_publish("breaker", dict(st))

    def trip(self) -> None:
        self.set_and_publish("breaker", {"closed": False, "tripped": True})
        self.publish_event("breaker.tripped", {"cause": "overcurrent"})

    def reset_on_site(self) -> None:
        """Someone checked the circuit and reset the breaker by hand (stays open)."""
        self.set_and_publish("breaker", {"tripped": False})

    def _drive(self, cid, closed: bool):
        with self.lock:
            tripped = self.state.get("breaker", {}).get("tripped") is True
        if closed and tripped:
            self.ack(cid, "rejected", "safety_rule", "breaker tripped: reset on site first")
            self.publish_event("breaker.close_refused")
            return
        self.ack(cid)

        def settle():
            if self.fault != "aux_broken":
                self.set_and_publish("breaker", {"closed": closed})
        t = threading.Timer(self.switch_time, settle)
        t.daemon = True
        t.start()

    def do_breaker_close(self, cid, p):
        self._drive(cid, True)

    def do_breaker_open(self, cid, p):
        self._drive(cid, False)


TYPES = {
    "light": LightSim, "power_meter": PowerMeterSim, "environment": EnvironmentSim,
    "motion": MotionSim, "leak": LeakSim, "gate": GateSim, "ir_climate": IRClimateSim,
    "valve": ValveSim, "contactor": ContactorSim, "contact": ContactSim, "siren": SirenSim,
    "breaker": BreakerSim,
}
