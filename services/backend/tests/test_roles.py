import pytest

from app.core.permissions import PERMISSIONS, ROLE_PERMISSIONS, has_permission
from conftest import PASSWORD, Api, login

# ARCHITECTURE 9. Guest = view only until grants exist; family camera_live = deny by default.
EXPECTED = {
    "owner": set(PERMISSIONS),
    "admin": set(PERMISSIONS) - {"manage_users"},
    "family": {"view", "control_basic", "control_access"},
    "guest": {"view"},
    "viewer": {"view"},
}


@pytest.mark.parametrize("role", sorted(EXPECTED))
def test_permission_matrix(role):
    assert set(ROLE_PERMISSIONS[role]) == EXPECTED[role]
    for perm in PERMISSIONS:
        assert has_permission(role, perm) == (perm in EXPECTED[role])


def test_unknown_permission_raises():
    with pytest.raises(ValueError):
        has_permission("owner", "fly")


# role -> expected status for (create room, add member, view devices, read audit, list members)
API_MATRIX = {
    "admin": (201, 403, 200, 200, 200),
    "family": (403, 403, 200, 403, 403),
    "guest": (403, 403, 200, 403, 403),
    "viewer": (403, 403, 200, 403, 403),
}


@pytest.mark.parametrize("role", sorted(API_MATRIX))
def test_role_api_matrix(role, make_member, owner_home):
    api = make_member(role)
    h = f"/api/v1/homes/{owner_home}"
    got = (
        api.post(f"{h}/rooms", json={"name": "Oshxona"}).status_code,
        api.post(f"{h}/members", json={"email": "z@example.com", "role": "viewer",
                                       "name": "Z", "initial_password": PASSWORD}).status_code,
        api.get(f"{h}/devices").status_code,
        api.get(f"{h}/audit").status_code,
        api.get(f"{h}/members").status_code,
    )
    assert got == API_MATRIX[role]


def test_forbidden_error_shape(make_member, owner_home):
    r = make_member("viewer").post(f"/api/v1/homes/{owner_home}/rooms", json={"name": "X"})
    assert r.json()["error"]["code"] == "FORBIDDEN"
    assert r.json()["data"] is None


def test_cannot_create_second_owner(owner, owner_home):
    r = owner.post(f"/api/v1/homes/{owner_home}/members",
                   json={"email": "second@example.com", "role": "owner", "name": "S",
                         "initial_password": PASSWORD})
    assert r.status_code == 422


def test_cannot_promote_to_owner_or_touch_owner(owner, owner_home, make_member, client):
    make_member("family", "fam@example.com")
    members = owner.get(f"/api/v1/homes/{owner_home}/members").json()["data"]
    fam = next(m for m in members if m["email"] == "fam@example.com")
    own = next(m for m in members if m["role"] == "owner")
    base = f"/api/v1/homes/{owner_home}/members"
    assert owner.patch(f"{base}/{fam['user_id']}", json={"role": "owner"}).status_code == 422
    assert owner.patch(f"{base}/{own['user_id']}", json={"role": "viewer"}).status_code == 403
    assert owner.delete(f"{base}/{own['user_id']}").status_code == 403
    r = owner.patch(f"{base}/{fam['user_id']}", json={"role": "viewer"})
    assert r.status_code == 200 and r.json()["data"]["role"] == "viewer"
    assert owner.delete(f"{base}/{fam['user_id']}").status_code == 200
    # Removed member no longer sees the home.
    fam_api = Api(client, login(client, "fam@example.com")["access_token"])
    assert fam_api.get(f"/api/v1/homes/{owner_home}").status_code == 404


def test_admin_cannot_manage_members(make_member, owner_home, owner):
    admin = make_member("admin")
    make_member("viewer", "v@example.com")
    members = owner.get(f"/api/v1/homes/{owner_home}/members").json()["data"]
    v = next(m for m in members if m["email"] == "v@example.com")
    base = f"/api/v1/homes/{owner_home}/members/{v['user_id']}"
    assert admin.patch(base, json={"role": "admin"}).status_code == 403
    assert admin.delete(base).status_code == 403


def test_add_existing_user_and_duplicates(owner, owner_home, outsider):
    base = f"/api/v1/homes/{owner_home}/members"
    # Existing user: no password may be set by the owner.
    r = owner.post(base, json={"email": "outsider@example.com", "role": "viewer",
                               "initial_password": PASSWORD})
    assert r.status_code == 422
    r = owner.post(base, json={"email": "outsider@example.com", "role": "viewer"})
    assert r.status_code == 201
    r = owner.post(base, json={"email": "outsider@example.com", "role": "viewer"})
    assert r.status_code == 409
    # New user without initial password.
    r = owner.post(base, json={"email": "new@example.com", "role": "viewer", "name": "N"})
    assert r.status_code == 422


def test_any_user_can_create_own_home_and_becomes_owner(outsider):
    r = outsider.post("/api/v1/homes", json={"name": "Dacha"})
    assert r.status_code == 201
    assert r.json()["data"]["my_role"] == "owner"
    homes = outsider.get("/api/v1/homes").json()
    assert homes["meta"]["total"] == 2


def test_matrix_matches_contracts_roles_json(settings):
    import json
    roles = json.loads((settings.contracts_dir / "roles.json").read_text())
    assert {r: set(p) for r, p in roles["roles"].items()} == \
        {r: set(p) for r, p in ROLE_PERMISSIONS.items()}
    assert tuple(roles["permissions"]) == PERMISSIONS
