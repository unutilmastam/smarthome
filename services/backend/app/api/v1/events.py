"""Event feed (ADR 0012): what happened at home, newest first."""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_db, get_principal, membership_or_404
from app.core.responses import ok
from app.models import Device, Event
from app.services.events import event_out

router = APIRouter(tags=["events"])


@router.get("/homes/{home_id}/events")
def list_events(home_id: uuid.UUID,
                limit: int = Query(50, ge=1, le=200),
                before: Optional[datetime] = Query(None),
                device_id: Optional[uuid.UUID] = Query(None),
                severity: Optional[str] = Query(None, pattern="^(info|warning|critical)$"),
                capability: Optional[str] = Query(None, pattern="^[a-z][a-z0-9_]*$"),
                p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    membership_or_404(db, home_id, p.user)
    q = select(Event).where(Event.home_id == home_id)
    if before is not None:
        q = q.where(Event.ts < before)
    if device_id is not None:
        q = q.where(Event.device_id == device_id)
    if severity:
        q = q.where(Event.severity == severity)
    if capability:
        q = q.where(Event.type.like(f"{capability}.%"))
    rows = db.scalars(q.order_by(Event.ts.desc(), Event.id).limit(limit)).all()
    ids = {e.device_id for e in rows if e.device_id}
    names = dict(db.execute(select(Device.id, Device.name).where(Device.id.in_(ids))).all()) if ids else {}
    return ok([event_out(e, names) for e in rows], {"count": len(rows)})
