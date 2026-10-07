"""Full chain in one process [SIM]:

phone (test client) -> backend (FastAPI, SQLite) -> hub gateway (HTTP polling)
-> real Mosquitto (ACL) -> simulated devices -> ack/state -> gateway -> backend.
"""

import asyncio
import os
import time
import uuid
from datetime import datetime

import httpx
import pytest

from conftest import CONTRACTS, GW_PASSWORD, SIM_PASSWORD, add_backend_to_path

os.environ["ENV"] = "test"
for _k in ("DATABASE_URL", "JWT_SECRET", "SIGNING_MASTER_KEY"):
    os.environ.pop(_k, None)
add_backend_to_path()

from fastapi.testclient import TestClient  # noqa: E402

from app.cli import create_owner  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import Database, make_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from gateway.backend import BackendClient  # noqa: E402
from gateway.config import GatewaySettings  # noqa: E402
from gateway.core import Gateway  # noqa: E402
from simulator.devices import (  # noqa: E402
    GateSim, IRClimateSim, LightSim, PowerMeterSim, ValveSim,
)

PASSWORD = "correct-horse-battery"
PIN = "4821"

DEVICES = {
    "garden_lights": {"capabilities": {"switch": {}, "dimmer": {}}},
    "front_gate": {"capabilities": {"cover": {"confirm_timeout_s": 4}}},
    "ac_bedroom": {"capabilities": {"climate": {}}},
    "garden_valve": {"capabilities": {"valve": {"max_runtime_s": 600}}},
    "main_meter": {"capabilities": {"power_meter": {}},
                   "unsupported": ["power_meter.frequency"]},
}


class FlakyTransport(httpx.AsyncBaseTransport):
    """Lets a test cut the hub's internet connection."""

    def __init__(self, inner):
        self.inner = inner
        self.down = False

    async def handle_async_request(self, request):
        if self.down:
            raise httpx.ConnectError("internet down (simulated)")
        return await self.inner.handle_async_request(request)


