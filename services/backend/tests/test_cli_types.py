import io
from datetime import datetime

import pytest
from sqlalchemy import func, select

from app import cli
from app.core.config import get_settings
from app.models import AuditLog, HomeMember, User


def test_cli_create_owner(tmp_path, monkeypatch, capsys):
    db_url = f"sqlite:///{tmp_path / 'cli.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    try:
        from app.db.base import Base
        from app.db.session import make_engine
        engine = make_engine(db_url)
        Base.metadata.create_all(engine)
        monkeypatch.setattr("sys.stdin", io.StringIO("a-long-password-1\n"))
        rc = cli.main(["create-owner", "--email", "Me@Example.com", "--name", "Men",
                       "--home-name", "Uy", "--password-stdin"])
        assert rc == 0
        assert "home_id=" in capsys.readouterr().out
        from sqlalchemy.orm import Session
        with Session(engine) as s:
            user = s.scalar(select(User))
            assert user.email == "me@example.com"
            assert s.scalar(select(HomeMember.role)) == "owner"
            assert s.scalar(select(AuditLog.action)) == "home.created"
        # Running it again (installer re-run / forgotten password): same home, new password.
        monkeypatch.setattr("sys.stdin", io.StringIO("another-password-2\n"))
        assert cli.main(["create-owner", "--email", "me@example.com", "--name", "Men",
                         "--password-stdin"]) == 0
        from app.core.security import verify_secret
        from app.models import Home
        with Session(engine) as s:
            assert s.scalar(select(func.count()).select_from(Home)) == 1
            assert verify_secret(s.scalar(select(User)).password_hash, "another-password-2")
            assert "user.password_reset" in s.scalars(select(AuditLog.action)).all()
        monkeypatch.setattr("sys.stdin", io.StringIO("short\n"))
        rc = cli.main(["create-owner", "--email", "x@example.com", "--name", "X",
                       "--password-stdin"])
        assert rc == 1
    finally:
        get_settings.cache_clear()


def test_naive_datetime_rejected(dbs, owner_home):
    user = dbs.scalar(select(User))
    user.locked_until = datetime(2026, 1, 1, 12, 0, 0)
    with pytest.raises(Exception):
        dbs.commit()
    dbs.rollback()


def test_datetimes_come_back_utc(dbs, owner_home):
    user = dbs.scalar(select(User))
    assert user.created_at.tzinfo is not None
    assert user.created_at.utcoffset().total_seconds() == 0
