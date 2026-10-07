import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Device, EnergyDaily, Home, Telemetry1h, Telemetry1m
from app.services import telemetry as tm
from conftest import Api

METER = {"key": "main_meter", "name": "Hisoblagich", "adapter": "esphome", "protocol": "mqtt",
         "capabilities": {"power_meter": {"report_interval_s": 10}},
         "unsupported": ["power_meter.frequency"]}


@pytest.fixture
def meter(owner, owner_home):
    return owner.post(f"/api/v1/homes/{owner_home}/devices", json=METER).json()["data"]


@pytest.fixture
def hub(client, owner, owner_home):
    d = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "h"}).json()["data"]
    return Api(client, d["hub_token"])


def item(metric="power_meter.power", ts=None, **kw):
    ts = ts or (datetime.now(timezone.utc) - timedelta(minutes=3)).replace(second=0, microsecond=0)
    base = {"device_key": "main_meter", "metric": metric,
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "avg": 400.0, "min": 380.0, "max": 420.0,
            "last": 410.0, "count": 6}
    base.update(kw)
    return base


def post(hub, *items):
    return hub.post("/api/v1/hub/telemetry:batch", json={"schema": 1, "items": list(items)})


def test_ingest_and_idempotent_resend(hub, meter, dbs):
    r = post(hub, item())
    assert r.status_code == 200 and r.json()["data"]["accepted"] == 1
    post(hub, item(avg=401.0))
    rows = dbs.scalars(select(Telemetry1m)).all()
    assert len(rows) == 1 and rows[0].avg == 401.0


def test_ingest_rejections(hub, meter, dbs):
    future = datetime.now(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=10)
    r = post(hub,
             item(device_key="ghost"),
             item(metric="climate.current_temp"),
             item(metric="power_meter.frequency", avg=50, min=50, max=50, last=50),
             item(ts=future),
             item(avg=500.0),                     # avg > max
             item(metric="power_meter.voltage", min=-9999.0, avg=0, max=230.0, last=230.0))
    errs = [e["error"] for e in r.json()["data"]["errors"]]
    assert errs == ["unknown_device", "unknown_metric", "not_supported", "ts_in_future",
                    "inconsistent", "out_of_range"]
    assert dbs.scalars(select(Telemetry1m)).all() == []


def test_schema_violation_is_422(hub, meter):
    bad = item()
    bad["ts"] = bad["ts"].replace(":00Z", ":17Z")
    assert post(hub, bad).status_code == 422


def test_counter_delta_handles_reset():
    assert tm.counter_delta([10.0, 10.5, 11.0], 9.5) == pytest.approx(1.5)
    # meter reset to 0 after 11.0 -> 0.2 -> 0.7
    assert tm.counter_delta([11.0, 0.2, 0.7], 10.0) == pytest.approx(1.0 + 0.2 + 0.5)
    assert tm.counter_delta([5.0], None) == 0.0


def _seed_energy(dbs, device_id, start_utc, values, step=timedelta(minutes=1)):
    for i, v in enumerate(values):
        dbs.merge(Telemetry1m(device_id=uuid.UUID(device_id), metric="power_meter.energy",
                              ts=start_utc + i * step, avg=v, min=v, max=v, last=v, count=1))
    dbs.commit()


def test_energy_daily_uses_local_day_and_tariff(meter, owner, owner_home, dbs):
    # Tashkent is UTC+5: local day 2026-10-06 = 2026-10-05T19:00Z .. 2026-10-06T19:00Z
    _seed_energy(dbs, meter["id"], datetime(2026, 10, 5, 18, 0, tzinfo=timezone.utc), [100.0])
    _seed_energy(dbs, meter["id"], datetime(2026, 10, 5, 19, 0, tzinfo=timezone.utc),
                 [100.5, 102.0, 104.0], step=timedelta(hours=6))
    _seed_energy(dbs, meter["id"], datetime(2026, 10, 6, 19, 30, tzinfo=timezone.utc), [105.0])
    n = tm.update_energy_daily(dbs, days_back=1, today=date(2026, 10, 7))
    assert n == 2
    d6 = dbs.get(EnergyDaily, (uuid.UUID(meter["id"]), date(2026, 10, 6)))
    assert d6.kwh == pytest.approx(4.0)          # 100 -> 104 within the local day
    assert d6.cost is None and d6.currency is None  # no tariff yet: unknown, not 0
    owner.patch(f"/api/v1/homes/{owner_home}", json={"tariff_per_kwh": 1000})
    tm.update_energy_daily(dbs, days_back=1, today=date(2026, 10, 7))
    dbs.refresh(d6)
    assert (d6.cost, d6.currency) == (4000.0, "UZS")


