"""Every minute: queued -> expired, sent -> timeout, acked -> timeout (no feedback).

The same check also runs on every hub poll and command read, so a slower cron
interval only delays the status shown for homes whose hub is offline.
"""

import logging

from app.jobs._runner import job
from app.services.commands import expire_due


def run(db, settings, contracts) -> int:
    return expire_due(db, settings, contracts)


if __name__ == "__main__":
    with job("expire_due") as (settings, contracts, db):
        logging.info("expired/timed out %d commands", run(db, settings, contracts))
