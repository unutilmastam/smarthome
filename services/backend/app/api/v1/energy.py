import calendar
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db, get_principal, membership_or_404
from app.core.errors import ApiError, not_found, validation_error
from app.core.responses import ok
from app.models import Device, Home
from app.services import telemetry as tm
from app.services.device_view import iso

router = APIRouter(tags=["energy"])


@router.get("/homes/{home_id}/energy/summary")
def energy_summary(home_id: uuid.UUID, period: str = Query("day", pattern="^(day|month)$"),
                   on: Optional[date] = Query(None, alias="date"),
                   p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    membership_or_404(db, home_id, p.user)
    home = db.get(Home, home_id)
    day = on or datetime.now(ZoneInfo(home.timezone)).date()
    if period == "day":
        first = last = day
    else:
        first = day.replace(day=1)
        last = day.replace(day=calendar.monthrange(day.year, day.month)[1])
    rows = tm.energy_range(db, home_id, first, last)
    items = []
    for dev_id, key, name, kwh, cost, n_cost, n_days, currency in rows:
        items.append({
            "device_id": str(dev_id), "key": key, "name": name,
            "kwh": round(kwh, 3), "days_with_data": n_days,
            # Cost only when every counted day had a tariff; otherwise unknown.
            "cost": round(cost, 2) if n_cost == n_days and cost is not None else None,
            "currency": currency,
        })
    total_kwh = round(sum(i["kwh"] for i in items), 3) if items else None
    costs = [i["cost"] for i in items]
    total_cost = round(sum(costs), 2) if items and all(c is not None for c in costs) else None
    return ok({
        "period": period, "from": first.isoformat(), "to": last.isoformat(),
        "timezone": home.timezone, "tariff_per_kwh": home.tariff_per_kwh,
        "currency": home.currency, "total_kwh": total_kwh, "total_cost": total_cost,
        "devices": items,
    })


@router.get("/devices/{device_id}/telemetry")
def device_telemetry(device_id: uuid.UUID, metric: str = Query(..., max_length=64),
                     resolution: str = Query("1m", pattern="^(1m|1h)$"),
                     hours: int = Query(24, ge=1, le=24 * 400),
                     p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    d = db.get(Device, device_id)
    if d is None:
        raise not_found("Device")
    try:
        membership_or_404(db, d.home_id, p.user)
    except ApiError:
        raise not_found("Device")
    if resolution == "1m" and hours > 24 * 30:
        raise validation_error("1m data is kept for 30 days; use resolution=1h")
    end = datetime.now(timezone.utc)
    rows = tm.series(db, device_id, metric, resolution, end - timedelta(hours=hours), end)
    return ok([{"ts": iso(r.ts), "avg": r.avg, "min": r.min, "max": r.max, "last": r.last}
               for r in rows], {"metric": metric, "resolution": resolution, "count": len(rows)})
