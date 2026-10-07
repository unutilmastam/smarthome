"""`alembic upgrade head` on a clean database must match the models exactly."""

import os

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import text

from app.db.base import Base
from app.db.session import make_engine

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PG_URL = os.environ.get("TEST_POSTGRES_URL")


def _urls(tmp_path):
    urls = [f"sqlite:///{tmp_path / 'mig.db'}"]
    if PG_URL:
        urls.append(PG_URL)
    return urls


def _cfg(url):
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "migrations"))
    cfg.attributes["database_url"] = url
    return cfg


@pytest.mark.parametrize("kind", ["sqlite", "postgres"])
def test_upgrade_head_matches_models_and_downgrades(kind, tmp_path):
    if kind == "postgres" and not PG_URL:
        pytest.skip("TEST_POSTGRES_URL not set")
    url = f"sqlite:///{tmp_path / 'mig.db'}" if kind == "sqlite" else PG_URL
    engine = make_engine(url)
    if kind == "postgres":
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    cfg = _cfg(url)
    command.upgrade(cfg, "head")
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []
    command.downgrade(cfg, "base")
    with engine.connect() as conn:
        tables = set(engine.dialect.get_table_names(conn)) - {"alembic_version"}
    assert tables == set()
    engine.dispose()
