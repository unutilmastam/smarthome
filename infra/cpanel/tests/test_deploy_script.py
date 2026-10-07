"""infra/cpanel/deploy.sh against a simulated cPanel account (ADR 0011).

Real PostgreSQL, real alembic, real HTTP health checks. Passenger is replaced by a
uvicorn process that RESTART_CMD restarts (like touching tmp/restart.txt would).
Needs TEST_POSTGRES_ADMIN_URL (a role that may CREATE DATABASE); skipped otherwise.
"""

import gzip
import os
import shutil
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
DEPLOY = REPO / "infra" / "cpanel" / "deploy.sh"
ADMIN_URL = os.environ.get("TEST_POSTGRES_ADMIN_URL")
pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="TEST_POSTGRES_ADMIN_URL not set")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def psql(url, sql):
    return subprocess.run(["psql", "-Atq", url, "-c", sql], check=True, capture_output=True,
                          text=True).stdout.strip()


class Server:
    """A fake cPanel home: app root, web root, deploy state, a 'Passenger' (uvicorn)."""

    def __init__(self, tmp: Path):
        self.home = tmp / "home"
        self.app = self.home / "smarthome-api"
        self.web = self.home / "home.example.uz"
        self.state = self.home / "sh-deploy"
        self.stage = self.home / "sh-incoming"
        self.port = free_port()
        dbname = "deploy_" + uuid.uuid4().hex[:8]
        psql(ADMIN_URL, f"CREATE DATABASE {dbname}")
        base = ADMIN_URL.rsplit("/", 1)[0]
        self.db_url = f"{base}/{dbname}".replace("postgresql://", "postgresql+psycopg://")
        self.psql_url = f"{base}/{dbname}"
        self.dbname = dbname
        self.home.mkdir(parents=True)
        # "virtualenv activate": the test interpreter already has everything installed.
        self.activate = self.home / "activate"
        self.activate.write_text(f'export PATH="{Path(sys.executable).parent}:$PATH"\n')
        restart = self.home / "restart.sh"
        restart.write_text(f"""#!/bin/sh
[ -f {self.home}/uvicorn.pid ] && kill $(cat {self.home}/uvicorn.pid) 2>/dev/null
sleep 0.3
cd {self.app} && nohup {sys.executable} -m uvicorn app.main:app --host 127.0.0.1 \\
  --port {self.port} --log-level warning > {self.home}/uvicorn.log 2>&1 &
echo $! > {self.home}/uvicorn.pid
""")
        restart.chmod(0o755)
        self.restart = restart

    def release(self, build, mutate=None):
        out = self.home / f"build-{build}"
        subprocess.run(["sh", "infra/cpanel/build_release.sh", str(out)], cwd=REPO, check=True,
                       env={**os.environ, "BUILD_ID": build}, capture_output=True)
        if mutate:
            mutate(out)
        if self.stage.exists():
            shutil.rmtree(self.stage)
        shutil.copytree(out, self.stage)
        return out

    def deploy(self, build, first=False, health_timeout=25, extra=None):
        env = {**os.environ, "APP_DIR": str(self.app), "WEB_DIR": str(self.web),
               "STAGE_DIR": str(self.stage), "STATE_DIR": str(self.state),
               "VENV_ACTIVATE": str(self.activate), "EXPECT_BUILD": build,
               "HEALTH_URL": f"http://127.0.0.1:{self.port}/api/v1/health",
               "HEALTH_TIMEOUT": str(health_timeout), "RESTART_CMD": str(self.restart),
               "PIP_INSTALL": ":", "KEEP_BACKUPS": "3", "SKIP_CRON": "1"}
        if first:
            env["INIT_DATABASE_URL"] = self.db_url
        env.update(extra or {})
        p = subprocess.run(["bash", str(DEPLOY)], env=env, capture_output=True, text=True,
                           timeout=300)
        out = dict(line.split("=", 1) for line in p.stdout.splitlines() if "=" in line
                   and line.split("=", 1)[0].isupper())
        return p.returncode, out, p.stdout + p.stderr

    def health(self):
        import json
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/v1/health", timeout=5) as r:
            return json.load(r)["data"]

    def stop(self):
        pid = self.home / "uvicorn.pid"
        if pid.exists():
            subprocess.run(["kill", pid.read_text().strip()], capture_output=True)
        time.sleep(0.3)
        psql(ADMIN_URL, f"DROP DATABASE IF EXISTS {self.dbname} WITH (FORCE)")


@pytest.fixture
def server(tmp_path):
    s = Server(tmp_path)
    yield s
    s.stop()


