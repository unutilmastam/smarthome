"""Applies Hub state reports (POST /hub/report) to device_state."""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contracts import Contracts
from app.db.types import utcnow
from app.models import Device, DeviceState, Hub

MAX_FUTURE_SKEW = timedelta(seconds=60)


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def apply_report(db: Session, hub: Hub, contracts: Contracts, report: dict) -> dict:
    now = utcnow()
    devices = {d.key: d for d in db.scalars(select(Device).where(Device.home_id == hub.home_id))}
    results = []
    for item in report["devices"]:
        key = item["device_key"]
        d = devices.get(key)
        if d is None:
            results.append({"device_key": key, "result": "unknown_device"})
            continue
        errors = []
        if "availability" in item:
            if d.availability != item["availability"]:
                d.availability = item["availability"]
                d.availability_ts = now
            elif d.availability_ts is None:
                d.availability_ts = now
        caps = {c.capability for c in d.capabilities}
        unsupported = set(d.unsupported or [])
        current = {(s.capability, s.attribute): s for s in d.states}
        for cap, attrs in (item.get("states") or {}).items():
            if cap not in caps:
                errors.append(f"{cap}: device has no such capability")
                continue
            spec_attrs = contracts.attributes(cap)
            for attr, val in attrs.items():
                path = f"{cap}.{attr}"
                if attr not in spec_attrs:
                    errors.append(f"{path}: unknown attribute")
                    continue
                if path in unsupported and val["quality"] != "not_supported":
                    errors.append(f"{path}: declared not_supported for this device")
                    continue
                ts = _parse_ts(val["ts"])
                if ts is not None and ts > now + MAX_FUTURE_SKEW:
                    errors.append(f"{path}: ts is in the future")
                    continue
                if val["quality"] in ("good", "stale"):
                    verr = list(contracts.attribute_validator(cap, attr).iter_errors(val["value"]))
                    if verr:
                        errors.append(f"{path}: {verr[0].message}")
                        continue
                st = current.get((cap, attr))
                if st is not None and st.ts is not None and ts is not None and ts < st.ts:
                    continue  # older than what we have; keep the newer value
                if st is None:
                    st = DeviceState(device_id=d.id, capability=cap, attribute=attr)
                    d.states.append(st)
                    current[(cap, attr)] = st
                st.value_json = val["value"]
                st.source = val["source"]
                st.quality = val["quality"]
                st.ts = ts
        results.append({"device_key": key, "result": "error" if errors else "ok",
                        **({"errors": errors} if errors else {})})
    db.commit()
    return {"devices": results}
