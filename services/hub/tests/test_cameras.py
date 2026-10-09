"""Phase 10 [SIM]: Frigate status -> camera capability in the cloud. No video ever."""

import asyncio

import httpx

from gateway.frigate import FrigateMonitor, parse
from test_integration import Stack, run

STATS = {"cameras": {"gate_cam": {"camera_fps": 5.0}, "yard_cam": {"camera_fps": 0.0}},
         "service": {"storage": {"/media/frigate/recordings": {"total": 1000.0, "used": 900.0}}}}
CONFIG = {"cameras": {"gate_cam": {"record": {"enabled": True}},
                      "yard_cam": {"record": {"enabled": False}},
                      "new_cam": {"record": {"enabled": True}}}}


def test_parse_never_assumes_streaming():
    snap = parse(STATS, CONFIG)
    assert snap["cameras"]["gate_cam"] == {"stream_available": True, "recording": True}
    assert snap["cameras"]["yard_cam"] == {"stream_available": False, "recording": False}
    assert snap["cameras"]["new_cam"]["stream_available"] is None   # no stats -> unknown
    assert snap["disk_usage_pct"] == 90.0
    assert parse({}, {})["disk_usage_pct"] is None


class FakeFrigate:
    def __init__(self):
        self.up = True
        self.paths = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.paths.append(request.url.path)
        if not self.up:
            raise httpx.ConnectError("frigate down")
        return httpx.Response(200, json=STATS if request.url.path == "/api/stats" else CONFIG)


def test_camera_status_reaches_cloud_and_frigate_down_is_unknown(broker, tmp_path):
    st = Stack(broker, tmp_path, frigate_poll_s=0.3)
    for name in ("gate_cam", "yard_cam"):
        r = st.phone.post(f"/api/v1/homes/{st.home_id}/cameras",
                          json={"name": name, "frigate_name": name})
        assert r.status_code == 201, r.text
    fake = FakeFrigate()
    st.gateway.frigate = FrigateMonitor(
        "http://frigate:5000", client=httpx.AsyncClient(transport=httpx.MockTransport(fake.handler)))

    def cams():
        return {c["frigate_name"]: c for c in
                st.phone.get(f"/api/v1/homes/{st.home_id}/cameras").json()["data"]}

    async def scenario(st):
        await st.wait(lambda: cams()["gate_cam"]["status"]["recording"]["quality"] == "good",
                      "camera status in backend")
        c = cams()
        assert c["gate_cam"]["availability"]["status"] == "online"
        assert c["gate_cam"]["status"]["stream_available"]["value"] is True
        assert c["gate_cam"]["status"]["disk_usage_pct"]["value"] == 90.0
        assert c["yard_cam"]["availability"]["status"] == "offline"
        assert st.gateway.health()["disk_warning"] is True
        # Only status endpoints were ever read from Frigate (no media).
        assert set(fake.paths) <= {"/api/stats", "/api/config"}
        fake.up = False
        await st.wait(lambda: cams()["gate_cam"]["availability"]["status"] == "unknown",
                      "frigate down -> unknown")
        assert st.gateway.health()["frigate_ok"] is False
        await asyncio.sleep(0)
    run(st, scenario)


def test_heartbeat_reports_hosts_for_camera_links(broker, tmp_path):
    st = Stack(broker, tmp_path, tailnet_host="hub.tail1234.ts.net", lan_host="hub.local")
    r = st.phone.post(f"/api/v1/homes/{st.home_id}/cameras",
                      json={"name": "Darvoza", "frigate_name": "gate_cam"})
    cam_id = r.json()["data"]["id"]

    async def scenario(st):
        await st.wait(lambda: st.phone.get(f"/api/v1/cameras/{cam_id}/access").json()["data"]
                      ["links"].get("tailscale"), "links from heartbeat")
        links = st.phone.get(f"/api/v1/cameras/{cam_id}/access").json()["data"]["links"]
        assert links == {"tailscale": "https://hub.tail1234.ts.net:8971/",
                         "lan": "https://hub.local:8971/"}
    run(st, scenario)
