"""Resources of homes the user is not a member of answer 404, never 403."""

import uuid

import pytest


@pytest.fixture
def room(owner, owner_home):
    return owner.post(f"/api/v1/homes/{owner_home}/rooms", json={"name": "Zal"}).json()["data"]


@pytest.fixture
def floor(owner, owner_home):
    return owner.post(f"/api/v1/homes/{owner_home}/floors", json={"name": "1-qavat"}
                      ).json()["data"]


@pytest.fixture
def hub(owner, owner_home):
    return owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "hub"}).json()["data"]


def test_outsider_gets_404_everywhere(outsider, owner_home, light, room, floor, hub):
    h = f"/api/v1/homes/{owner_home}"
    calls = [
        ("get", h, None),
        ("patch", h, {"name": "x"}),
        ("get", f"{h}/members", None),
        ("post", f"{h}/members", {"email": "a@example.com", "role": "viewer"}),
        ("get", f"{h}/floors", None),
        ("post", f"{h}/floors", {"name": "x"}),
        ("get", f"{h}/rooms", None),
        ("post", f"{h}/rooms", {"name": "x"}),
        ("get", f"{h}/devices", None),
        ("post", f"{h}/devices", {"key": "k_x", "name": "x", "adapter": "a", "protocol": "p",
                                  "capabilities": {"switch": {}}}),
        ("get", f"{h}/hubs", None),
        ("post", f"{h}/hubs", {"name": "x"}),
        ("get", f"{h}/audit", None),
        ("get", f"/api/v1/devices/{light['id']}", None),
        ("patch", f"/api/v1/devices/{light['id']}", {"name": "x"}),
        ("delete", f"/api/v1/devices/{light['id']}", None),
        ("get", f"/api/v1/rooms/{room['id']}", None),
        ("patch", f"/api/v1/rooms/{room['id']}", {"name": "x"}),
        ("delete", f"/api/v1/rooms/{room['id']}", None),
        ("patch", f"/api/v1/floors/{floor['id']}", {"name": "x"}),
        ("delete", f"/api/v1/floors/{floor['id']}", None),
        ("post", f"/api/v1/hubs/{hub['id']}/revoke", None),
    ]
    for method, url, body in calls:
        kw = {"json": body} if body is not None and method != "get" else {}
        r = getattr(outsider, method)(url, **kw)
        assert r.status_code == 404, (method, url, r.status_code)
        assert r.json()["error"]["code"] == "NOT_FOUND"


def test_random_ids_are_404(owner):
    rid = uuid.uuid4()
    for url in (f"/api/v1/homes/{rid}", f"/api/v1/devices/{rid}", f"/api/v1/rooms/{rid}"):
        assert owner.get(url).status_code == 404


def test_cannot_attach_room_from_other_home(owner, owner_home, outsider):
    other_home = outsider.get("/api/v1/homes").json()["data"][0]["id"]
    other_room = outsider.post(f"/api/v1/homes/{other_home}/rooms", json={"name": "R"}
                               ).json()["data"]
    body = {"key": "lamp", "name": "Lamp", "adapter": "esphome", "protocol": "mqtt",
            "capabilities": {"switch": {}}, "room_id": other_room["id"]}
    r = owner.post(f"/api/v1/homes/{owner_home}/devices", json=body)
    assert r.status_code == 422
