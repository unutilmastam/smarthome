"""Daily: delete data that is no longer needed (ARCHITECTURE 7).

- rate limit counters older than 1 day
- auth sessions revoked or expired more than 30 days ago
- events older than 180 days (ADR 0012)
Audit log and command history are kept (append-only by design).
"""

import logging
from datetime import timedelta

from sqlalchemy import delete, or_

from app.db.types import utcnow
from app.jobs._runner import job
from app.models import AuthSession
from app.services import events, telemetry
from app.services.rate_limit import purge_old


def run(db) -> dict:
    cutoff = utcnow() - timedelta(days=30)
    sessions = db.execute(delete(AuthSession).where(or_(
        AuthSession.revoked_at < cutoff, AuthSession.expires_at < cutoff))).rowcount or 0
    db.commit()
    return {"rate_limits": purge_old(db), "auth_sessions": sessions, "events": events.purge(db),
            **telemetry.purge(db)}


if __name__ == "__main__":
    with job("retention") as (settings, contracts, db):
        logging.info("deleted %s", run(db))
