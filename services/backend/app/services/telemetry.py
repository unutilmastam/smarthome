"""Telemetry ingest, roll-ups and daily energy (ARCHITECTURE 7, Faza 9)."""

import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from app.core.contracts import Contracts
from app.db.types import utcnow
from app.models import Device, EnergyDaily, Home, Hub, Telemetry1h, Telemetry1m

ENERGY_METRIC = "power_meter.energy"
MAX_FUTURE = timedelta(minutes=2)
RETAIN_1M = timedelta(days=30)
RETAIN_1H = timedelta(days=730)


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def _numeric(spec: dict) -> bool:
    return spec.get("type") in ("number", "integer")


def _upsert_1m(db: Session, values: dict) -> None:
    """INSERT ... ON CONFLICT DO UPDATE: a bucket sent twice (retry, or two batches racing)
    simply overwrites itself instead of failing with a unique-key error."""
    dialect = db.get_bind().dialect.name
    insert = postgresql.insert if dialect == "postgresql" else sqlite.insert
    stmt = insert(Telemetry1m).values(**values)
    db.execute(stmt.on_conflict_do_update(
        index_elements=["device_id", "metric", "ts"],
        set_={k: stmt.excluded[k] for k in ("avg", "min", "max", "last", "count")}))


def ingest(db: Session, hub: Hub, contracts: Contracts, batch: dict) -> dict:
    devices = {d.key: d for d in db.scalars(select(Device).where(Device.home_id == hub.home_id))}
    now = utcnow()
    accepted, errors = 0, []
    for i, it in enumerate(batch["items"]):
        d = devices.get(it["device_key"])
        if d is None:
            errors.append({"index": i, "error": "unknown_device"})
            continue
        cap, attr = it["metric"].split(".", 1)
        caps = {c.capability for c in d.capabilities}
        if cap not in caps or attr not in contracts.attributes(cap):
            errors.append({"index": i, "error": "unknown_metric"})
            continue
        if not _numeric(contracts.attributes(cap)[attr]):
            errors.append({"index": i, "error": "not_numeric"})
            continue
        if it["metric"] in (d.unsupported or []):
            errors.append({"index": i, "error": "not_supported"})
            continue
        ts = _parse(it["ts"])
        if ts > now + MAX_FUTURE:
            errors.append({"index": i, "error": "ts_in_future"})
            continue
        if not it["min"] <= it["avg"] <= it["max"] or not it["min"] <= it["last"] <= it["max"]:
            errors.append({"index": i, "error": "inconsistent"})
            continue
        validator = contracts.attribute_validator(cap, attr)
        if any(True for v in (it["min"], it["max"]) for _ in validator.iter_errors(v)):
            errors.append({"index": i, "error": "out_of_range"})
            continue
        _upsert_1m(db, {"device_id": d.id, "metric": it["metric"], "ts": ts, "avg": it["avg"],
                        "min": it["min"], "max": it["max"], "last": it["last"],
                        "count": it["count"]})
        accepted += 1
    db.commit()
    return {"accepted": accepted, "rejected": len(errors), "errors": errors[:50]}


# ---- roll-up --------------------------------------------------------------------------

def rollup_hours(db: Session, since: datetime, until: Optional[datetime] = None) -> int:
    """(Re)build 1h buckets from 1m for complete hours in [since, until)."""
    until = (until or utcnow()).replace(minute=0, second=0, microsecond=0)
    since = since.replace(minute=0, second=0, microsecond=0)
    rows = db.scalars(select(Telemetry1m).where(Telemetry1m.ts >= since, Telemetry1m.ts < until)
                      .order_by(Telemetry1m.ts)).all()
    groups: Dict[Tuple[uuid.UUID, str, datetime], List[Telemetry1m]] = defaultdict(list)
    for r in rows:
        groups[(r.device_id, r.metric, r.ts.replace(minute=0, second=0, microsecond=0))].append(r)
    for (dev, metric, hour), items in groups.items():
        n = sum(x.count for x in items)
        h = db.get(Telemetry1h, (dev, metric, hour)) or Telemetry1h(device_id=dev, metric=metric,
                                                                    ts=hour)
        h.avg = sum(x.avg * x.count for x in items) / n
        h.min = min(x.min for x in items)
        h.max = max(x.max for x in items)
        h.last = items[-1].last
        h.count = n
        db.add(h)
    db.commit()
    return len(groups)


