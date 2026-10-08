"""DB-backed rate limiter (works across Passenger processes).

Counts are stored per fixed window, but the decision uses the sliding-window estimate
    previous_window_count * (share of the previous window still inside the last window_s)
    + current_window_count
so a burst across a window boundary cannot get 2x the limit (Faza 14 finding: 20 failed
logins at 12:04:59 + 20 more at 12:05:00 were all accepted).
"""

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


def _estimate(db: Session, key: str, window_s: int, now: datetime) -> float:
    start = _window_start(now, window_s)
    prev_start = start - timedelta(seconds=window_s)
    rows = dict(db.execute(select(RateLimitHit.window_start, RateLimitHit.count).where(
        RateLimitHit.key == key, RateLimitHit.window_start.in_([start, prev_start]))).all())
    current = rows.get(start, 0)
    prev = rows.get(prev_start, 0)
    overlap = 1.0 - (now - start).total_seconds() / window_s
    return current + prev * max(0.0, overlap)


def _retry_after(window_s: int, now: datetime) -> int:
    start = _window_start(now, window_s)
    return max(1, int((start + timedelta(seconds=window_s) - now).total_seconds()))


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
    if _estimate(db, key, window_s, now) > limit:
        raise rate_limited(_retry_after(window_s, now))


def purge_old(db: Session, older_than: timedelta = timedelta(days=1)) -> int:
    res = db.execute(delete(RateLimitHit).where(RateLimitHit.window_start < utcnow() - older_than))
    db.commit()
    return res.rowcount or 0


def ensure_below(db: Session, key: str, limit: int, window_s: int,
                 now: Optional[datetime] = None) -> None:
    """Raise RATE_LIMITED if the current window already reached the limit (no increment)."""
    now = now or utcnow()
    if _estimate(db, key, window_s, now) >= limit:
        raise rate_limited(_retry_after(window_s, now))
