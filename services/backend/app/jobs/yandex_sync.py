"""Cron, every minute (ADR 0016): Yandex Alisa devices and states for every home that
linked Yandex. A failed sync never stops the others; the error is stored on the link."""
import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.contracts import load_contracts
from app.db.session import Database
from app.models import Integration
from app.services import yandex


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    contracts = load_contracts(str(settings.contracts_dir))
    db = next(Database(settings).session())
    try:
        for i in db.scalars(select(Integration).where(Integration.kind == "yandex")).all():
            try:
                res = yandex.sync(db, i, contracts, settings)
                logging.info("yandex sync %s: %s", i.home_id, res)
            except Exception:
                db.rollback()
                logging.exception("yandex sync %s failed", i.home_id)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