def counter_delta(values: Iterable[float], baseline: Optional[float]) -> float:
    """kWh consumed from a monotonically increasing counter that may reset to ~0."""
    total, prev = 0.0, baseline
    for v in values:
        if prev is not None:
            total += v - prev if v >= prev else v  # reset: count from zero
        prev = v
    return total


def compute_energy_day(db: Session, device: Device, home: Home, day: date) -> Optional[float]:
    tz = ZoneInfo(home.timezone)
    start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(timezone.utc)
    end = start + timedelta(days=1)
    vals = db.scalars(select(Telemetry1m.last).where(
        Telemetry1m.device_id == device.id, Telemetry1m.metric == ENERGY_METRIC,
        Telemetry1m.ts >= start, Telemetry1m.ts < end).order_by(Telemetry1m.ts)).all()
    if not vals:
        return None  # no data: unknown, not zero
    baseline = db.scalar(select(Telemetry1m.last).where(
        Telemetry1m.device_id == device.id, Telemetry1m.metric == ENERGY_METRIC,
        Telemetry1m.ts < start, Telemetry1m.ts >= start - timedelta(hours=6))
        .order_by(Telemetry1m.ts.desc()).limit(1))
    return round(counter_delta(vals, baseline), 4)


def update_energy_daily(db: Session, days_back: int = 2, today: Optional[date] = None) -> int:
    n = 0
    meters = db.execute(select(Device, Home).join(Home, Home.id == Device.home_id).where(
        Device.id.in_(select(Telemetry1m.device_id).where(Telemetry1m.metric == ENERGY_METRIC)
                      .distinct()))).all()
    for device, home in meters:
        local_today = today or datetime.now(ZoneInfo(home.timezone)).date()
        for k in range(days_back + 1):
            day = local_today - timedelta(days=k)
            kwh = compute_energy_day(db, device, home, day)
            if kwh is None:
                continue
            row = db.get(EnergyDaily, (device.id, day)) or EnergyDaily(device_id=device.id, day=day)
            row.kwh = kwh
            row.cost = round(kwh * home.tariff_per_kwh, 2) if home.tariff_per_kwh is not None \
                else None
            row.currency = home.currency if home.tariff_per_kwh is not None else None
            db.add(row)
            n += 1
    db.commit()
    return n


def purge(db: Session, now: Optional[datetime] = None) -> dict:
    now = now or utcnow()
    a = db.execute(delete(Telemetry1m).where(Telemetry1m.ts < now - RETAIN_1M)).rowcount or 0
    b = db.execute(delete(Telemetry1h).where(Telemetry1h.ts < now - RETAIN_1H)).rowcount or 0
    db.commit()
    return {"telemetry_1m": a, "telemetry_1h": b}


# ---- queries ----------------------------------------------------------------------------

def series(db: Session, device_id: uuid.UUID, metric: str, resolution: str, start: datetime,
           end: datetime, limit: int = 2000) -> list:
    model = Telemetry1m if resolution == "1m" else Telemetry1h
    rows = db.scalars(select(model).where(and_(model.device_id == device_id,
                                               model.metric == metric, model.ts >= start,
                                               model.ts < end)).order_by(model.ts).limit(limit))
    return list(rows)


def energy_range(db: Session, home_id: uuid.UUID, first: date, last: date) -> list:
    return db.execute(
        select(Device.id, Device.key, Device.name, func.sum(EnergyDaily.kwh),
               func.sum(EnergyDaily.cost), func.count(EnergyDaily.cost),
               func.count(EnergyDaily.day), func.max(EnergyDaily.currency))
        .join(EnergyDaily, EnergyDaily.device_id == Device.id)
        .where(Device.home_id == home_id, EnergyDaily.day >= first, EnergyDaily.day <= last)
        .group_by(Device.id, Device.key, Device.name).order_by(Device.name)).all()