def add_migration(body):
    """Mutator: add a migration 9999 to the staged release."""
    def mutate(out: Path):
        versions = out / "api" / "migrations" / "versions"
        heads = sorted(p.stem.split("_")[0] for p in versions.glob("0*.py"))
        (versions / "9999_test.py").write_text(
            f"from alembic import op\nimport sqlalchemy as sa\n\nrevision = '9999'\n"
            f"down_revision = '{heads[-1]}'\nbranch_labels = None\ndepends_on = None\n\n\n"
            f"def upgrade():\n{body}\n\n\ndef downgrade():\n    pass\n")
    return mutate


def test_first_deploy_creates_env_and_backup(server):
    server.release("v1")
    code, out, log = server.deploy("v1", first=True)
    assert code == 0, log
    assert out["RESULT"] == "deployed"
    assert server.health()["build"] == "v1"
    env = server.app / ".env"
    assert oct(env.stat().st_mode & 0o777) == "0o600"
    text = env.read_text()
    assert "ENV=production" in text and len(text.split("JWT_SECRET=")[1].split()[0]) == 64
    assert len(list((server.state / "backups").glob("pre-deploy-*.sql.gz"))) == 1
    assert (server.web / "index.html").exists()


def test_good_deploy_then_broken_migration_rolls_back(server):
    server.release("v1")
    assert server.deploy("v1", first=True)[0] == 0
    server.release("v2")
    assert server.deploy("v2")[0] == 0
    # Real data written between deploys must survive the rollback.
    psql(server.psql_url, "INSERT INTO homes (id, name, timezone, currency, created_at, updated_at)"
         " VALUES (gen_random_uuid(), 'Uy', 'Asia/Tashkent', 'UZS', now(), now())")
    rev_before = psql(server.psql_url, "SELECT version_num FROM alembic_version")
    server.release("v3", add_migration("    op.create_table('half_done', sa.Column('id', sa.Integer, primary_key=True))\n    raise RuntimeError('migration bug')"))
    code, out, log = server.deploy("v3")
    assert code == 10, log
    assert out["RESULT"] == "rolled_back" and "alembic" in out["DETAIL"]
    assert server.health()["build"] == "v2"
    assert psql(server.psql_url, "SELECT version_num FROM alembic_version") == rev_before
    assert psql(server.psql_url, "SELECT count(*) FROM homes") == "1"
    assert psql(server.psql_url, "SELECT to_regclass('public.half_done') IS NULL") == "t"


def test_broken_app_after_successful_migration_rolls_back_code_and_db(server):
    server.release("v1")
    assert server.deploy("v1", first=True)[0] == 0

    def broken(out: Path):
        add_migration("    op.create_table('new_feature', sa.Column('id', sa.Integer, primary_key=True))")(out)
        main = out / "api" / "app" / "main.py"
        main.write_text(main.read_text() + "\nraise RuntimeError('boot bug')\n")
    server.release("v2", broken)
    code, out, log = server.deploy("v2", health_timeout=10)
    assert code == 10, log
    assert "health check failed" in out["DETAIL"]
    assert server.health()["build"] == "v1"
    assert psql(server.psql_url, "SELECT to_regclass('public.new_feature') IS NULL") == "t"
    assert "boot bug" not in (server.app / "app" / "main.py").read_text()


def test_backups_keep_last_n(server):
    server.release("v1")
    server.deploy("v1", first=True)
    for b in ("v2", "v3", "v4", "v5"):
        time.sleep(1.1)  # distinct timestamps
        server.release(b)
        assert server.deploy(b)[0] == 0
    dumps = sorted((server.state / "backups").glob("pre-deploy-*.sql.gz"))
    assert len(dumps) == 3  # KEEP_BACKUPS=3 in the test (10 in production)
    with gzip.open(dumps[-1], "rt") as fh:
        assert "CREATE TABLE" in fh.read()


def test_lock_and_failed_backup_abort_without_changes(server):
    server.release("v1")
    assert server.deploy("v1", first=True)[0] == 0
    server.release("v2")
    (server.state / "lock").mkdir()
    code, out, _ = server.deploy("v2")
    assert (code, out["RESULT"]) == (11, "aborted")
    (server.state / "lock").rmdir()
    env = server.app / ".env"
    good = env.read_text()
    env.write_text(good.replace(server.dbname, "no_such_db"))
    code, out, log = server.deploy("v2")
    assert code == 11 and "pg_dump failed" in out["DETAIL"], log
    env.write_text(good)
    assert server.health()["build"] == "v1"  # nothing was touched
