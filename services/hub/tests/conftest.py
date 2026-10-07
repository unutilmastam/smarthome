import os
import pwd
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

HUB_DIR = Path(__file__).resolve().parents[1]
REPO = HUB_DIR.parents[1]
CONTRACTS = REPO / "packages" / "contracts"
SIM_PASSWORD = "sim-device-password"
GW_PASSWORD = "gateway-password"
DEVICE_KEYS = ["garden_lights", "main_meter", "living_temp", "garden_radar", "front_gate",
               "ac_bedroom", "garden_valve", "kitchen_leak", "other_lamp"]

MOSQUITTO = shutil.which("mosquitto") or "/usr/sbin/mosquitto"
MOSQUITTO_PASSWD = shutil.which("mosquitto_passwd") or "/usr/bin/mosquitto_passwd"
needs_mosquitto = pytest.mark.skipif(not os.path.exists(MOSQUITTO),
                                     reason="mosquitto binary not installed")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def broker(tmp_path):
    """Real Mosquitto with the production ACL, anonymous access disabled."""
    if not os.path.exists(MOSQUITTO):
        pytest.skip("mosquitto binary not installed")
    port = free_port()
    passwd = tmp_path / "passwd"
    passwd.touch()
    passwd.chmod(0o600)
    subprocess.run([MOSQUITTO_PASSWD, "-b", str(passwd), "gateway", GW_PASSWORD], check=True)
    for key in DEVICE_KEYS:
        subprocess.run([MOSQUITTO_PASSWD, "-b", str(passwd), key, SIM_PASSWORD], check=True)
    conf = tmp_path / "mosquitto.conf"
    conf.write_text(
        f"listener {port} 127.0.0.1\nallow_anonymous false\n"
        f"password_file {passwd}\nacl_file {HUB_DIR / 'mosquitto' / 'acl'}\n"
        "persistence false\n"
        # When tests run as root, mosquitto would drop to user "mosquitto" and lose
        # access to the 0600 password file.
        + (f"user {pwd.getpwuid(os.geteuid()).pw_name}\n" if os.geteuid() == 0 else ""))
    proc = subprocess.Popen([MOSQUITTO, "-c", str(conf)], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            break
        except OSError:
            time.sleep(0.05)
    else:
        proc.kill()
        raise RuntimeError("mosquitto did not start")
    yield {"host": "127.0.0.1", "port": port}
    proc.terminate()
    proc.wait(5)


@pytest.fixture
def contracts():
    from gateway.contracts import Contracts
    return Contracts(CONTRACTS)


def add_backend_to_path():
    p = str(REPO / "services" / "backend")
    if p not in sys.path:
        sys.path.insert(0, p)
