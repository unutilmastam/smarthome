import os
import uuid

import pytest

# Tests must never pick up a developer's .env or production settings.
os.environ["ENV"] = "test"
for _k in ("DATABASE_URL", "JWT_SECRET", "SIGNING_MASTER_KEY"):
    os.environ.pop(_k, None)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import app.models  # noqa: E402,F401
from app.cli import create_owner  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import Database, make_engine  # noqa: E402
from app.main import create_app  # noqa: E402

PG_URL = os.environ.get("TEST_POSTGRES_URL")
BACKENDS = ["sqlite"] + (["postgres"] if PG_URL else [])
PASSWORD = "correct-horse-battery"


def _engine(kind, tmp_path):
    if kind == "sqlite":
        return make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    engine = make_engine(PG_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    return engine


@pytest.fixture(params=BACKENDS)
def backend(request):
    return request.param


@pytest.fixture
def settings():
    return Settings(_env_file=None, env="test", cookie_secure=False)


@pytest.fixture
def database(backend, settings, tmp_path):
    engine = _engine(backend, tmp_path)
    Base.metadata.create_all(engine)
    db = Database(settings, engine=engine)
    yield db
    engine.dispose()


@pytest.fixture
def client(settings, database):
    with TestClient(create_app(settings, database)) as c:
        yield c


@pytest.fixture
def dbs(database):
    s = database.sessionmaker()
    yield s
    s.close()


class Api:
    """Small helper around TestClient for authenticated calls."""

    def __init__(self, client, token=None):
        self.c = client
        self.token = token

    def _h(self, headers=None):
        h = dict(headers or {})
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get(self, url, **kw):
        return self.c.get(url, headers=self._h(kw.pop("headers", None)), **kw)

    def post(self, url, json=None, **kw):
        return self.c.post(url, json=json, headers=self._h(kw.pop("headers", None)), **kw)

    def patch(self, url, json=None, **kw):
        return self.c.patch(url, json=json, headers=self._h(kw.pop("headers", None)), **kw)

    def delete(self, url, **kw):
        return self.c.delete(url, headers=self._h(kw.pop("headers", None)), **kw)


def login(client, email, password=PASSWORD):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["data"]


@pytest.fixture
def owner_home(dbs):
    home = create_owner(dbs, "owner@example.com", "Owner", PASSWORD, "Uy")
    return home.id


@pytest.fixture
def owner(client, owner_home):
    tokens = login(client, "owner@example.com")
    return Api(client, tokens["access_token"])


@pytest.fixture
def make_member(client, owner, owner_home):
    def make(role, email=None):
        email = email or f"{role}-{uuid.uuid4().hex[:6]}@example.com"
        r = owner.post(f"/api/v1/homes/{owner_home}/members",
                       json={"email": email, "role": role, "name": role,
                             "initial_password": PASSWORD})
        assert r.status_code == 201, r.text
        return Api(client, login(client, email)["access_token"])
    return make


@pytest.fixture
def outsider(client, dbs):
    create_owner(dbs, "outsider@example.com", "Out", PASSWORD, "Other home")
    return Api(client, login(client, "outsider@example.com")["access_token"])


LIGHT = {
    "key": "garden_lights",
    "name": "Bog' chiroqlari",
    "adapter": "esphome",
    "protocol": "mqtt",
    "capabilities": {"switch": {}, "dimmer": {}},
}


@pytest.fixture
def light(owner, owner_home):
    r = owner.post(f"/api/v1/homes/{owner_home}/devices", json=LIGHT)
    assert r.status_code == 201, r.text
    return r.json()["data"]
