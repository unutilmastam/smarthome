"""Home Hub gateway: cloud <-> local bridge.

Loops: heartbeat (30 s), command polling (1-2 s, exponential backoff on errors),
config refresh, MQTT listener, outbox flush (offline buffer), periodic full report.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

import aiomqtt

from gateway.backend import BackendClient, BackendError
from gateway.config import GatewaySettings
from gateway.contracts import Contracts
from gateway.expectations import expectation
from gateway.store import Store
from gateway.telemetry import RAW_RETENTION, Aggregator
from gateway.timeutil import iso, parse_ts, utcnow
from gateway.verifier import verify_envelope

log = logging.getLogger("gateway")

ALLOWED_DEVICE_REJECT = {"safety_rule", "invalid_params", "forbidden"}


@dataclass
class Pending:
    device_key: str
    capability: str
    ack: asyncio.Future
    check: Optional[object] = None
    published: bool = False
    confirmed: asyncio.Event = field(default_factory=asyncio.Event)


class Gateway:
    def __init__(self, settings: GatewaySettings, backend: Optional[BackendClient] = None,
                 store: Optional[Store] = None, contracts: Optional[Contracts] = None):
        self.s = settings
        self.contracts = contracts or Contracts(settings.contracts_dir)
        self.store = store or Store(settings.db_path)
        self.backend = backend or BackendClient(settings.backend_url, settings.hub_token)
        self.devices: Dict[str, dict] = {}
        cached = self.store.get_kv("config")
        if cached:
            self._apply_config(cached)
        self.mqtt: Optional[aiomqtt.Client] = None
        self.mqtt_connected = asyncio.Event()
        self.pending: Dict[str, Pending] = {}
        self.dirty: Dict[str, Set[tuple]] = {}
        self.dirty_availability: Set[str] = set()
        self.backend_ok = False
        self.home_id: Optional[str] = (cached or {}).get("home", {}).get("id") if cached else None
        self.cloud: Optional[aiomqtt.Client] = None
        self.cloud_connected = asyncio.Event()
        self.cloud_dirty: Set[str] = set()
        self.aggregator = Aggregator(self.store)
        self._tasks: list = []
        self._stop = asyncio.Event()

    # ---- lifecycle -------------------------------------------------------------------
    async def run(self) -> None:
        self._tasks = [asyncio.create_task(c) for c in (
            self._mqtt_loop(), self._heartbeat_loop(), self._config_loop(),
            self._poll_loop(), self._flush_loop(), self._full_report_loop(),
            self._cloud_loop(), self._cloud_publish_loop())]
        await self._stop.wait()

    async def stop(self) -> None:
        self._stop.set()
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    # ---- config ------------------------------------------------------------------------
    def _apply_config(self, cfg: dict) -> None:
        self.devices = {d["key"]: d for d in cfg.get("devices", [])}
        self.home_id = (cfg.get("home") or {}).get("id")

    async def refresh_config(self) -> None:
        cfg = await self.backend.config()
        self.store.put_kv("config", cfg)
        self._apply_config(cfg)

    async def _config_loop(self) -> None:
        while True:
            try:
                await self.refresh_config()
            except BackendError as exc:
                log.warning("config refresh failed: %s", exc)
            await asyncio.sleep(self.s.config_refresh_s)

    # ---- heartbeat -------------------------------------------------------------------
    def health(self) -> dict:
        avail = self.store.availability()
        return {"mqtt_connected": self.mqtt_connected.is_set(),
                "outbox": self.store.outbox_size(),
                "devices_online": sum(1 for v in avail.values() if v == "online"),
                "devices_known": len(self.devices)}

    async def _heartbeat_loop(self) -> None:
        while True:
            try:
                await self.backend.heartbeat(self.s.version, self.health())
                self.backend_ok = True
            except BackendError as exc:
                self.backend_ok = False
                log.warning("heartbeat failed: %s", exc)
            await asyncio.sleep(self.s.heartbeat_interval_s)

    # ---- command polling ---------------------------------------------------------------
    async def poll_once(self) -> int:
        envelopes = await self.backend.commands()
        for env in envelopes:
            asyncio.create_task(self.execute(env))
        return len(envelopes)

    async def _poll_loop(self) -> None:
        delay = self.s.poll_interval_s
        while True:
            try:
                await self.poll_once()
                self.backend_ok = True
                delay = self.s.poll_interval_s
            except BackendError as exc:
                self.backend_ok = False
                log.warning("poll failed: %s (retry in %.1fs)", exc, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.s.poll_max_backoff_s)
                continue
            await asyncio.sleep(delay)

    # ---- execution -------------------------------------------------------------------------
    def _ack(self, command_id: str, status: str, reason: Optional[str] = None,
             detail: Optional[str] = None) -> None:
        a = {"schema": 1, "command_id": command_id, "status": status, "ts": iso(utcnow())}
        if reason:
            a["reason"] = reason
        if detail:
            a["detail"] = detail[:500]
        self.store.enqueue("ack", a)

    async def execute(self, env: dict) -> str:
        """Verify and run one command. Returns the final local outcome."""
        verdict = verify_envelope(
            env, key=self.s.signing_key, contracts=self.contracts, store=self.store,
            devices=self.devices, availability=self.store.availability(), now=utcnow(),
            skew_s=self.s.clock_skew_s)
        if not verdict.ok and verdict.reason == "replay":
            # Same command seen before (polling + broker both deliver, ADR 0008) or a
            # replay attack. Never executed again; no ack, so an in-flight command is
            # not turned into "rejected" by its own duplicate.
            log.info("duplicate/replayed command %s ignored", verdict.command_id)
            return "duplicate"
        if not verdict.ok:
            log.warning("rejected %s: %s (%s)", verdict.command_id, verdict.reason,
                        verdict.detail)
            if verdict.command_id:
                if verdict.reason != "replay":
                    self.store.set_outcome(verdict.command_id, "rejected")
                self._ack(verdict.command_id, "rejected", verdict.reason, verdict.detail)
            return f"rejected:{verdict.reason}"

        p = verdict.payload
        cid, key, cap = p["command_id"], p["device_key"], p["capability"]
        prev = {a: (self.store.get_state(key, cap, a) or {}).get("value")
                for a in self.contracts.capabilities[cap]["attributes"]}
        pend = Pending(key, cap, asyncio.get_running_loop().create_future(),
                       expectation(cap, p["action"], p["params"], prev))
        self.pending[cid] = pend
        try:
            return await self._run(cid, p, pend)
        finally:
            self.pending.pop(cid, None)

    async def _run(self, cid: str, p: dict, pend: Pending) -> str:
        cmd = {"schema": 1, "command_id": cid, "capability": p["capability"],
               "action": p["action"], "params": p["params"]}
        try:
            if self.mqtt is None or not self.mqtt_connected.is_set():
                raise aiomqtt.MqttError("local broker not connected")
            pend.published = True
            await self.mqtt.publish(f"home/{p['device_key']}/cmd", json.dumps(cmd), qos=1)
        except aiomqtt.MqttError as exc:
            self.store.set_outcome(cid, "failed")
            self._ack(cid, "failed", "device_offline", f"local mqtt: {exc}")
            return "failed:device_offline"

        try:
            dev_ack = await asyncio.wait_for(pend.ack, self.s.device_ack_timeout_s)
        except asyncio.TimeoutError:
            self.store.set_outcome(cid, "failed")
            self._ack(cid, "failed", "device_offline", "device did not ack in time")
            return "failed:device_offline"

        status = dev_ack.get("status")
        if status == "rejected":
            reason = dev_ack.get("reason") if dev_ack.get("reason") in ALLOWED_DEVICE_REJECT \
                else "safety_rule"
            self.store.set_outcome(cid, "rejected")
            self._ack(cid, "rejected", reason, dev_ack.get("detail") or "rejected by device")
            return f"rejected:{reason}"
        if status == "failed":
            self.store.set_outcome(cid, "failed")
            self._ack(cid, "failed", "device_error", dev_ack.get("detail") or "device error")
            return "failed:device_error"

        self._ack(cid, "acked")
        self.store.set_outcome(cid, "acked")
        if pend.check is None:
            return "acked"
        spec = self.contracts.capabilities[p["capability"]]
        cfg = self.devices.get(p["device_key"], {}).get("capabilities", {}).get(
            p["capability"]) or {}
        timeout = cfg.get("confirm_timeout_s") or self.s.default_confirm_timeout_s
        try:
            await asyncio.wait_for(pend.confirmed.wait(), timeout)
        except asyncio.TimeoutError:
            if "confirm_attribute" in spec:
                self.store.set_outcome(cid, "failed")
                self._ack(cid, "failed", "no_feedback",
                          f"{spec['confirm_attribute']} did not change within {timeout}s")
                return "failed:no_feedback"
            return "acked"
        self.store.set_outcome(cid, "confirmed")
        self._ack(cid, "confirmed")
        return "confirmed"

    # ---- local MQTT --------------------------------------------------------------------
    async def _mqtt_loop(self) -> None:
        delay = 1.0
        while True:
            try:
                async with aiomqtt.Client(
                    hostname=self.s.mqtt_host, port=self.s.mqtt_port,
                    username=self.s.mqtt_username, password=self.s.mqtt_password,
                    identifier="smarthome-gateway",
                ) as client:
                    self.mqtt = client
                    for t in ("state", "telemetry", "availability", "ack"):
                        await client.subscribe(f"home/+/{t}", qos=1)
                    self.mqtt_connected.set()
                    delay = 1.0
                    async for msg in client.messages:
                        try:
                            self.handle_message(str(msg.topic), msg.payload)
                        except Exception:  # never let one bad message kill the bridge
                            log.exception("bad message on %s", msg.topic)
            except aiomqtt.MqttError as exc:
                log.warning("local mqtt: %s (reconnect in %.0fs)", exc, delay)
            finally:
                self.mqtt_connected.clear()
                self.mqtt = None
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30.0)

    def handle_message(self, topic: str, raw: bytes) -> None:
        parts = topic.split("/")
        if len(parts) != 3 or parts[0] != "home":
            return
        key, kind = parts[1], parts[2]
        if kind == "availability":
            status = raw.decode("utf-8", "replace").strip()
            if status in ("online", "offline"):
                self.store.set_availability(key, status)
                self.dirty_availability.add(key)
                self.cloud_dirty.add(key)
            return
        try:
            msg = json.loads(raw)
        except ValueError:
            log.warning("non-JSON on %s", topic)
            return
        if kind == "ack":
            if self.contracts.local["ack"].is_valid(msg):
                pend = self.pending.get(msg["command_id"])
                if pend and pend.device_key == key and not pend.ack.done():
                    pend.ack.set_result(msg)
            return
        if kind in ("state", "telemetry"):
            self._handle_state(key, msg)

    def _handle_state(self, key: str, msg: dict) -> None:
        if not self.contracts.local["state"].is_valid(msg):
            log.warning("invalid state message from %s", key)
            return
        source = msg.get("source", "reported")
        now = utcnow()
        ts = now
        if "ts" in msg:
            dev_ts = parse_ts(msg["ts"])
            if abs((dev_ts - now).total_seconds()) < 3600:
                ts = dev_ts
        device = self.devices.get(key)
        accepted: Dict[str, Dict[str, object]] = {}
        for cap, attrs in msg["states"].items():
            if cap not in self.contracts.capabilities:
                continue
            if device is not None and cap not in device["capabilities"]:
                continue
            spec_attrs = self.contracts.capabilities[cap]["attributes"]
            for attr, value in attrs.items():
                if attr not in spec_attrs:
                    continue
                if device and f"{cap}.{attr}" in (device.get("unsupported") or []):
                    continue
                if self.contracts.value_errors(cap, attr, value):
                    log.warning("dropping invalid value %s.%s.%s=%r", key, cap, attr, value)
                    continue
                self.store.put_state(key, cap, attr, value, source, iso(ts))
                if isinstance(value, (int, float)) and not isinstance(value, bool) \
                        and source == "reported":
                    self.aggregator.add(key, f"{cap}.{attr}", value, ts)
                self.dirty.setdefault(key, set()).add((cap, attr))
                accepted.setdefault(cap, {})[attr] = value
        if accepted:
            self.cloud_dirty.add(key)
        if source != "reported":
            return  # assumed values never confirm a command
        for pend in list(self.pending.values()):
            if pend.device_key != key or pend.check is None or pend.capability not in accepted:
                continue
            if pend.published and pend.check(accepted[pend.capability]):
                pend.confirmed.set()

    # ---- reporting / offline buffer ------------------------------------------------------
    def _value(self, st: dict) -> dict:
        return {"value": st["value"], "source": st["source"], "quality": "good", "ts": st["ts"]}

    def build_report(self, keys=None, full: bool = False) -> Optional[dict]:
        states = self.store.all_states()
        avail = self.store.availability()
        if full:
            keys = set(states) | set(avail)
        devices = []
        for key in sorted(keys or ()):
            item: dict = {"device_key": key}
            if key in avail:
                item["availability"] = avail[key]
            dev_states = states.get(key, {})
            wanted = None if full else self.dirty.get(key)
            out: Dict[str, dict] = {}
            for cap, attrs in dev_states.items():
                for attr, st in attrs.items():
                    if wanted is not None and (cap, attr) not in wanted:
                        continue
                    out.setdefault(cap, {})[attr] = self._value(st)
            if out:
                item["states"] = out
            if len(item) > 1:
                devices.append(item)
        if not devices:
            return None
        return {"schema": 1, "ts": iso(utcnow()), "devices": devices}

    def queue_dirty(self) -> None:
        keys = set(self.dirty) | self.dirty_availability
        if not keys:
            return
        known = {k for k in keys if not self.devices or k in self.devices}
        report = self.build_report(known)
        self.dirty.clear()
        self.dirty_availability.clear()
        if report:
            self.store.enqueue("report", report)

    async def flush_once(self) -> bool:
        """Send buffered acks then reports, oldest first. False if the backend is unreachable."""
        self.queue_dirty()
        self.queue_telemetry()
        for kind in ("ack", "report", "telemetry"):
            while True:
                items = self.store.peek(kind, 100 if kind == "ack" else 1)
                if not items:
                    break
                try:
                    if kind == "ack":
                        await self.backend.acks([p for _, p in items])
                    elif kind == "report":
                        await self.backend.report(items[0][1])
                    else:
                        await self.backend.telemetry(items[0][1])
                except BackendError as exc:
                    if exc.permanent:
                        log.error("dropping %s rejected by backend: %s", kind, exc)
                        self.store.ack_outbox([i for i, _ in items])
                        continue
                    self.backend_ok = False
                    return False
                self.store.ack_outbox([i for i, _ in items])
        return True

    def queue_telemetry(self, now=None) -> None:
        items = [i for i in self.aggregator.close_minutes(now)
                 if not self.devices or i["device_key"] in self.devices]
        for start in range(0, len(items), 2000):
            self.store.enqueue("telemetry", {"schema": 1, "items": items[start:start + 2000]})

    async def _flush_loop(self) -> None:
        while True:
            await self.flush_once()
            await asyncio.sleep(self.s.flush_interval_s)

    async def _full_report_loop(self) -> None:
        while True:
            await asyncio.sleep(self.s.full_report_interval_s)
            if not self.store.peek("report", 1):
                report = self.build_report(full=True)
                if report:
                    report["devices"] = [d for d in report["devices"]
                                         if not self.devices or d["device_key"] in self.devices]
                    if report["devices"]:
                        self.store.enqueue("report", report)
            self.store.purge_executed(self.s.executed_retention_days)
            self.store.purge_raw(RAW_RETENTION)

    # ---- managed cloud broker (ADR 0008): fast path, never required ----------------------
    async def _cloud_loop(self) -> None:
        if not self.s.cloud_mqtt_host:
            return
        delay = 1.0
        while True:
            while not self.home_id:
                await asyncio.sleep(0.5)
            home = self.home_id
            try:
                tls = aiomqtt.TLSParameters() if self.s.cloud_mqtt_tls else None
                async with aiomqtt.Client(
                    hostname=self.s.cloud_mqtt_host, port=self.s.cloud_mqtt_port,
                    username=self.s.cloud_mqtt_username, password=self.s.cloud_mqtt_password,
                    identifier=f"hub-{home}", tls_params=tls,
                ) as client:
                    self.cloud = client
                    await client.subscribe(f"sh/v1/{home}/cmd", qos=1)
                    self.cloud_connected.set()
                    self.cloud_dirty.update(self.store.availability())
                    delay = 1.0
                    async for msg in client.messages:
                        try:
                            env = json.loads(msg.payload)
                        except ValueError:
                            log.warning("non-JSON command from cloud broker")
                            continue
                        asyncio.create_task(self.execute(env))
            except aiomqtt.MqttError as exc:
                log.warning("cloud mqtt: %s (polling continues; retry in %.0fs)", exc, delay)
            finally:
                self.cloud_connected.clear()
                self.cloud = None
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60.0)

    def cloud_messages(self, keys) -> list:
        """Retained state/availability messages for the cloud broker (no telemetry history)."""
        states = self.store.all_states()
        avail = self.store.availability()
        out = []
        for key in sorted(keys):
            dev = self.devices.get(key)
            if dev is None:
                continue
            base = f"sh/v1/{self.home_id}/dev/{dev['id']}"
            if key in avail:
                out.append((f"{base}/availability",
                            {"schema": 1, "device_key": key, "status": avail[key],
                             "ts": iso(utcnow())}))
            if states.get(key):
                out.append((f"{base}/state", {
                    "schema": 1, "device_key": key, "ts": iso(utcnow()),
                    "states": {c: {a: self._value(v) for a, v in attrs.items()}
                               for c, attrs in states[key].items()}}))
        return out

    async def _cloud_publish_loop(self) -> None:
        if not self.s.cloud_mqtt_host:
            return
        last_health = 0.0
        while True:
            await asyncio.sleep(0.2)
            client = self.cloud
            if client is None or not self.cloud_connected.is_set():
                continue
            keys, self.cloud_dirty = self.cloud_dirty, set()
            try:
                for topic, payload in self.cloud_messages(keys):
                    await client.publish(topic, json.dumps(payload), qos=1, retain=True)
                loop_t = asyncio.get_running_loop().time()
                if loop_t - last_health >= self.s.heartbeat_interval_s:
                    last_health = loop_t
                    await client.publish(f"sh/v1/{self.home_id}/hub/health",
                                         json.dumps({"schema": 1, "ts": iso(utcnow()),
                                                     **self.health()}), qos=1, retain=True)
            except aiomqtt.MqttError as exc:
                self.cloud_dirty |= keys
                log.warning("cloud publish failed: %s", exc)
