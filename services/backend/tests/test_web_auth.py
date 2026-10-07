"""ADR 0009: PWA keeps the refresh token in an HttpOnly cookie."""

import secrets

import pytest

from app.core.config import ConfigError, Settings
from conftest import PASSWORD, Api

WEB = {"X-Client": "web"}


def web_login(client):
    return client.post("/api/v1/auth/login", headers=WEB,
                       json={"email": "owner@example.com", "password": PASSWORD})


def test_web_login_sets_httponly_cookie_and_hides_token(client, owner_home):
    r = web_login(client)
    assert r.status_code == 200
    assert "refresh_token" not in r.json()["data"]
    cookie = r.headers["set-cookie"]
    assert cookie.startswith("sh_refresh=")
    low = cookie.lower()
    assert "httponly" in low and "samesite=strict" in low and "path=/api/v1/auth" in low


def test_web_refresh_uses_cookie_and_rotates(client, owner_home):
    web_login(client)
    first = client.cookies.get("sh_refresh")
    r = client.post("/api/v1/auth/refresh", headers=WEB)
    assert r.status_code == 200, r.text
    assert "refresh_token" not in r.json()["data"]
    assert client.cookies.get("sh_refresh") != first
    me = Api(client, r.json()["data"]["access_token"]).get("/api/v1/auth/me")
    assert me.status_code == 200


def test_cookie_ignored_without_web_header(client, owner_home):
    web_login(client)
    r = client.post("/api/v1/auth/refresh")  # cookie present, header missing (CSRF guard)
    assert r.status_code == 401


def test_logout_clears_cookie(client, owner_home):
    access = web_login(client).json()["data"]["access_token"]
    r = Api(client, access).post("/api/v1/auth/logout")
    assert 'sh_refresh=""' in r.headers["set-cookie"] or "max-age=0" in \
        r.headers["set-cookie"].lower()
    assert client.post("/api/v1/auth/refresh", headers=WEB).status_code == 401


def test_secure_flag_and_production_rule(settings):
    base = dict(_env_file=None, env="production", database_url="postgresql+psycopg://u:p@h/d",
                jwt_secret=secrets.token_hex(32), signing_master_key=secrets.token_hex(32))
    with pytest.raises((ConfigError, ValueError)):
        Settings(**base, cookie_secure=False)
    assert Settings(**base).cookie_secure is True


def test_sessions_list_and_revoke(client, owner_home):
    a = client.post("/api/v1/auth/login", json={"email": "owner@example.com",
                                                "password": PASSWORD}).json()["data"]
    b = client.post("/api/v1/auth/login", json={"email": "owner@example.com",
                                                "password": PASSWORD}).json()["data"]
    api = Api(client, a["access_token"])
    sessions = api.get("/api/v1/auth/sessions").json()["data"]
    assert len(sessions) == 2 and sum(s["current"] for s in sessions) == 1
    other = next(s for s in sessions if not s["current"])
    assert api.delete(f"/api/v1/auth/sessions/{other['id']}").status_code == 200
    assert Api(client, b["access_token"]).get("/api/v1/auth/me").status_code == 401
    assert api.delete(f"/api/v1/auth/sessions/{other['id']}").status_code == 404


def test_cannot_revoke_someone_elses_session(client, owner_home, outsider):
    mine = Api(client, client.post("/api/v1/auth/login", json={
        "email": "owner@example.com", "password": PASSWORD}).json()["data"]["access_token"])
    sid = mine.get("/api/v1/auth/sessions").json()["data"][0]["id"]
    assert outsider.delete(f"/api/v1/auth/sessions/{sid}").status_code == 404
