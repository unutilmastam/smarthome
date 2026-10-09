"""Every minute (ADR 0014): watchdog (hub/device offline and back), reminders for
unacknowledged critical notifications, then delivery of everything due (retries too)."""

import logging

from app.jobs._runner import job
from app.services import notifications


def run(db, settings) -> dict:
    made = notifications.watchdog(db, settings)
    reminded = notifications.reminders(db, settings)
    sent = notifications.deliver_due(db, settings)
    return {"created": len(made), "reminded": reminded, "deliveries": sent}


if __name__ == "__main__":
    with job("notify") as (settings, contracts, db):
        logging.info("notify %s", run(db, settings))
