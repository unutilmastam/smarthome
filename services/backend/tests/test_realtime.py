import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import ConfigError, Settings
from app.main import create_app
from app.services.realtime import EmqxServerless
from conftest import PASSWORD, Api, login


class FakeEmqx:
    """Records requests; behaves like the EMQX HTTP API."""

    def __init__(self, fail=False):
        self.requests = []
        self.fail = fail
        self.users = set()

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, body,
                              request.headers.get("authorization")))
        if self.fail:
            return httpx.Response(503, json={"code": "UNAVAILABLE"})
        path = request.url.path
        if "/users/" in path and request.method == "PUT" and "rules" not in path:
            name = path.rsplit("/", 1)[1]
            return httpx.Response(200 if name in self.users else 404, json={})
        if path.endswith("/users") and request.method == "POST" and "rules" not in path:
            self.users.add(body["user_id"])
            return httpx.Response(201, json={})
        if "/rules/users/" in path and request.method == "PUT":
            return httpx.Response(404, json={})
        return httpx.Response(200, json={})

    def realtime(self):
        client = httpx.Client(transport=httpx.MockTransport(self.handler))
        return EmqxServerless("https://broker.example/api", "app-id", "app-secret",
                              client=client)


@pytest.fixture
def emqx():
    return FakeEmqx()


@pytest.fixture
def rt_client(settings, database, emqx):
    with TestClient(create_app(settings, database, emqx.realtime())) as c:
        yield c


@pytest.fixture
def rt_owner(rt_client, owner_home):
    return Api(rt_client, login(rt_client, "owner@example.com")["access_token"])


@pytest.fixture
def online_hub(rt_client, rt_owner, owner_home):
    data = rt_owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "h"}).json()["data"]
    Api(rt_client, data["hub_token"]).post("/api/v1/hub/heartbeat", json={})
    return data


LIGHT = {"key": "lamp", "name": "Lamp", "adapter": "esphome", "protocol": "mqtt",
         "capabilities": {"switch": {}}}


def _light(api, home):
    return api.post(f"/api/v1/homes/{home}/devices", json=LIGHT).json()["data"]


def test_publish_request_shape(emqx):
    emqx.realtime().publish("sh/v1/h/cmd", {"a": 1}, qos=1)
    method, path, body, auth = emqx.requests[0]
    assert (method, path) == ("POST", "/api/publish")
    assert body == {"topic": "sh/v1/h/cmd", "payload": '{"a":1}', "qos": 1, "retain": False}
    assert auth.startswith("Basic ")


def test_command_is_published_to_broker(rt_owner, owner_home, online_hub, emqx):
    light = _light(rt_owner, owner_home)
    r = rt_owner.post("/api/v1/commands", json={
        "device_id": light["id"], "capability": "switch", "action": "turn_on", "params": {},
        "idempotency_key": uuid.uuid4().hex})
    assert r.status_code == 201
    pubs = [b for m, p, b, _ in emqx.requests if p == "/api/publish"]
    assert len(pubs) == 1
    assert pubs[0]["topic"] == f"sh/v1/{owner_home}/cmd"
    env = json.loads(pubs[0]["payload"])
    assert env["payload"]["command_id"] == r.json()["data"]["id"]
    assert len(env["signature"]) == 64


def test_broker_failure_never_blocks_commands(settings, database, owner_home):
    bad = FakeEmqx(fail=True)
    with TestClient(create_app(settings, database, bad.realtime())) as c:
        api = Api(c, login(c, "owner@example.com")["access_token"])
        hub = api.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "h"}).json()["data"]
        hub_api = Api(c, hub["hub_token"])
        hub_api.post("/api/v1/hub/heartbeat", json={})
        light = _light(api, owner_home)
        r = api.post("/api/v1/commands", json={
            "device_id": light["id"], "capability": "switch", "action": "turn_on",
            "params": {}, "idempotency_key": uuid.uuid4().hex})
        assert r.status_code == 201
        cid = r.json()["data"]["id"]
        events = api.get(f"/api/v1/commands/{cid}").json()["data"]["events"]
        assert any("polling will deliver" in (e["detail"] or "") for e in events)
        # Polling still delivers it.
        got = hub_api.get("/api/v1/hub/commands").json()["data"]
        assert [e["payload"]["command_id"] for e in got] == [cid]


def test_credentials_disabled_means_polling(owner):
    r = owner.get("/api/v1/realtime/credentials")
    assert r.status_code == 200
    assert r.json()["data"] == {"enabled": False, "transport": "polling", "poll_interval_s": 3}


def test_credentials_are_read_only_and_scoped(rt_owner, rt_client, owner_home, emqx, dbs):
    from app.cli import create_owner
    other = create_owner(dbs, "x@example.com", "X", PASSWORD, "Boshqa uy")
    r = rt_owner.get("/api/v1/realtime/credentials")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["enabled"] and d["read_only"] and d["username"].startswith("app-")
    assert d["topics"] == [f"sh/v1/{owner_home}/#"]
    acl = [b for m, p, b, _ in emqx.requests if "rules" in p][-1]
    rules = acl[0]["rules"] if isinstance(acl, list) else acl["rules"]
    assert {"topic": f"sh/v1/{owner_home}/#", "permission": "allow",
            "action": "subscribe"} in rules
    assert rules[-1] == {"topic": "#", "permission": "deny", "action": "all"}
    assert not any(r_["action"] in ("publish", "all") and r_["permission"] == "allow"
                   for r_ in rules)
    assert all(str(other.id) not in r_["topic"] for r_ in rules)
    # Password rotates on every call.
    d2 = rt_owner.get("/api/v1/realtime/credentials").json()["data"]
    assert d2["password"] != d["password"] and d2["username"] == d["username"]


def test_credentials_broker_down_is_503_with_polling_hint(settings, database, owner_home):
    bad = FakeEmqx(fail=True)
    with TestClient(create_app(settings, database, bad.realtime())) as c:
        api = Api(c, login(c, "owner@example.com")["access_token"])
        r = api.get("/api/v1/realtime/credentials")
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "REALTIME_UNAVAILABLE"
        assert r.json()["error"]["details"]["transport"] == "polling"


def test_production_requires_complete_emqx_config():
    import secrets
    base = dict(_env_file=None, env="production",
                database_url="postgresql+psycopg://u:p@h/db",
                jwt_secret=secrets.token_hex(32), signing_master_key=secrets.token_hex(32))
    with pytest.raises((ConfigError, ValueError)):
        Settings(**base, realtime_provider="emqx_serverless")
    with pytest.raises((ConfigError, ValueError)):
        Settings(**base, realtime_provider="emqx_serverless", emqx_api_base="https://x/api",
                 emqx_app_id="a", emqx_app_secret="b", realtime_wss_url="ws://insecure")
    with pytest.raises(ValueError):
        Settings(**base, realtime_provider="hivemq")
    ok = Settings(**base, realtime_provider="emqx_serverless", emqx_api_base="https://x/api",
                  emqx_app_id="a", emqx_app_secret="b", realtime_wss_url="wss://x:8084/mqtt")
    assert ok.realtime_provider == "emqx_serverless"
