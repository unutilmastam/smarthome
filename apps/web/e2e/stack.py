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


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_port(port, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
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
    subprocess.run([mp, "-b", str(passwd), "front_gate", SIM_PW], check=True)
    conf = tmp / "mosquitto.conf"
    conf.write_text(f"listener {mport} 127.0.0.1\nallow_anonymous false\npassword_file {passwd}\n"
                    f"acl_file {HUB / 'mosquitto' / 'acl'}\npersistence false\n"
                    + (f"user {pwd.getpwuid(os.geteuid()).pw_name}\n" if os.geteuid() == 0 else ""))
    start([shutil.which("mosquitto") or "/usr/sbin/mosquitto", "-c", str(conf)])
    wait_port(mport)

    # 2. Backend DB + seed (owner, home, hub, devices).
    db_url = f"sqlite:///{tmp / 'backend.db'}"
    benv = {"ENV": "development", "DATABASE_URL": db_url, "COOKIE_SECURE": "false",
            "JWT_SECRET": "e2e-only-jwt-0123456789abcdef0123456789",
            "SIGNING_MASTER_KEY": "e2e-only-signing-0123456789abcdef01234567"}
    subprocess.run([PY, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env={**os.environ, **benv},
                   check=True)
    seed = subprocess.run([PY, "-c", SEED], cwd=BACKEND, env={**os.environ, **benv}, check=True,
                          capture_output=True, text=True).stdout.strip().splitlines()[-1]
    hub_token, signing_key = seed.split()

    # 3. Backend API.
    start([PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT),
           "--log-level", "warning"], env=benv, cwd=BACKEND)
    wait_port(PORT)

    # 4. Simulated devices and the hub gateway.
    sim = tmp / "devices.json"
    sim.write_text('[{"type":"light","key":"garden_lights"},'
                   '{"type":"gate","key":"front_gate","travel_time_s":2}]')
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


SEED = """
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
                        ("front_gate", "Darvoza", {"cover": {"confirm_timeout_s": 10}})):
    d = Device(id=uuid.uuid4(), home_id=home.id, key=key, name=name, adapter="esphome",
               protocol="mqtt", unsupported=[], availability="unknown")
    d.capabilities = [DeviceCapability(capability=c, config_json=cfg) for c, cfg in caps.items()]
    db.add(d)
db.commit()
print(token, derive_home_key(s.signing_master_key, home.id).hex())
"""

if __name__ == "__main__":
    main()
