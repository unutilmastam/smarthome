"""Starts the full [SIM] stack for Playwright: mosquitto + backend + hub gateway + simulator.

    PYTHON=python3 python e2e/stack.py     (prints "STACK READY", runs until killed)

Backend: http://127.0.0.1:8000 (SQLite in a temp dir). Login: owner@example.com /
correct-horse-battery, PIN 4821. Nothing here is used in production.
"""

import os
import pwd
import shutil
import signal
import socket
import subprocess
import sys
import json
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
BACKEND = REPO / "services" / "backend"
HUB = REPO / "services" / "hub"
PY = os.environ.get("PYTHON", sys.executable)
PORT = int(os.environ.get("E2E_BACKEND_PORT", "8000"))
PASSWORD = "correct-horse-battery"
SIM_PW = "sim-device-password"
GW_PW = "gateway-password"

procs = []

# [SIM] the electrical panel (ADR 0015): key, name, number, rating, curve, poles, tripped
BREAKERS = [
    ('brk_oshxona', 'Oshxona', 1, 16, 'C', 1, False),
    ('brk_mehmonxona', 'Mehmonxona', 2, 16, 'C', 1, False),
    ('brk_yotoqxona', 'Yotoqxona', 3, 16, 'C', 1, False),
    ('brk_bolalar', 'Bolalar xonasi', 4, 16, 'C', 1, False),
    ('brk_hammom', 'Hammom', 5, 16, 'C', 1, False),
    ('brk_konditsioner', 'Konditsioner', 6, 20, 'C', 1, False),
    ('brk_kir_mashina', 'Kir yuvish mashinasi', 7, 16, 'C', 1, False),
    ('brk_suv_isitgich', 'Suv isitgich', 8, 25, 'C', 2, False),
    ('brk_yorug_1', 'Yoritish 1-qavat', 9, 10, 'B', 1, False),
    ('brk_yorug_2', 'Yoritish 2-qavat', 10, 10, 'B', 1, False),
    ('brk_hovli', 'Hovli', 11, 16, 'C', 1, False),
    ('brk_nasos', 'Nasos', 12, 16, 'C', 1, True),
]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port, timeout=20, proc=None):
    end = time.time() + timeout
    while time.time() < end:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(f"{proc.args} exited with {proc.returncode} before port {port} opened")
        try:
            socket.create_connection(("127.0.0.1", port), 0.3).close()
            return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"port {port} not ready")


def start(cmd, env=None, cwd=None):
    p = subprocess.Popen(cmd, env={**os.environ, **(env or {})}, cwd=cwd)
    procs.append(p)
    return p


def stop(*_):
    for p in reversed(procs):
        p.terminate()
    for p in procs:
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    tmp = Path(tempfile.mkdtemp(prefix="sh-e2e-"))

    # 1. Local broker with the production ACL.
    mport = free_port()
    passwd = tmp / "passwd"
    passwd.touch()
    passwd.chmod(0o600)
    mp = shutil.which("mosquitto_passwd") or "/usr/bin/mosquitto_passwd"
    subprocess.run([mp, "-b", str(passwd), "gateway", GW_PW], check=True)
    subprocess.run([mp, "-b", str(passwd), "garden_lights", SIM_PW], check=True)
    for key in ("front_gate", "front_door", "siren", *[b[0] for b in BREAKERS]):
        subprocess.run([mp, "-b", str(passwd), key, SIM_PW], check=True)
    conf = tmp / "mosquitto.conf"
    conf.write_text(f"listener {mport} 127.0.0.1\nallow_anonymous false\npassword_file {passwd}\n"
                    f"acl_file {HUB / 'mosquitto' / 'acl'}\npersistence false\n"
                    + (f"user {pwd.getpwuid(os.geteuid()).pw_name}\n" if os.geteuid() == 0 else ""))
    broker = start([shutil.which("mosquitto") or "/usr/sbin/mosquitto", "-c", str(conf)])
    wait_port(mport, proc=broker)

    # 2. Backend DB + seed (owner, home, hub, devices).
    db_url = f"sqlite:///{tmp / 'backend.db'}"
    # LOGIN_IP_LIMIT: every e2e test logs in from 127.0.0.1; the real limit (20/5 min)
    # would lock the suite out (it did — the protection works).
    benv = {"ENV": "development", "DATABASE_URL": db_url, "COOKIE_SECURE": "false",
            "LOGIN_IP_LIMIT": "1000",
            "JWT_SECRET": "e2e-only-jwt-0123456789abcdef0123456789",
            "SIGNING_MASTER_KEY": "e2e-only-signing-0123456789abcdef01234567"}
    subprocess.run([PY, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env={**os.environ, **benv},
                   check=True)
    seed = subprocess.run([PY, "-c", SEED], cwd=BACKEND, env={**os.environ, **benv}, check=True,
                          capture_output=True, text=True).stdout.strip().splitlines()[-1]
    hub_token, signing_key = seed.split()

    # 3. Backend API.
    api = start([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT),
                 "--log-level", "warning"], env=benv, cwd=BACKEND)
    wait_port(PORT, proc=api)

    # 4. Simulated devices and the hub gateway.
    sim = tmp / "devices.json"
    sim.write_text('[{"type":"light","key":"garden_lights"},'
                   '{"type":"gate","key":"front_gate","travel_time_s":2},'
                   '{"type":"contact","key":"front_door"},{"type":"siren","key":"siren"},'
                   + ",".join(json.dumps({"type": "breaker", "key": b[0], "switch_time_s": 0.3,
                                          "closed": b[0] != "brk_hovli", "tripped": b[6]})
                              for b in BREAKERS) + ']')
    start([PY, "-m", "simulator", str(sim)], cwd=HUB,
          env={"MQTT_HOST": "127.0.0.1", "MQTT_PORT": str(mport), "SIM_DEVICE_PASSWORD": SIM_PW})
    start([PY, "-m", "gateway"], cwd=HUB, env={
        "BACKEND_URL": f"http://127.0.0.1:{PORT}", "HUB_TOKEN": hub_token,
        "SIGNING_KEY_HEX": signing_key, "MQTT_HOST": "127.0.0.1", "MQTT_PORT": str(mport),
        "MQTT_USERNAME": "gateway", "MQTT_PASSWORD": GW_PW, "DB_PATH": str(tmp / "hub.sqlite3"),
        "POLL_INTERVAL_S": "0.5", "HEARTBEAT_INTERVAL_S": "2", "CONFIG_REFRESH_S": "2",
        "FLUSH_INTERVAL_S": "0.3"})
    print("STACK READY", flush=True)
    while True:
        for p in procs:
            if p.poll() is not None:
                print(f"process exited: {p.args}", flush=True)
                stop()
        time.sleep(1)


