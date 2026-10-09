"""GET /realtime/credentials — read-only broker access for the PWA (ADR 0008)."""

from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, client_ip, get_db, get_principal, get_realtime
from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.core.responses import ok
from app.core.security import new_token
from app.db.types import utcnow
from app.models import HomeMember
from app.services import audit, rate_limit
from app.services.device_view import iso
from app.services.realtime import RealtimeError, topic_home

router = APIRouter(prefix="/realtime", tags=["realtime"])

POLL_INTERVAL_S = 3


@router.get("/credentials")
def credentials(request: Request, p: Principal = Depends(get_principal),
                db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
                realtime=Depends(get_realtime)):
    if not realtime.enabled:
        return ok({"enabled": False, "transport": "polling", "poll_interval_s": POLL_INTERVAL_S})
    rate_limit.hit(db, f"rt:user:{p.user.id}", 10, 60)
    homes = db.scalars(select(HomeMember.home_id).where(HomeMember.user_id == p.user.id)).all()
    topics = sorted(topic_home(h) for h in homes)
    username = f"app-{p.user.id}"
    password = new_token(24)
    try:
        realtime.set_read_only_user(username, password, topics)
    except RealtimeError as exc:
        # The app keeps working with polling.
        raise ApiError(503, "REALTIME_UNAVAILABLE", f"Realtime broker unavailable: {exc}",
                       {"transport": "polling", "poll_interval_s": POLL_INTERVAL_S})
    audit.record(db, "realtime.credentials_issued", actor_id=p.user.id, ip=client_ip(request),
                 details={"topics": len(topics)})
    db.commit()
    return ok({
        "enabled": True,
        "transport": "mqtt-wss",
        "url": settings.realtime_wss_url,
        "client_id": username,
        "username": username,
        "password": password,
        "topics": topics,
        "read_only": True,
        "rotate_after": iso(utcnow() + timedelta(seconds=settings.realtime_credentials_ttl_s)),
        "poll_interval_s": POLL_INTERVAL_S,
    })
