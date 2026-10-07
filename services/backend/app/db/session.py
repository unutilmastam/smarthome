from typing import Iterator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings


def make_engine(url: str, **kwargs) -> Engine:
    if url.startswith("sqlite"):
        kwargs.setdefault("connect_args", {"check_same_thread": False})
        engine = create_engine(url, **kwargs)

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # pragma: no cover - trivial
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        return engine
    # Shared hosting: keep the pool small.
    if "poolclass" not in kwargs:
        kwargs.setdefault("pool_size", 3)
        kwargs.setdefault("max_overflow", 2)
    kwargs.setdefault("pool_pre_ping", True)
    return create_engine(url, **kwargs)


class Database:
    def __init__(self, settings: Settings, engine: Optional[Engine] = None):
        self.engine = engine or make_engine(settings.database_url)
        self.sessionmaker = sessionmaker(bind=self.engine, expire_on_commit=False)

    def session(self) -> Iterator[Session]:
        db = self.sessionmaker()
        try:
            yield db
        finally:
            db.close()
