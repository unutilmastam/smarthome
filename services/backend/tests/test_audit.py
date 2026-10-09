from sqlalchemy import select

from app.models import AuditLog


def test_audit_records_changes(owner, owner_home, light, dbs):
    owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "hub"})
    owner.patch(f"/api/v1/devices/{light['id']}", json={"name": "Yangi nom"})
    actions = [a.action for a in dbs.scalars(select(AuditLog)).all()]
    for expected in ("home.created", "auth.login.success", "device.created", "hub.created",
                     "device.updated"):
        assert expected in actions
    r = owner.get(f"/api/v1/homes/{owner_home}/audit")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] >= 4
    assert body["data"][0]["ts"].endswith("Z")


def test_audit_has_no_write_api(owner, owner_home):
    url = f"/api/v1/homes/{owner_home}/audit"
    assert owner.delete(url).status_code == 405
    assert owner.post(url, json={}).status_code == 405
    assert owner.patch(url, json={}).status_code == 405


def test_audit_never_contains_secrets(owner, owner_home, dbs):
    data = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "hub"}).json()["data"]
    for a in dbs.scalars(select(AuditLog)).all():
        blob = repr(a.details)
        assert data["hub_token"] not in blob and data["signing_key_hex"] not in blob
