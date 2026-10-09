"""Shared bootstrap for cron jobs: python -m app.jobs.<name> (cPanel Cron Jobs)."""

import logging
import sys
from contextlib import contextmanager

from app.core.config import get_settings
from app.core.contracts import load_contracts
from app.db.session import Database


@contextmanager
def job(name: str):
    logging.basicConfig(level=logging.INFO, format=f"%(asctime)s {name} %(levelname)s %(message)s")
    settings = get_settings()
    database = Database(settings)
    db = next(database.session())
    try:
        yield settings, load_contracts(str(settings.contracts_dir)), db
    except Exception:
        logging.exception("job failed")
        sys.exit(1)
    finally:
        db.close()
        database.engine.dispose()
