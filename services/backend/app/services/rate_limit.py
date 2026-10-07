"""DB-backed fixed-window rate limiter (works across Passenger processes)."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import rate_limited
from app.db.types import utcnow
from app.models import RateLimitHit


def _window_start(now: datetime, window_s: int) -> datetime:
    epoch = int(now.timestamp())
    return datetime.fromtimestamp(epoch - epoch % window_s, tz=timezone.utc)


def hit(db: Session, key: str, limit: int, window_s: int,
        now: Optional[datetime] = None) -> None:
    """Count one hit and raise RATE_LIMITED if the limit is exceeded.

    Commits immediately so the counter survives a failing request.
    """
    now = now or utcnow()
    start = _window_start(now, window_s)
    for _ in range(2):
        res = db.execute(
            update(RateLimitHit)
            .where(RateLimitHit.key == key, RateLimitHit.window_start == start)
            .values(count=RateLimitHit.count + 1)
        )
        if res.rowcount:
            break
        try:
            with db.begin_nested():
                db.add(RateLimitHit(key=key, window_start=start, count=1))
            break
        except IntegrityError:
            continue  # another process inserted it; retry the update
    db.commit()
    count = db.scalar(
        select(RateLimitHit.count).where(
            RateLimitHit.key == key, RateLimitHit.window_start == start
        )
    )
    if count is not None and count > limit:
        retry = int((start + timedelta(seconds=window_s) - now).total_seconds())
        raise rate_limited(retry)


def purge_old(db: Session, older_than: timedelta = timedelta(days=1)) -> int:
    res = db.execute(delete(RateLimitHit).where(RateLimitHit.window_start < utcnow() - older_than))
    db.commit()
    return res.rowcount or 0