def test_no_data_day_is_absent_not_zero(meter, dbs):
    assert tm.update_energy_daily(dbs, days_back=3, today=date(2026, 10, 7)) == 0
    assert dbs.scalars(select(EnergyDaily)).all() == []


def test_rollup_hours(meter, dbs):
    t0 = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)
    for i, (avg, n) in enumerate([(100.0, 1), (200.0, 3)]):
        dbs.add(Telemetry1m(device_id=uuid.UUID(meter["id"]), metric="power_meter.power",
                            ts=t0 + timedelta(minutes=i), avg=avg, min=avg - 1, max=avg + 1,
                            last=avg, count=n))
    dbs.commit()
    assert tm.rollup_hours(dbs, t0, until=t0 + timedelta(hours=1)) == 1
    h = dbs.scalars(select(Telemetry1h)).one()
    assert h.avg == pytest.approx(175.0) and (h.min, h.max, h.last, h.count) == (99, 201, 200, 4)


def test_purge(meter, dbs):
    old = datetime.now(timezone.utc) - timedelta(days=31)
    dbs.add(Telemetry1m(device_id=uuid.UUID(meter["id"]), metric="power_meter.power", ts=old,
                        avg=1, min=1, max=1, last=1, count=1))
    dbs.commit()
    assert tm.purge(dbs)["telemetry_1m"] == 1


def test_summary_and_series_api(owner, owner_home, meter, hub, dbs, outsider):
    post(hub, item())
    owner.patch(f"/api/v1/homes/{owner_home}", json={"tariff_per_kwh": 900, "currency": "UZS"})
    today = datetime.now(timezone(timedelta(hours=5))).date()
    dbs.add(EnergyDaily(device_id=uuid.UUID(meter["id"]), day=today, kwh=3.5, cost=3150.0,
                        currency="UZS"))
    dbs.commit()
    s = owner.get(f"/api/v1/homes/{owner_home}/energy/summary").json()["data"]
    assert s["total_kwh"] == 3.5 and s["total_cost"] == 3150.0 and s["devices"][0]["key"] == "main_meter"
    m = owner.get(f"/api/v1/homes/{owner_home}/energy/summary", params={"period": "month"}).json()["data"]
    assert m["from"].endswith("-01")
    ser = owner.get(f"/api/v1/devices/{meter['id']}/telemetry",
                    params={"metric": "power_meter.power"}).json()
    assert ser["meta"]["count"] == 1 and ser["data"][0]["avg"] == 400.0
    assert owner.get(f"/api/v1/devices/{meter['id']}/telemetry",
                     params={"metric": "power_meter.power", "hours": 24 * 60}).status_code == 422
    assert outsider.get(f"/api/v1/devices/{meter['id']}/telemetry",
                        params={"metric": "power_meter.power"}).status_code == 404
    assert outsider.get(f"/api/v1/homes/{owner_home}/energy/summary").status_code == 404


def test_empty_summary_is_null_not_zero(owner, owner_home):
    s = owner.get(f"/api/v1/homes/{owner_home}/energy/summary").json()["data"]
    assert s["total_kwh"] is None and s["total_cost"] is None and s["devices"] == []


def test_tariff_validation(owner, owner_home):
    assert owner.patch(f"/api/v1/homes/{owner_home}", json={"tariff_per_kwh": -1}).status_code == 422
    assert owner.patch(f"/api/v1/homes/{owner_home}", json={"currency": "som"}).status_code == 422
    d = owner.patch(f"/api/v1/homes/{owner_home}", json={"tariff_per_kwh": 1000.5}).json()["data"]
    assert d["tariff_per_kwh"] == 1000.5 and d["currency"] == "UZS"
