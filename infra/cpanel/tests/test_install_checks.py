"""install.sh checks, before anything on the server changes (no PostgreSQL needed).

`psql`, `uapi` and `curl` are replaced by small scripts that behave like cPanel's; the run
stops after the checks (SH_DRY_RUN=1) and prints the plan, or stops with exit 11 and the
reason in Uzbek.
"""

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


@pytest.fixture
def box(tmp_path):
    home = tmp_path / "home"
    rel = tmp_path / "rel"
    (rel / "api" / "app").mkdir(parents=True)
    (rel / "web").mkdir()
    (rel / "api" / "passenger_wsgi.py").write_text("")
    (rel / "api" / "app" / "_build.py").write_text('BUILD = "abc123"\n')
    (rel / "web" / "index.html").write_text("")
    for name in ("deploy.sh", "install.sh"):
        (rel / name).write_text((REPO / "infra" / "cpanel" / name).read_text())
    venv = home / "virtualenv" / "smarthome-api" / "3.10" / "bin"
    venv.mkdir(parents=True)
    (venv / "activate").write_text("")
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    state = tmp_path / "state"
    state.mkdir()

    def stub(name, body):
        (bin_ / name).write_text("#!/bin/sh\n" + body)
        (bin_ / name).chmod(0o755)

    # curl: https works unless CURL_RC says otherwise
    stub("curl", 'exit "${CURL_RC:-0}"\n')
    # psql: the login works only when $STATE/db_ok exists (or PSQL_ERR is empty)
    stub("psql", f'[ -f {state}/db_ok ] && exit 0\necho "psql: error: FATAL:  $PSQL_ERR" >&2\nexit 2\n')

    def run(**env):
        e = {"PATH": f"{bin_}:/usr/bin:/bin", "HOME": str(home), "STATE_DIR": str(state),
             "CP_USER": "itcode", "SH_NONINTERACTIVE": "1", "SH_DRY_RUN": "1",
             "PSQL_ERR": "password authentication failed for user", **env}
        p = subprocess.run(["bash", str(rel / "install.sh")], env=e, capture_output=True,
                           text=True, timeout=60)
        return p.returncode, p.stdout + p.stderr

    box = type("Box", (), {})()
    box.run, box.stub, box.state, box.home = run, stub, state, home
    return box


def test_domain_is_cleaned_and_names_follow_the_subdomain(box):
    (box.state / "db_ok").write_text("")
    code, out = box.run(DOMAIN="https://www.SMY.itcode.uz/", DB_PASS="p@ss:w/rd", OWNER_EMAIL="a@b.uz",
                        OWNER_PASSWORD="0123456789")
    assert code == 0, out
    assert "domain=smy.itcode.uz" in out
    assert f"web={box.home}/smy.itcode.uz" in out
    assert "postgresql+psycopg://***@127.0.0.1:5432/itcode_smy" in out
    assert "p@ss" not in out and "p%40ss" not in out          # never printed


def test_a_database_name_is_not_a_domain(box):
    code, out = box.run(DOMAIN="itcode_smarthome")
    assert code == 11 and "sayt manzili emas" in out


def test_https_and_python_app_are_checked_first(box):
    code, out = box.run(DOMAIN="smy.itcode.uz", CURL_RC="60")
    assert code == 11 and "SSL" in out and "hech narsa" in out
    code, out = box.run(DOMAIN="smy.itcode.uz", CURL_RC="6")
    assert code == 11 and "topilmadi" in out
    (box.home / "virtualenv" / "smarthome-api" / "3.10" / "bin" / "activate").unlink()
    code, out = box.run(DOMAIN="smy.itcode.uz")
    assert code == 11 and "Setup Python App" in out


@pytest.mark.parametrize("err,expect", [
    ("password authentication failed for user", "paroli noto'g'ri"),
    ('database "itcode_smy" does not exist', "yo'q"),
    ('no pg_hba.conf entry for host "::1"', "Add User To Database"),
])
def test_database_problems_are_explained(box, err, expect):
    code, out = box.run(DOMAIN="smy.itcode.uz", DB_PASS="x", PSQL_ERR=err)
    assert code == 11 and expect in out, out


def test_missing_database_is_created_with_cpanel_uapi(box):
    log = box.state / "uapi.log"
    box.stub("uapi", f'''echo "$*" >> {log}
case "$*" in
  *list_databases*|*list_users*) echo '{{"result":{{"status":1,"data":[]}}}}' ;;
  *grant_all_privileges*) touch {box.state}/db_ok; echo '{{"result":{{"status":1,"data":null}}}}' ;;
  *DomainInfo*) echo '{{"result":{{"status":1,"data":{{"documentroot":"/home/itcode/public_html/smy"}}}}}}' ;;
  *) echo '{{"result":{{"status":1,"data":null}}}}' ;;
esac
''')
    code, out = box.run(DOMAIN="smy.itcode.uz", DB_PASS="secret123", PSQL_ERR='database "itcode_smy" does not exist',
                        OWNER_EMAIL="a@b.uz", OWNER_PASSWORD="0123456789")
    assert code == 0, out
    calls = log.read_text()
    assert "create_database name=itcode_smy" in calls
    assert "create_user name=itcode_smy" in calls
    assert "grant_all_privileges user=itcode_smy database=itcode_smy" in calls
    assert "web=/home/itcode/public_html/smy" in out                 # Document Root from cPanel


def test_short_owner_password_stops_before_any_change(box):
    (box.state / "db_ok").write_text("")
    code, out = box.run(DOMAIN="smy.itcode.uz", DB_PASS="x", OWNER_EMAIL="a@b.uz", OWNER_PASSWORD="short")
    assert code == 11 and "10 belgi" in out
