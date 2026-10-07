import uuid

from sqlalchemy import select

from app.core.security import sha256_hex
from app.core.signing import derive_home_key
from app.models import Hub


def test_create_hub_returns_secrets_once(owner, owner_home, dbs, settings):
    r = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "Asosiy hub"})
    assert r.status_code == 201
    data = r.json()["data"]
    token, key = data["hub_token"], data["signing_key_hex"]
    assert token.startswith("hub_") and len(key) == 64
    assert key == derive_home_key(settings.signing_master_key, owner_home).hex()
    hub = dbs.get(Hub, uuid.UUID(data["id"]))
    assert hub.token_hash == sha256_hex(token)
    # Neither secret is stored or returned again.
    listing = owner.get(f"/api/v1/homes/{owner_home}/hubs").json()["data"]
    assert "hub_token" not in listing[0] and "signing_key_hex" not in listing[0]
    assert listing[0]["online"] is False and listing[0]["last_seen"] is None


def test_signing_key_differs_per_home(settings):
    a = derive_home_key(settings.signing_master_key, uuid.uuid4())
    b = derive_home_key(settings.signing_master_key, uuid.uuid4())
    assert a != b


def test_one_active_hub_per_home_and_revoke(owner, owner_home, dbs):
    url = f"/api/v1/homes/{owner_home}/hubs"
    first = owner.post(url, json={"name": "a"}).json()["data"]
    assert owner.post(url, json={"name": "b"}).status_code == 409
    r = owner.post(f"/api/v1/hubs/{first['id']}/revoke")
    assert r.status_code == 200 and r.json()["data"]["status"] == "revoked"
    assert owner.post(url, json={"name": "b"}).status_code == 201
    assert len(dbs.scalars(select(Hub)).all()) == 2


def test_family_cannot_create_hub(make_member, owner_home):
    fam = make_member("family")
    assert fam.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "x"}).status_code == 403
