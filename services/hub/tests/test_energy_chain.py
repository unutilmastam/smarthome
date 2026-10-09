"""Phase 9 [SIM]: meter telemetry -> 1-minute aggregates in the cloud; contactor feedback."""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from gateway.telemetry import Aggregator
from gateway.store import Store
from simulator.devices import ContactorSim
from conftest import SIM_PASSWORD
from test_integration import PIN, Stack, run


def test_aggregator_closes_finished_minutes(tmp_path):
    agg = Aggregator(Store(str(tmp_path / "x.sqlite3")))
    t = datetime(2026, 10, 7, 12, 0, 10, tzinfo=timezone.utc)
    for i, v in enumerate([10.0, 20.0, 30.0]):
        agg.add("m", "power_meter.power", v, t + timedelta(seconds=i * 10))
    agg.add("m", "power_meter.power", 99.0, t + timedelta(minutes=1))
    assert agg.close_minutes(t + timedelta(seconds=45)) == []          # 12:00:55, still open
    items = agg.close_minutes(t + timedelta(minutes=1, seconds=5))
    assert items == [{"device_key": "m", "metric": "power_meter.power",
                      "ts": "2026-10-07T12:00:00Z", "avg": 20.0, "min": 10.0, "max": 30.0,
                      "last": 30.0, "count": 3}]
    assert len(agg.buckets) == 1  # the 12:01 bucket is still open


def test_meter_telemetry_reaches_backend(broker, tmp_path):
    st = Stack(broker, tmp_path)

    async def scenario(st):
        from app.models import Telemetry1m
        # Close every minute right away (instead of waiting for a real minute boundary).
        await st.wait(lambda: len(st.gateway.aggregator.buckets) > 0, "readings aggregated")
        await asyncio.sleep(1.0)
        st.gateway.queue_telemetry(now=datetime.now(timezone.utc) + timedelta(minutes=2))
        await st.gateway.flush_once()

        def rows():
            with st.database.sessionmaker() as s:
                return s.scalars(select(Telemetry1m)).all()
        got = await st.wait(rows, "telemetry_1m rows in backend")
        metrics = {r.metric for r in got}
        assert {"power_meter.voltage", "power_meter.power", "power_meter.energy"} <= metrics
        # main_meter declares frequency unsupported -> the hub never sends it.
        assert "power_meter.frequency" not in metrics
        v = next(r for r in got if r.metric == "power_meter.voltage")
        assert 200 < v.avg < 260 and v.min <= v.avg <= v.max and v.count >= 1
        # Raw readings stay on the hub.
        raw = st.gateway.store.db.execute("SELECT COUNT(*) FROM raw_telemetry").fetchone()[0]
        assert raw > 0
    run(st, scenario)


def test_contactor_confirmed_only_by_aux_contact(broker, tmp_path):
    from test_integration import DEVICES
    DEVICES["line_boiler"] = {"capabilities": {"contactor": {"confirm_timeout_s": 2}}}
    try:
        st = Stack(broker, tmp_path)
        st.sims["line_boiler"] = ContactorSim("line_boiler", host=broker["host"],
                                              port=broker["port"], password=SIM_PASSWORD)

        async def scenario(st):
            await st.wait(lambda: st.device("line_boiler")["capabilities"]["contactor"][
                "attributes"]["aux_contact_closed"]["quality"] == "good", "initial state")
            r = await st.send("line_boiler", "contactor", "open", confirm_pin=PIN)
            assert r.status_code == 201, r.text
            c = await st.wait_status(r.json()["data"]["id"], {"confirmed", "failed"})
            assert c["status"] == "confirmed"
            # Contacts weld: coil drops, line stays powered -> NOT confirmed.
            st.sims["line_boiler"].set_fault("welded")
            r = await st.send("line_boiler", "contactor", "close", confirm_pin=PIN)
            await st.wait_status(r.json()["data"]["id"], {"confirmed", "failed"})
            r = await st.send("line_boiler", "contactor", "open", confirm_pin=PIN)
            c = await st.wait_status(r.json()["data"]["id"], {"confirmed", "failed"}, timeout=8)
            assert (c["status"], c["reason"]) == ("failed", "no_feedback")
            attrs = st.device("line_boiler")["capabilities"]["contactor"]["attributes"]
            assert attrs["commanded_closed"]["value"] is False
            assert attrs["aux_contact_closed"]["value"] is True   # the truth
        run(st, scenario)
    finally:
        DEVICES.pop("line_boiler", None)
