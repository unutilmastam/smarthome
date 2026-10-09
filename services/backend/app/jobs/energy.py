"""Hourly (cron): 1m -> 1h roll-up for the last 3 hours and daily kWh for the last 2 days.

Recomputing a short window makes late data (hub was offline and flushed its buffer)
land in the right hour and day.
"""

import logging
from datetime import timedelta

from app.db.types import utcnow
from app.jobs._runner import job
from app.services import telemetry


def run(db) -> dict:
    hours = telemetry.rollup_hours(db, utcnow() - timedelta(hours=3))
    days = telemetry.update_energy_daily(db, days_back=2)
    return {"hours": hours, "energy_days": days}


if __name__ == "__main__":
    with job("energy") as (settings, contracts, db):
        logging.info("%s", run(db))
