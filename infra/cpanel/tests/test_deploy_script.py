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
    # ADR 0014: generated on the server, never printed.
    assert len(text.split("TELEGRAM_WEBHOOK_SECRET=")[1].split()[0]) == 64
    assert len(text.split("VAPID_PRIVATE_KEY=")[1].split()[0]) == 43
    assert "VAPID_PRIVATE_KEY=" not in log and "TELEGRAM_WEBHOOK_SECRET=" not in log


def test_bot_token_and_public_url_are_written_to_env_and_kept(server):
    server.release("v1")
    # No bot token here: the webhook is never contacted from a test.
    extra = {"TELEGRAM_BOT_TOKEN": "", "PUBLIC_BASE_URL": "https://home.example.uz"}
    code, out, log = server.deploy("v1", first=True, extra=extra)
    assert code == 0, log
    text = (server.app / ".env").read_text()
    assert "PUBLIC_BASE_URL=https://home.example.uz" in text
    secret = text.split("TELEGRAM_WEBHOOK_SECRET=")[1].split()[0]
    server.release("v2")
    assert server.deploy("v2", extra=extra)[0] == 0
    again = (server.app / ".env").read_text()
    assert again.split("TELEGRAM_WEBHOOK_SECRET=")[1].split()[0] == secret      # not rotated
    assert again.count("PUBLIC_BASE_URL=") == 1
    assert oct((server.app / ".env").stat().st_mode & 0o777) == "0o600"


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


def test_deploy_keeps_cpanel_owned_files_in_the_web_root(server):
    """CloudLinux writes the Passenger config of the /api app into the web root and AutoSSL
    keeps its challenges there: a deploy must never delete them."""
    server.release("v1")
    assert server.deploy("v1", first=True)[0] == 0
    (server.web / "api").mkdir(exist_ok=True)
    (server.web / "api" / ".htaccess").write_text("PassengerAppRoot /home/u/smarthome-api\n")
    (server.web / ".well-known" / "acme-challenge").mkdir(parents=True)
    (server.web / ".well-known" / "acme-challenge" / "tok").write_text("x")
    ht = server.web / ".htaccess"
    block = ("# DO NOT REMOVE. CLOUDLINUX PASSENGER CONFIGURATION BEGIN\nPassengerAppRoot \"/x\"\n"
             "# DO NOT REMOVE. CLOUDLINUX PASSENGER CONFIGURATION END")
    ht.write_text(block + "\n\n" + ht.read_text())
    server.release("v2")
    code, _, log = server.deploy("v2")
    assert code == 0, log
    assert (server.web / "api" / ".htaccess").read_text().startswith("PassengerAppRoot")
    assert (server.web / ".well-known" / "acme-challenge" / "tok").exists()
    text = ht.read_text()
    assert text.count("CLOUDLINUX PASSENGER CONFIGURATION BEGIN") == 1 and "RewriteEngine On" in text


