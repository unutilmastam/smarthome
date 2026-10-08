"""Faza 14: backup -> disaster -> restore, performed for real (PostgreSQL, deployed app,
alembic, health check). Same simulated cPanel account as test_deploy_script.py."""

import gzip
import os
import subprocess
import sys
from pathlib import Path

import pytest

from test_deploy_script import ADMIN_URL, Server, psql  # noqa: F401  (skip marker below)

pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="TEST_POSTGRES_ADMIN_URL not set")


@pytest.fixture
def server(tmp_path):
    s = Server(tmp_path)
    s.release("v1")
    code, _, log = s.deploy("v1", first=True)
    assert code == 0, log
    yield s
    s.stop()


def run(server, script, *args, **env):
    e = {**os.environ, "PATH": f"{Path(sys.executable).parent}:{os.environ['PATH']}",
         "HOME": str(server.home), "STATE_DIR": str(server.state),
         "RESTART_CMD": str(server.restart), **env}
    p = subprocess.run(["bash" if script.endswith("restore.sh") else "sh", str(server.app / script), *args],
                       env=e, capture_output=True, text=True, timeout=180)
    return p.returncode, p.stdout + p.stderr


def healthy(server, timeout=30):
    import time
    end = time.time() + timeout
    while time.time() < end:
        try:
            return server.health()
        except OSError:
            time.sleep(0.3)
    raise AssertionError("app did not come back after restore")


def homes(server):
    return psql(server.psql_url, "SELECT string_agg(name, ',' ORDER BY name) FROM homes")


def add_home(server, name):
    psql(server.psql_url, "INSERT INTO homes (id, name, timezone, currency, created_at, updated_at)"
         f" VALUES (gen_random_uuid(), '{name}', 'Asia/Tashkent', 'UZS', now(), now())")


def test_backup_disaster_restore_and_undo(server):
    add_home(server, "Uy")
    code, out = run(server, "backup.sh")
    assert code == 0 and "backup ok" in out, out
    dump = next((server.state / "daily").glob("smarthome-*.sql.gz"))
    assert oct(dump.stat().st_mode & 0o777) == "0o600"

    # Disaster: data deleted, a table dropped, junk written.
    psql(server.psql_url, "DELETE FROM homes")
    psql(server.psql_url, "DROP TABLE audit_log")
    add_home(server, "Xato")
    head = psql(server.psql_url, "SELECT version_num FROM alembic_version")

    # Dry check changes nothing.
    code, out = run(server, "restore.sh", str(dump))
    assert code == 0 and "dry check only" in out, out
    assert homes(server) == "Xato"

    # A truncated dump is refused before anything is touched.
    bad = server.home / "bad.sql.gz"
    with gzip.open(dump, "rb") as f:
        raw = f.read()
    bad.write_bytes(gzip.compress(raw[: len(raw) // 2]))
    code, out = run(server, "restore.sh", str(bad), "--yes")
    assert code == 1 and "incomplete" in out, out
    assert homes(server) == "Xato"

    # The real restore.
    code, out = run(server, "restore.sh", str(dump), "--yes")
    assert code == 0, out
    assert homes(server) == "Uy"
    assert psql(server.psql_url, "SELECT to_regclass('public.audit_log') IS NOT NULL") == "t"
    assert psql(server.psql_url, "SELECT version_num FROM alembic_version") == head
    assert healthy(server)["status"] == "ok"      # restarted and serving
    safety = next((server.state / "backups").glob("pre-restore-*.sql.gz"))
    with gzip.open(safety, "rt") as f:
        assert "Xato" in f.read()

    # Undo with the safety dump: back to the state right before the restore.
    code, out = run(server, "restore.sh", str(safety), "--yes")
    assert code == 0, out
    assert homes(server) == "Xato"


def test_failed_load_is_rolled_back(server):
    add_home(server, "Uy")
    run(server, "backup.sh")
    dump = next((server.state / "daily").glob("smarthome-*.sql.gz"))
    # Valid footer, but a statement in the middle fails: the whole load must roll back.
    with gzip.open(dump, "rt") as f:
        text = f.read()
    broken = text.replace("COPY public.homes", "SELECT no_such_function();\nCOPY public.homes", 1)
    bad = server.home / "broken.sql.gz"
    bad.write_bytes(gzip.compress(broken.encode()))
    add_home(server, "Keyin")
    code, out = run(server, "restore.sh", str(bad), "--yes")
    assert code == 1 and "rolled back" in out, out
    assert homes(server) == "Keyin,Uy"           # untouched, tables not dropped


def test_backup_never_reports_ok_for_a_failed_dump(server):
    env = server.app / ".env"
    good = env.read_text()
    env.write_text(good.replace(server.dbname, "no_such_db"))
    code, out = run(server, "backup.sh")
    env.write_text(good)
    assert code != 0 and "backup ok" not in out, out
    assert list((server.state / "daily").glob("*")) == []
