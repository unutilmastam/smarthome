"""[SIM] A fake Yandex Smart Home API for the e2e stack (ADR 0016): one Alisa lamp that
really changes when switched, a Yandex TV and a scenario. Usage: fake_yandex.py PORT"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = "y0_e2e_fake_token_not_secret_0000"
LAMP, TV = "11111111-2222-3333-4444-555555555555", "22222222-2222-3333-4444-555555555555"
state = {"lamp": False, "volume": 12}


def device(yid):
    if yid == LAMP:
        return {"id": LAMP, "name": "Alisa chirog'i", "type": "devices.types.light", "state": "online",
                "capabilities": [{"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": state["lamp"]}}],
                "properties": []}
    return {"id": TV, "name": "Yandex TV", "type": "devices.types.media_device.tv", "state": "online",
            "capabilities": [{"type": "devices.capabilities.on_off", "state": {"instance": "on", "value": True}},
                             {"type": "devices.capabilities.range", "state": {"instance": "volume", "value": state["volume"]}},
                             {"type": "devices.capabilities.range", "state": {"instance": "channel", "value": 5}}],
            "properties": []}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def ok_auth(self):
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send(401, {"status": "error", "message": "unauthorized"})
            return False
        return True

    def do_GET(self):
        if not self.ok_auth():
            return
        if self.path.endswith("/user/info"):
            return self.send(200, {"status": "ok", "rooms": [], "devices": [device(LAMP), device(TV)],
                                   "scenarios": [{"id": "sc1", "name": "Kino rejimi", "is_active": True}]})
        return self.send(200, {"status": "ok", **device(self.path.rsplit("/", 1)[1])})

    def do_POST(self):
        if not self.ok_auth():
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path.endswith("/devices/actions"):
            d = body["devices"][0]
            act = d["actions"][0]
            if d["id"] == LAMP and act["type"].endswith("on_off"):
                state["lamp"] = act["state"]["value"]
            if d["id"] == TV and act["state"]["instance"] == "volume":
                st = act["state"]
                state["volume"] = max(0, min(100, state["volume"] + st["value"] if st.get("relative") else st["value"]))
            return self.send(200, {"status": "ok", "devices": [{"id": d["id"], "capabilities": [
                {"type": act["type"], "state": {"instance": act["state"]["instance"], "action_result": {"status": "DONE"}}}]}]})
        return self.send(200, {"status": "ok"})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