def test_install_script_first_run_creates_owner_and_update_reuses_answers(server):
    """The zip's install.sh (manual upload from an iPad) drives the same deploy.sh."""
    rel = server.release("v9")
    env = {**os.environ, "SH_NONINTERACTIVE": "1", "HOME": str(server.home),
           "STATE_DIR": str(server.state), "DOMAIN": "home.example.uz",
           "APP_DIR": str(server.app), "WEB_DIR": str(server.web),
           "VENV_ACTIVATE": str(server.activate), "INIT_DATABASE_URL": server.db_url,
           "HEALTH_URL": f"http://127.0.0.1:{server.port}/api/v1/health", "HEALTH_TIMEOUT": "25",
           "RESTART_CMD": str(server.restart), "PIP_INSTALL": ":", "SKIP_CRON": "1",
           "OWNER_EMAIL": "ega@example.uz", "OWNER_NAME": "Ega", "HOME_NAME": "Uy",
           "OWNER_PASSWORD": "correct-horse-battery", "SH_SKIP_HTTPS_CHECK": "1"}
    # A wrong answer remembered from an earlier try must not beat the value given now.
    server.state.mkdir(parents=True, exist_ok=True)
    (server.state / "install.conf").write_text("DOMAIN=itcode_smarthome\nWEB_DIR=/nowhere\n")
    p = subprocess.run(["bash", str(rel / "install.sh")], env=env, capture_output=True, text=True,
                       timeout=300)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "O'rnatildi" in p.stdout and "Owner created" in p.stdout
    assert psql(server.psql_url, "SELECT email FROM users") == "ega@example.uz"
    conf = (server.state / "install.conf").read_text()
    assert "home.example.uz" in conf and "postgresql" not in conf and "nowhere" not in conf      # no secrets remembered
    assert "PUBLIC_BASE_URL=https://home.example.uz" in (server.app / ".env").read_text()
    # Update: answers come from install.conf; no new owner, no DB question.
    rel2 = server.release("v10")
    env2 = {k: v for k, v in env.items() if k not in ("DOMAIN", "APP_DIR", "WEB_DIR", "INIT_DATABASE_URL")}
    p = subprocess.run(["bash", str(rel2 / "install.sh")], env=env2, capture_output=True, text=True,
                       timeout=300)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "Owner created" not in p.stdout
    assert server.health()["build"] == "v10"


def test_hosts_without_rsync_deploy_and_roll_back_the_same_way(server):
    """hostmaster.uz has no rsync: deploy.sh falls back to the Python copy (SH_NO_RSYNC forces it)."""
    no_rsync = {"SH_NO_RSYNC": "1"}
    server.release("v1")
    code, _, log = server.deploy("v1", first=True, extra=no_rsync)
    assert code == 0, log
    (server.web / "api").mkdir(exist_ok=True)
    (server.web / "api" / ".htaccess").write_text("PassengerAppRoot /home/u/smarthome-api\n")
    (server.web / "stale.js").write_text("old")
    (server.app / "logs").mkdir(exist_ok=True)
    (server.app / "logs" / "app.log").write_text("keep")
    server.release("v2")
    code, _, log = server.deploy("v2", extra=no_rsync)
    assert code == 0, log
    assert server.health()["build"] == "v2"
    assert not (server.web / "stale.js").exists()                 # --delete
    assert (server.web / "api" / ".htaccess").exists()            # excluded: kept
    assert (server.app / "logs" / "app.log").read_text() == "keep"
    assert (server.app / ".env").exists()
    server.release("v3", add_migration("    raise RuntimeError('migration bug')"))
    code, out, log = server.deploy("v3", extra=no_rsync)
    assert code == 10 and out["RESULT"] == "rolled_back", log
    assert server.health()["build"] == "v2"
    assert (server.web / "api" / ".htaccess").exists()


def test_python_fallback_matches_rsync(tmp_path):
    if not shutil.which("rsync"):
        pytest.skip("rsync not installed")
    fn = DEPLOY.read_text().split("sync_tree() {", 1)[1].split("\n}\n", 1)[0]
    src = tmp_path / "src"
    for rel, text in {"a.txt": "1", "d/b.txt": "2", "d/logs/x": "3", "api/y": "4", "x/api/z": "5"}.items():
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_text(text)
    (src / "link").symlink_to("a.txt")
    results = []
    for mode in ("rsync", "python"):
        dst = tmp_path / mode
        for rel, text in {"old.txt": "o", "api/keep": "k", "d/logs/keep": "k", "a.txt": "stale"}.items():
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            (dst / rel).write_text(text)
        env = {**os.environ, **({"SH_NO_RSYNC": "1"} if mode == "python" else {})}
        script = f"sync_tree() {{{fn}\n}}\nsync_tree --exclude '/api/' --exclude 'logs/' {src}/ {dst}/"
        subprocess.run(["bash", "-c", script], env=env, check=True)
        results.append(sorted((str(p.relative_to(dst)), p.is_symlink() and os.readlink(p) or p.read_text())
                              for p in dst.rglob("*") if p.is_file() or p.is_symlink()))
    assert results[0] == results[1]
