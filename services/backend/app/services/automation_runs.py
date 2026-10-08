"""Automation run history from the hub (ADR 0013). Idempotent by run id; kept 90 days."""

import uuid
from datetime import timedelta
from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.types import utcnow
from app.models import Automation, AutomationRun, Hub
from app.services import notifications
from app.services.hub_reports import _parse_ts as parse_ts

RETENTION = timedelta(days=90)


def ingest(db: Session, hub: Hub, body: dict, created: Optional[List] = None) -> dict:
    """`notify` actions of new runs become notifications (ADR 0014), collected in `created`."""
    made: list = []
    ids = [uuid.UUID(r["id"]) for r in body["runs"]]
    seen = set(db.scalars(select(AutomationRun.id).where(AutomationRun.id.in_(ids))))
    autos = {a.id for a in db.scalars(select(Automation).where(Automation.home_id == hub.home_id))}
    accepted, duplicates, rejected = 0, 0, []
    for r in body["runs"]:
        rid, aid = uuid.UUID(r["id"]), uuid.UUID(r["automation_id"])
        if rid in seen:
            duplicates += 1
            continue
        if aid not in autos:  # deleted meanwhile, or another home's
            rejected.append({"id": r["id"], "reason": "unknown automation"})
            continue
        db.add(AutomationRun(id=rid, home_id=hub.home_id, automation_id=aid,
                             version=r["version"], ts=parse_ts(r["ts"]), trigger=r["trigger"],
                             result=r["result"], reason=r.get("reason"),
                             actions=r.get("actions") or []))
        db.flush()
        made += notifications.from_run(db, hub.home_id, rid, aid, parse_ts(r["ts"]),
                                       r.get("actions") or [])
        seen.add(rid)
        accepted += 1
    db.commit()
    if created is not None:
        created.extend(made)
    return {"accepted": accepted, "duplicates": duplicates, "rejected": rejected}


def purge(db: Session) -> int:
    n = db.execute(delete(AutomationRun).where(AutomationRun.ts < utcnow() - RETENTION)).rowcount or 0
    db.commit()
    return n
