"""Rate limiter: a burst across a window boundary must not get twice the limit (Faza 14)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import ApiError
from app.services import rate_limit

T0 = datetime(2026, 10, 8, 12, 4, 59, tzinfo=timezone.utc)   # 1 s before a 5-min boundary


def burst(dbs, n, now, key="login:ip:1.2.3.4"):
    ok = 0
    for _ in range(n):
        try:
            rate_limit.hit(dbs, key, 20, 300, now=now)
            ok += 1
        except ApiError as e:
            assert e.code == "RATE_LIMITED"
    return ok


def test_boundary_burst_does_not_double_the_limit(dbs):
    assert burst(dbs, 20, T0) == 20
    # 2 s later, in the next fixed window: the old fixed-window limiter accepted 20 more.
    assert burst(dbs, 20, T0 + timedelta(seconds=2)) == 0


def test_limit_frees_up_as_the_previous_window_slides_out(dbs):
    assert burst(dbs, 20, T0) == 20
    # Halfway through the next window, half of the previous window's weight is gone.
    half = T0 + timedelta(seconds=1 + 150)
    assert 9 <= burst(dbs, 20, half) <= 10
    # A full window later the old hits no longer count at all.
    assert burst(dbs, 20, T0 + timedelta(seconds=1 + 300 + 300)) == 20


def test_ensure_below_uses_the_same_estimate(dbs):
    for _ in range(5):
        rate_limit.hit(dbs, "pin:u", 5, 900, now=T0)
    with pytest.raises(ApiError):
        rate_limit.ensure_below(dbs, "pin:u", 5, 900, now=T0 + timedelta(seconds=2))
    rate_limit.ensure_below(dbs, "other", 5, 900, now=T0)        # untouched key passes


def test_retry_after_is_positive(dbs):
    burst(dbs, 20, T0)
    with pytest.raises(ApiError) as e:
        rate_limit.hit(dbs, "login:ip:1.2.3.4", 20, 300, now=T0 + timedelta(seconds=2))
    assert int(e.value.headers["Retry-After"]) >= 1
