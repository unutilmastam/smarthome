from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import create_access_token
from app.models import AuditLog, AuthSession, User
from conftest import PASSWORD, Api, login

LOGIN = "/api/v1/auth/login"


def test_login_success_returns_tokens(client, owner_home):
    data = login(client, "owner@example.com")
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "owner@example.com"
    assert data["access_expires_at"].endswith("Z")
    me = Api(client, data["access_token"]).get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["data"]["has_pin"] is False


def test_email_is_case_insensitive(client, owner_home):
    r = client.post(LOGIN, json={"email": "  Owner@Example.COM ", "password": PASSWORD})
    assert r.status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(client, owner_home):
    a = client.post(LOGIN, json={"email": "owner@example.com", "password": "wrong-password"})
    b = client.post(LOGIN, json={"email": "nobody@example.com", "password": "wrong-password"})
    assert a.status_code == b.status_code == 401
    assert a.json()["error"] == b.json()["error"]
    assert a.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_refresh_stores_only_hash(client, owner_home, dbs):
    data = login(client, "owner@example.com")
    secret = data["refresh_token"].split(".", 1)[1]
    s = dbs.scalars(select(AuthSession)).one()
    assert secret not in s.refresh_hash and len(s.refresh_hash) == 64


def test_account_lock_after_five_failures(client, owner_home, dbs):
    for _ in range(5):
        r = client.post(LOGIN, json={"email": "owner@example.com", "password": "bad-password"})
        assert r.status_code == 401
    r = client.post(LOGIN, json={"email": "owner@example.com", "password": PASSWORD})
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "RATE_LIMITED"
    assert int(r.headers["Retry-After"]) > 0
    # After the lock expires the correct password works again.
    user = dbs.scalar(select(User).where(User.email == "owner@example.com"))
    user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    dbs.commit()
    assert client.post(LOGIN, json={"email": "owner@example.com",
                                    "password": PASSWORD}).status_code == 200
    actions = set(dbs.scalars(select(AuditLog.action)).all())
    assert {"auth.login.failure", "auth.account.locked", "auth.login.locked"} <= actions


def test_ip_rate_limit(client, owner_home):
    codes = [
        client.post(LOGIN, json={"email": f"x{i}@example.com", "password": "nope"}).status_code
        for i in range(21)
    ]
    assert codes[:20] == [401] * 20
    assert codes[20] == 429


def test_refresh_rotation(client, owner_home):
    first = login(client, "owner@example.com")
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 200
    second = r.json()["data"]
    assert second["refresh_token"] != first["refresh_token"]
    assert Api(client, second["access_token"]).get("/api/v1/auth/me").status_code == 200


def test_refresh_reuse_revokes_all_sessions(client, owner_home):
    other = login(client, "owner@example.com")  # another device
    first = login(client, "owner@example.com")
    rotated = client.post("/api/v1/auth/refresh",
                          json={"refresh_token": first["refresh_token"]}).json()["data"]
    # Attacker replays the old refresh token.
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert r.status_code == 401
    # Every session of the user is gone, including the legitimate rotated one.
    for tok in (rotated["access_token"], other["access_token"]):
        assert Api(client, tok).get("/api/v1/auth/me").status_code == 401
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]})
    assert r.status_code == 401


def test_garbage_refresh_token(client, owner_home):
    for tok in ("not-a-token-at-all", "123.abcdefghijk", "00000000-0000-0000-0000-000000000000.x"):
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": tok})
        assert r.status_code == 401


def test_logout_revokes_current_session_only(client, owner_home):
    a = login(client, "owner@example.com")
    b = login(client, "owner@example.com")
    assert Api(client, a["access_token"]).post("/api/v1/auth/logout").status_code == 200
    assert Api(client, a["access_token"]).get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/refresh",
                       json={"refresh_token": a["refresh_token"]}).status_code == 401
    assert Api(client, b["access_token"]).get("/api/v1/auth/me").status_code == 200


def test_logout_all(client, owner_home):
    a = login(client, "owner@example.com")
    b = login(client, "owner@example.com")
    r = Api(client, a["access_token"]).post("/api/v1/auth/logout-all")
    assert r.json()["data"]["sessions_revoked"] == 2
    for t in (a, b):
        assert Api(client, t["access_token"]).get("/api/v1/auth/me").status_code == 401


def test_password_change_revokes_other_sessions(client, owner_home):
    a = login(client, "owner@example.com")
    b = login(client, "owner@example.com")
    api = Api(client, a["access_token"])
    r = api.post("/api/v1/auth/password",
                 json={"current_password": "wrong-one", "new_password": "new-password-123"})
    assert r.status_code == 401
    r = api.post("/api/v1/auth/password",
                 json={"current_password": PASSWORD, "new_password": "new-password-123"})
    assert r.status_code == 200 and r.json()["data"]["other_sessions_revoked"] == 1
    assert api.get("/api/v1/auth/me").status_code == 200
    assert Api(client, b["access_token"]).get("/api/v1/auth/me").status_code == 401
    assert client.post(LOGIN, json={"email": "owner@example.com",
                                    "password": PASSWORD}).status_code == 401
    login(client, "owner@example.com", "new-password-123")


def test_password_too_short(owner):
    r = owner.post("/api/v1/auth/password",
                   json={"current_password": PASSWORD, "new_password": "short"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_set_pin(owner, dbs):
    assert owner.post("/api/v1/auth/pin", json={"password": PASSWORD, "pin": "12ab"}
                      ).status_code == 422
    assert owner.post("/api/v1/auth/pin", json={"password": "bad", "pin": "1234"}
                      ).status_code == 401
    assert owner.post("/api/v1/auth/pin", json={"password": PASSWORD, "pin": "4821"}
                      ).status_code == 200
    assert owner.get("/api/v1/auth/me").json()["data"]["has_pin"] is True
    user = dbs.scalar(select(User).where(User.email == "owner@example.com"))
    assert "4821" not in user.pin_hash and user.pin_hash.startswith("$argon2id$")


def test_missing_and_bad_tokens(client, owner_home, settings, dbs):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me").json()["error"]["code"] == "AUTH_REQUIRED"
    assert Api(client, "garbage").get("/api/v1/auth/me").status_code == 401
    data = login(client, "owner@example.com")
    s = dbs.scalars(select(AuthSession)).first()
    expired, _ = create_access_token(
        s.user_id, s.id, settings.jwt_secret,
        now=datetime.now(timezone.utc) - timedelta(minutes=16),
    )
    assert Api(client, expired).get("/api/v1/auth/me").status_code == 401
    forged, _ = create_access_token(s.user_id, s.id, "another-secret-another-secret-xx")
    assert Api(client, forged).get("/api/v1/auth/me").status_code == 401
    assert Api(client, data["access_token"]).get("/api/v1/auth/me").status_code == 200


def test_password_hash_is_argon2id(dbs, owner_home):
    user = dbs.scalar(select(User))
    assert user.password_hash.startswith("$argon2id$")
