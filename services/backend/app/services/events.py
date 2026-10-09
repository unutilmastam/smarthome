"""Events from the hub (ADR 0012). Idempotent by event id; nothing is invented:
the type must be listed in the contract and the severity comes from the contract."""

import uuid
from datetime import timedelta
from typing import Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.contracts import Contracts
from app.db.types import utcnow
from app.models import Device, Event, Hub
from app.services import notifications
from app.services.device_view import iso
from app.services.hub_reports import _parse_ts as parse_ts

RETENTION = timedelta(days=180)


def ingest(db: Session, hub: Hub, contracts: Contracts, body: dict,
           created: Optional[List] = None) -> dict:
    """`created` (if given) receives the notifications made for new events (ADR 0014)."""
    keys = {e["device_key"] for e in body["events"]}
    devices: Dict[str, Device] = {
        d.key: d for d in db.scalars(select(Device).where(
            Device.home_id == hub.home_id, Device.key.in_(keys)))}
    ids = [uuid.UUID(e["id"]) for e in body["events"]]
    seen = set(db.scalars(select(Event.id).where(Event.id.in_(ids))))
    accepted, duplicates, rejected = 0, 0, []
    new: List[Event] = []
    for e in body["events"]:
        eid = uuid.UUID(e["id"])
        if eid in seen:
            duplicates += 1
            continue
        device = devices.get(e["device_key"])
        severity = contracts.event_severity(e["type"])
        cap = e["type"].split(".", 1)[0]
        if device is None:
            rejected.append({"id": e["id"], "reason": "unknown device_key"})
            continue
        if severity is None or cap not in {c.capability for c in device.capabilities}:
            rejected.append({"id": e["id"], "reason": f"event type {e['type']} not allowed for this device"})
            continue
        row = Event(id=eid, home_id=hub.home_id, device_id=device.id, device_key=device.key,
                    type=e["type"], severity=severity, ts=parse_ts(e["ts"]),
                    data=e.get("data") or {})
        db.add(row)
        new.append(row)
        seen.add(eid)
        accepted += 1
    db.flush()
    made = notifications.from_events(db, hub.home_id, new)
    db.commit()
    if created is not None:
        created.extend(made)
    return {"accepted": accepted, "duplicates": duplicates, "rejected": rejected}


def event_out(e: Event, names: Dict[uuid.UUID, str]) -> dict:
    return {"id": str(e.id), "ts": iso(e.ts), "type": e.type, "severity": e.severity,
            "device_id": str(e.device_id) if e.device_id else None, "device_key": e.device_key,
            "device_name": names.get(e.device_id) if e.device_id else None, "data": e.data or {}}


def purge(db: Session) -> int:
    n = db.execute(delete(Event).where(Event.ts < utcnow() - RETENTION)).rowcount or 0
    db.commit()
    return n
