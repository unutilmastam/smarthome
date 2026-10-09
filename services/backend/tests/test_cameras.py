"""Phase 10: cameras are metadata-only in the cloud (ADR 0006)."""

import re

import pytest
from sqlalchemy import LargeBinary

from app.db.base import Base
from conftest import Api


@pytest.fixture
def hub(client, owner, owner_home):
    d = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "h"}).json()["data"]
    api = Api(client, d["hub_token"])
    api.post("/api/v1/hub/heartbeat", json={"version": "1", "tailnet_host": "hub.tail1234.ts.net",
                                            "lan_host": "hub.local"})
    return api


@pytest.fixture
def cam(owner, owner_home):
    r = owner.post(f"/api/v1/homes/{owner_home}/cameras",
                   json={"name": "Darvoza kamerasi", "frigate_name": "gate_cam"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


def test_create_and_list(owner, owner_home, cam):
    assert cam["frigate_name"] == "gate_cam"
    status = cam["status"]
    assert set(status) == {"stream_available", "recording", "disk_usage_pct"}
    assert all(v["quality"] == "unknown" for v in status.values())
    lst = owner.get(f"/api/v1/homes/{owner_home}/cameras").json()
    assert lst["meta"]["total"] == 1
    assert owner.post(f"/api/v1/homes/{owner_home}/cameras",
                      json={"name": "x", "frigate_name": "gate_cam"}).status_code == 409


def test_status_from_hub_report(owner, owner_home, cam, hub):
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    v = lambda x: {"value": x, "source": "reported", "quality": "good", "ts": ts}  # noqa: E731
    r = hub.post("/api/v1/hub/report", json={"schema": 1, "ts": ts, "devices": [{
        "device_key": "cam_gate_cam", "availability": "online", "states": {"camera": {
            "stream_available": v(True), "recording": v(True), "disk_usage_pct": v(42.5)}}}]})
    assert r.json()["data"]["devices"][0]["result"] == "ok"
    c = owner.get(f"/api/v1/homes/{owner_home}/cameras").json()["data"][0]
    assert c["status"]["disk_usage_pct"]["value"] == 42.5


def test_access_links_and_permissions(owner, owner_home, cam, hub, make_member, outsider):
    r = owner.get(f"/api/v1/cameras/{cam['id']}/access")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["links"] == {"tailscale": "https://hub.tail1234.ts.net:8971/",
                          "lan": "https://hub.local:8971/"}
    assert d["archive_allowed"] is True
    admin = make_member("admin")
    assert admin.get(f"/api/v1/cameras/{cam['id']}/access").status_code == 200
    # family: camera_live is "configurable" (ARCHITECTURE 9) and defaults to deny
    for role in ("family", "guest", "viewer"):
        assert make_member(role).get(f"/api/v1/cameras/{cam['id']}/access").status_code == 403
    assert outsider.get(f"/api/v1/cameras/{cam['id']}/access").status_code == 404


def test_no_hub_hosts_means_no_links(owner, owner_home, cam):
    d = owner.get(f"/api/v1/cameras/{cam['id']}/access").json()["data"]
    assert d["links"] == {}


def test_delete_camera_removes_device(owner, owner_home, cam):
    assert owner.delete(f"/api/v1/cameras/{cam['id']}").status_code == 200
    assert owner.get(f"/api/v1/devices/{cam['device_id']}").status_code == 404


# ---- ADR 0006: video never reaches the cloud -----------------------------------------

VIDEOISH = re.compile(r"(video|snapshot|clip|image|frame|jpeg|jpg|mp4|thumbnail|blob)", re.I)


def test_schema_has_no_binary_or_video_columns():
    for table in Base.metadata.tables.values():
        for col in table.columns:
            assert not isinstance(col.type, LargeBinary), f"{table.name}.{col.name}"
            assert not VIDEOISH.search(col.name), f"{table.name}.{col.name}"


def test_api_accepts_no_uploads(client):
    spec = client.get("/api/v1/openapi.json").json()
    for path, ops in spec["paths"].items():
        for method, op in ops.items():
            content = (op.get("requestBody") or {}).get("content", {})
            for ctype in content:
                assert ctype == "application/json", f"{method.upper()} {path} accepts {ctype}"
            assert not VIDEOISH.search(path), path


def test_no_video_check_db_and_files(database, tmp_path):
    from app.jobs.no_video_check import db_findings, file_findings
    assert db_findings(database.engine) == []
    clean = tmp_path / "web"
    clean.mkdir()
    (clean / "icon-192.png").write_bytes(b"\x89PNG....")
    (clean / "index.html").write_text("<html></html>")
    assert file_findings([str(clean)]) == []
    (clean / "clip.mp4").write_bytes(b"x")
    (clean / "renamed.dat").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (clean / "snap.txt").write_bytes(b"\xff\xd8\xff\xe0JFIF")
    found = file_findings([str(clean)])
    assert len(found) == 3
