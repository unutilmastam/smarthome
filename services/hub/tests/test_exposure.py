"""Faza 14: nothing on the hub may listen on the internet (CLAUDE.md rule 7).

Docker publishes ports with its own iptables rules, ahead of ufw. A mapping like
"1883:1883" therefore listens on every address (also public IPv6) whatever ufw says.
Every published port must name its host address explicitly (LAN or Tailscale).
"""

import re
from pathlib import Path

HUB = Path(__file__).resolve().parents[1]
COMPOSE = (HUB / "docker-compose.yml").read_text()
SERVICES_BLOCK = COMPOSE.split("\nservices:\n", 1)[1].split("\nvolumes:\n", 1)[0] + "\n"
ALLOWED_HOSTS = ("${HUB_LAN_IP:?", "${HUB_TAILNET_IP:-127.0.0.1}")


def published_ports():
    out, in_ports, indent = [], False, 0
    for line in COMPOSE.splitlines():
        stripped = line.strip()
        if stripped.startswith("ports:"):
            in_ports, indent = True, len(line) - len(line.lstrip())
            continue
        if in_ports:
            cur = len(line) - len(line.lstrip())
            if stripped.startswith("-") and cur > indent:
                out.append(re.match(r'-\s*"?([^"#]+)"?', stripped).group(1).strip())
            elif stripped and not stripped.startswith("#"):
                in_ports = False
    return out


def test_every_published_port_is_bound_to_lan_or_tailscale():
    ports = published_ports()
    assert len(ports) >= 7, ports      # mosquitto + frigate mappings are all seen
    for p in ports:
        assert p.startswith(ALLOWED_HOSTS), f"port published on all addresses: {p}"


def test_only_esphome_uses_host_network():
    services = re.findall(r"^  (\w[\w-]*):\n((?:    .*\n|\n)*)", SERVICES_BLOCK, re.M)
    host = [name for name, body in services if "network_mode: host" in body]
    # ESPHome needs mDNS/OTA on the LAN; its port 6052 is a host socket, so ufw applies.
    assert host == ["esphome"]


def test_broker_requires_login_and_acl():
    conf = (HUB / "mosquitto" / "mosquitto.conf").read_text()
    assert re.search(r"^allow_anonymous false$", conf, re.M)
    assert re.search(r"^acl_file ", conf, re.M) and re.search(r"^password_file ", conf, re.M)
    assert "allow_anonymous true" not in conf


def test_hub_reports_its_own_data_disk(monkeypatch, tmp_path):
    """Faza 14: a full system disk loses the outbox; the hub says so (never guesses)."""
    import shutil
    from collections import namedtuple
    from types import SimpleNamespace

    from gateway.core import DATA_DISK_WARNING_PCT, Gateway

    g = SimpleNamespace(s=SimpleNamespace(db_path=str(tmp_path / "hub.sqlite3")))
    U = namedtuple("U", "total used free")
    monkeypatch.setattr(shutil, "disk_usage", lambda p: U(1000, 950, 50))
    assert Gateway.data_disk_pct(g) == 95.0 >= DATA_DISK_WARNING_PCT

    def boom(p):
        raise OSError("gone")
    monkeypatch.setattr(shutil, "disk_usage", boom)
    assert Gateway.data_disk_pct(g) is None


def test_every_service_rotates_its_logs():
    services = re.findall(r"^  (\w[\w-]*):\n((?:    .*\n|\n)*)", SERVICES_BLOCK, re.M)
    assert len(services) == 5 and all("logging: *logging" in body for _, body in services), \
        [n for n, b in services if "logging: *logging" not in b]
    assert 'max-size: "10m"' in COMPOSE