class Stack:
    def __init__(self, broker, tmp_path, realtime=None, **gw_overrides):
        self.broker = broker
        settings = Settings(_env_file=None, env="test")
        engine = make_engine(f"sqlite:///{tmp_path / 'backend.db'}")
        Base.metadata.create_all(engine)
        self.database = Database(settings, engine=engine)
        self.app = create_app(settings, self.database, realtime)
        self.phone = TestClient(self.app)
        with self.database.sessionmaker() as s:
            self.home_id = create_owner(s, "owner@example.com", "Owner", PASSWORD, "Uy").id
        tok = self.phone.post("/api/v1/auth/login",
                              json={"email": "owner@example.com", "password": PASSWORD})
        self.phone.headers["Authorization"] = f"Bearer {tok.json()['data']['access_token']}"
        self.phone.post("/api/v1/auth/pin", json={"password": PASSWORD, "pin": PIN})
        self.ids = {}
        for key, spec in DEVICES.items():
            body = {"key": key, "name": key, "adapter": "esphome", "protocol": "mqtt", **spec}
            r = self.phone.post(f"/api/v1/homes/{self.home_id}/devices", json=body)
            assert r.status_code == 201, r.text
            self.ids[key] = r.json()["data"]["id"]
        hub = self.phone.post(f"/api/v1/homes/{self.home_id}/hubs", json={"name": "hub"})
        self.hub_info = hub.json()["data"]
        self.transport = FlakyTransport(httpx.ASGITransport(app=self.app))
        gw = dict(
            _env_file=None, backend_url="http://backend", hub_token=self.hub_info["hub_token"],
            signing_key_hex=self.hub_info["signing_key_hex"], mqtt_host=broker["host"],
            mqtt_port=broker["port"], mqtt_username="gateway", mqtt_password=GW_PASSWORD,
            db_path=str(tmp_path / "hub.sqlite3"), contracts_dir=CONTRACTS,
            poll_interval_s=0.2, poll_max_backoff_s=0.5, heartbeat_interval_s=0.5,
            config_refresh_s=1, flush_interval_s=0.2, full_report_interval_s=2,
            device_ack_timeout_s=2, default_confirm_timeout_s=3)
        gw.update(gw_overrides)
        self.gw_settings = GatewaySettings(**gw)
        client = httpx.AsyncClient(transport=self.transport, base_url="http://backend")
        self.gateway = Gateway(self.gw_settings,
                               backend=BackendClient("http://backend", self.hub_info["hub_token"],
                                                     client=client))
        kw = dict(host=broker["host"], port=broker["port"], password=SIM_PASSWORD)
        self.sims = {
            "garden_lights": LightSim("garden_lights", **kw),
            "front_gate": GateSim("front_gate", travel_time_s=1.0, **kw),
            "ac_bedroom": IRClimateSim("ac_bedroom", **kw),
            "garden_valve": ValveSim("garden_valve", max_runtime_s=600, **kw),
            "main_meter": PowerMeterSim("main_meter", report_interval_s=0.3, **kw),
        }

    async def start(self):
        for s in self.sims.values():
            await asyncio.to_thread(s.start)
        self.task = asyncio.create_task(self.gateway.run())
        await self.wait(lambda: self.gateway.mqtt_connected.is_set() and self.gateway.devices,
                        "gateway connected")
        await self.wait(self.hub_online, "hub online")

    async def stop(self):
        await self.gateway.stop()
        self.task.cancel()
        for s in self.sims.values():
            await asyncio.to_thread(s.stop)
        self.phone.close()

    def hub_online(self):
        hubs = self.phone.get(f"/api/v1/homes/{self.home_id}/hubs").json()["data"]
        return any(h["online"] for h in hubs)

    async def wait(self, cond, what, timeout=10.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            res = await asyncio.to_thread(cond) if not asyncio.iscoroutinefunction(cond) \
                else await cond()
            if res:
                return res
            await asyncio.sleep(0.1)
        raise AssertionError(f"timeout waiting for: {what}")

    async def send(self, key, capability, action, params=None, **extra):
        body = {"device_id": self.ids[key], "capability": capability, "action": action,
                "params": params or {}, "idempotency_key": uuid.uuid4().hex, **extra}
        r = await asyncio.to_thread(self.phone.post, "/api/v1/commands", json=body)
        return r

    def command(self, cid):
        return self.phone.get(f"/api/v1/commands/{cid}").json()["data"]

    async def wait_status(self, cid, statuses, timeout=10.0):
        statuses = set(statuses)
        last = {}

        def check():
            c = self.command(cid)
            last["c"] = c
            return c if c["status"] in statuses else None
        try:
            return await self.wait(check, f"command {cid} in {statuses}", timeout)
        except AssertionError:
            c = last.get("c") or {}
            raise AssertionError(
                f"command {cid} not in {statuses}: status={c.get('status')} "
                f"reason={c.get('reason')} events={[(e['status'], e['detail']) for e in c.get('events', [])]}")

    def device(self, key):
        return self.phone.get(f"/api/v1/devices/{self.ids[key]}").json()["data"]


@pytest.fixture
def stack(broker, tmp_path):
    return Stack(broker, tmp_path)


def run(stack, scenario):
    async def main():
        await stack.start()
        try:
            await scenario(stack)
        finally:
            await stack.stop()
    asyncio.run(main())


def test_light_on_is_confirmed_end_to_end(stack):
    async def scenario(st):
        r = await st.send("garden_lights", "switch", "turn_on")
        assert r.status_code == 201, r.text
        c = await st.wait_status(r.json()["data"]["id"], {"confirmed", "failed", "rejected",
                                                          "timeout", "expired"})
        assert c["status"] == "confirmed"
        assert [e["status"] for e in c["events"] if e["applied"]] == \
            ["queued", "sent", "acked", "confirmed"]
        await st.wait(lambda: st.device("garden_lights")["capabilities"]["switch"][
            "attributes"]["on"]["value"] is True, "state reported to backend")
        on = st.device("garden_lights")["capabilities"]["switch"]["attributes"]["on"]
        assert (on["source"], on["quality"]) == ("reported", "good")
        assert st.device("garden_lights")["availability"]["status"] == "online"
        r = await st.send("garden_lights", "dimmer", "set_brightness", {"brightness": 30})
        c = await st.wait_status(r.json()["data"]["id"], {"confirmed", "failed"})
        assert c["status"] == "confirmed"
    run(stack, scenario)


def test_gate_confirmed_only_by_reed_switch(stack):
    async def scenario(st):
        r = await st.send("front_gate", "cover", "open", confirm_pin=PIN)
        assert r.status_code == 201, r.text
        cid = r.json()["data"]["id"]
        c = await st.wait_status(cid, {"confirmed", "failed"}, timeout=8)
        assert c["status"] == "confirmed"
        # Confirmation comes from the reed switch at the end of travel (1 s),
        # not from the device ack.
        ts = {e["status"]: datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
              for e in c["events"] if e["applied"]}
        assert (ts["confirmed"] - ts["acked"]).total_seconds() >= 0.8
        # Now the reed switch is broken / gate stuck: no confirmation.
        st.sims["front_gate"].set_fault("stuck")
        r = await st.send("front_gate", "cover", "close", confirm_pin=PIN)
        c = await st.wait_status(r.json()["data"]["id"], {"confirmed", "failed"}, timeout=10)
        assert (c["status"], c["reason"]) == ("failed", "no_feedback")
    run(stack, scenario)


def test_ir_climate_is_assumed_never_confirmed(stack):
    async def scenario(st):
        r = await st.send("ac_bedroom", "climate", "set_power", {"power": True})
        cid = r.json()["data"]["id"]
        await st.wait_status(cid, {"acked"})
        await asyncio.sleep(1.0)
        assert st.command(cid)["status"] == "acked"
        await st.wait(lambda: st.device("ac_bedroom")["capabilities"]["climate"]["attributes"][
            "power"]["value"] is True, "assumed state reported")
        attrs = st.device("ac_bedroom")["capabilities"]["climate"]["attributes"]
        assert attrs["power"]["source"] == "assumed"
        assert attrs["current_temp"]["source"] == "reported"
        assert attrs["fan"]["quality"] == "unknown"
    run(stack, scenario)


def test_unresponsive_device_fails(stack):
    async def scenario(st):
        st.sims["garden_lights"].set_fault("unresponsive")
        r = await st.send("garden_lights", "switch", "turn_on")
        c = await st.wait_status(r.json()["data"]["id"], {"failed", "confirmed"})
        assert (c["status"], c["reason"]) == ("failed", "device_offline")
    run(stack, scenario)


def test_power_loss_lwt_marks_device_offline(stack):
    async def scenario(st):
        await st.wait(lambda: st.device("garden_lights")["capabilities"]["switch"][
            "attributes"]["on"]["quality"] == "good", "initial state reported")
        await asyncio.to_thread(st.sims["garden_lights"].set_fault, "offline")
        await st.wait(lambda: st.device("garden_lights")["availability"]["status"] == "offline",
                      "LWT -> offline in backend")
        on = st.device("garden_lights")["capabilities"]["switch"]["attributes"]["on"]
        assert on["quality"] == "stale"
        r = await st.send("garden_lights", "switch", "turn_on")
        assert (r.status_code, r.json()["error"]["code"]) == (409, "DEVICE_OFFLINE")
    run(stack, scenario)


def test_replayed_and_tampered_envelopes_never_execute(stack):
    async def scenario(st):
        r = await st.send("garden_lights", "switch", "turn_on")
        cid = r.json()["data"]["id"]
        await st.wait_status(cid, {"confirmed"})
        env = None
        from sqlalchemy import select
        from app.models import Command
        with st.database.sessionmaker() as s:
            env = s.scalar(select(Command.envelope).where(Command.id == uuid.UUID(cid)))
        seen = len(st.sims["garden_lights"].commands_seen)
        assert (await st.gateway.execute(env)) == "duplicate"
        forged = {**env, "payload": {**env["payload"], "command_id": str(uuid.uuid4()),
                                     "action": "turn_off"}}
        assert (await st.gateway.execute(forged)) == "rejected:bad_signature"
        await asyncio.sleep(0.3)
        assert len(st.sims["garden_lights"].commands_seen) == seen
    run(stack, scenario)


def test_internet_outage_valve_still_closes_and_buffer_flushes(stack):
    async def scenario(st):
        r = await st.send("garden_valve", "valve", "open", {"duration_s": 2})
        cid = r.json()["data"]["id"]
        c = await st.wait_status(cid, {"confirmed", "failed"})
        assert c["status"] == "confirmed"
        # Internet goes down right after the valve opened.
        st.transport.down = True
        valve = st.sims["garden_valve"]
        closed = await asyncio.to_thread(valve.closed_by_firmware.wait, 5)
        assert closed, "valve must close by itself (firmware max_runtime/duration)"
        await st.wait(lambda: st.gateway.store.outbox_size() > 0, "state buffered offline")
        # Commands cannot even be created now (hub is unreachable from the cloud).
        await asyncio.sleep(1.5)
        hb_down = await asyncio.to_thread(lambda: st.phone.get(
            f"/api/v1/homes/{st.home_id}/hubs").json()["data"][0]["last_seen"])
        st.transport.down = False
        await st.wait(lambda: st.gateway.store.outbox_size() == 0, "outbox flushed")
        await st.wait(lambda: st.device("garden_valve")["capabilities"]["valve"]["attributes"][
            "open"]["value"] is False, "backend sees valve closed after reconnect")
        assert hb_down is not None
    run(stack, scenario)


def test_stale_commands_are_not_executed_after_outage(stack):
    async def scenario(st):
        st.transport.down = True
        await asyncio.sleep(0.5)
        # The backend still thinks the hub is online (90 s window) and queues a command.
        r = await st.send("garden_lights", "switch", "turn_on")
        assert r.status_code == 201
        cid = r.json()["data"]["id"]
        from sqlalchemy import select
        from app.models import Command
        from datetime import timedelta
        with st.database.sessionmaker() as s:
            c = s.scalar(select(Command).where(Command.id == uuid.UUID(cid)))
            c.expires_at -= timedelta(seconds=11)
            s.commit()
        st.transport.down = False
        c = await st.wait_status(cid, {"expired", "confirmed", "sent"})
        assert c["status"] == "expired"
        await asyncio.sleep(0.5)
        assert not any(m["command_id"] == cid for m in st.sims["garden_lights"].commands_seen)
    run(stack, scenario)


def test_meter_telemetry_and_bad_values(stack):
    async def scenario(st):
        await st.wait(lambda: st.device("main_meter")["capabilities"]["power_meter"][
            "attributes"]["voltage"]["quality"] == "good", "telemetry arrived")
        attrs = st.device("main_meter")["capabilities"]["power_meter"]["attributes"]
        assert 200 < attrs["voltage"]["value"] < 260
        assert attrs["frequency"]["quality"] == "not_supported"   # meter can't measure it
        st.sims["main_meter"].set_fault("bad_values")
        await asyncio.sleep(1.5)
        v = st.device("main_meter")["capabilities"]["power_meter"]["attributes"]["voltage"]
        assert v["value"] != -9999
    run(stack, scenario)