SEED = "BREAKERS = " + repr(BREAKERS) + """
from app.core.config import get_settings
from app.core.security import hash_secret, new_token, sha256_hex
from app.core.signing import derive_home_key
from app.cli import create_owner
from app.db.session import Database
from app.models import Device, DeviceCapability, Hub, User
import uuid
s = get_settings()
db = next(Database(s).session())
home = create_owner(db, "owner@example.com", "Ega", "correct-horse-battery", "Uy")
user = db.query(User).one()
user.pin_hash = hash_secret("4821")
token = "hub_" + new_token(32)
db.add(Hub(id=uuid.uuid4(), home_id=home.id, name="Asosiy hub", token_hash=sha256_hex(token)))
for key, name, caps in (("garden_lights", "Bog' chiroqlari", {"switch": {}, "dimmer": {}}),
                        ("front_gate", "Darvoza", {"cover": {"confirm_timeout_s": 10}}),
                        ("front_door", "Kirish eshigi", {"contact": {}}),
                        ("siren", "Sirena", {"switch": {}})):
    d = Device(id=uuid.uuid4(), home_id=home.id, key=key, name=name, adapter="esphome",
               protocol="mqtt", unsupported=[], availability="unknown")
    d.capabilities = [DeviceCapability(capability=c, config_json=cfg) for c, cfg in caps.items()]
    db.add(d)
# [SIM] one unacknowledged critical notification for the notifications e2e (ADR 0014).
from app.db.types import utcnow
from app.models import Notification
for key, name, pos, rating, curve, poles, _ in BREAKERS:
    d = Device(id=uuid.uuid4(), home_id=home.id, key=key, name=name, adapter="esphome", icon="breaker",
               protocol="mqtt", unsupported=[], availability="unknown")
    d.capabilities = [DeviceCapability(capability="breaker", config_json={
        "position": pos, "rating_a": rating, "curve": curve, "poles": poles, "confirm_timeout_s": 5})]
    db.add(d)
db.add(Notification(id=uuid.uuid4(), home_id=home.id, severity="critical", source="event",
                    kind="cover.sensor_conflict", title="Gerkonlar bir-biriga zid", body="",
                    data={"device_key": "front_gate"}, ts=utcnow(), dedupe_key="e2e:seed"))
db.commit()
print(token, derive_home_key(s.signing_master_key, home.id).hex())
"""

if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        if not isinstance(exc, SystemExit):
            print(f"stack failed: {exc!r}", file=sys.stderr, flush=True)
        # Never leave children (mosquitto, uvicorn, ...) running and holding the pipes.
        for p in procs:
            if p.poll() is None:
                p.kill()
        raise
