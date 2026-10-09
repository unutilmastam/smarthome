"""Phase 7: things the cPanel deployment depends on."""

import io
import json
import secrets
import sys
import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings
from app.db.types import utcnow
from app.jobs import expire_due, retention
from app.main import create_app
from app.models import AuthSession, Command, RateLimitHit
from conftest import LIGHT, Api


def _call(app, environ_extra):
    status = {}

    def start_response(s, headers, exc_info=None):
        status["s"] = s
    environ = {
        "REQUEST_METHOD": "GET", "QUERY_STRING": "", "SERVER_NAME": "home.example.uz",
        "SERVER_PORT": "443", "SERVER_PROTOCOL": "HTTP/1.1", "wsgi.url_scheme": "https",
        "wsgi.input": io.BytesIO(b""), "wsgi.errors": sys.stderr, "wsgi.version": (1, 0),
        "wsgi.multithread": False, "wsgi.multiprocess": True, "wsgi.run_once": False,
        **environ_extra,
    }
    body = b"".join(app(environ, start_response))
    return status["s"], body


def test_passenger_restores_api_prefix():
    import passenger_wsgi
    # Mounted at Application URL /api: Passenger strips the prefix.
    s, body = _call(passenger_wsgi.application, {"SCRIPT_NAME": "/api", "PATH_INFO": "/v1/health"})
    assert s.startswith("200") and json.loads(body)["data"]["status"] == "ok"
    # Mounted at the domain root: nothing to restore.
    s, _ = _call(passenger_wsgi.application, {"SCRIPT_NAME": "", "PATH_INFO": "/api/v1/health"})
    assert s.startswith("200")


def test_docs_are_off_in_production(database):
    prod = Settings(_env_file=None, env="production",
                    database_url="postgresql+psycopg://u:p@h/d",
                    jwt_secret=secrets.token_hex(32), signing_master_key=secrets.token_hex(32))
    assert prod.docs_enabled is False
    with TestClient(create_app(prod, database)) as c:
        assert c.get("/api/v1/docs").status_code == 404
        assert c.get("/api/v1/openapi.json").status_code == 404
        assert c.get("/api/v1/health").status_code == 200


def test_expire_due_job(owner, owner_home, client, dbs, settings):
    from app.core.contracts import load_contracts
    light = owner.post(f"/api/v1/homes/{owner_home}/devices", json=LIGHT).json()["data"]
    hub = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "h"}).json()["data"]
    Api(client, hub["hub_token"]).post("/api/v1/hub/heartbeat", json={})
    cid = owner.post("/api/v1/commands", json={
        "device_id": light["id"], "capability": "switch", "action": "turn_on", "params": {},
        "idempotency_key": uuid.uuid4().hex}).json()["data"]["id"]
    c = dbs.get(Command, uuid.UUID(cid))
    c.expires_at = utcnow() - timedelta(seconds=1)
    dbs.commit()
    assert expire_due.run(dbs, settings, load_contracts(str(settings.contracts_dir))) == 1
    dbs.refresh(c)
    assert c.status == "expired"


def test_retention_job(owner, dbs):
    old = utcnow() - timedelta(days=40)
    dbs.add(RateLimitHit(key="x", window_start=old, count=3))
    s = dbs.scalars(select(AuthSession)).first()
    s.revoked_at = old
    dbs.commit()
    out = retention.run(dbs)
    assert out["rate_limits"] >= 1 and out["auth_sessions"] == 1
    assert dbs.scalars(select(RateLimitHit).where(RateLimitHit.key == "x")).all() == []
