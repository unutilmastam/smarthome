import uuid
from datetime import timedelta

import pytest

from app.db.types import utcnow
from conftest import Api

TS = lambda d=timedelta(0): (utcnow() + d).strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731

GATE = {"key": "front_gate", "name": "Darvoza", "adapter": "esphome", "protocol": "mqtt",
        "capabilities": {"cover": {"left_open_after_s": 600}}}
ALARM = {"key": "security", "name": "Signalizatsiya", "adapter": "hub", "protocol": "virtual",
         "capabilities": {"alarm": {"zones": [
             {"device_key": "front_door", "capability": "contact", "mode": "entry"}],
             "sirens": ["siren"], "exit_delay_s": 30, "entry_delay_s": 20}}}


@pytest.fixture
def hub(client, owner, owner_home):
    data = owner.post(f"/api/v1/homes/{owner_home}/hubs", json={"name": "hub"}).json()["data"]
    return Api(client, data["hub_token"])


@pytest.fixture
def gate(owner, owner_home):
    r = owner.post(f"/api/v1/homes/{owner_home}/devices", json=GATE)
    assert r.status_code == 201, r.text
    return r.json()["data"]


def ev(type_="cover.left_open", key="front_gate", **kw):
    return {"id": str(uuid.uuid4()), "ts": TS(), "device_key": key, "type": type_,
            "severity": "warning", **kw}


def test_events_are_stored_idempotently_with_contract_severity(owner, owner_home, hub, gate):
    e1 = ev(data={"open_s": 900})
    e2 = ev("cover.sensor_conflict", severity="info")  # hub says info, contract says critical
    r = hub.post("/api/v1/hub/events", json={"schema": 1, "events": [e1, e2]})
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"accepted": 2, "duplicates": 0, "rejected": []}
    # Retried batch (hub did not get the response): nothing duplicated.
    r = hub.post("/api/v1/hub/events", json={"schema": 1, "events": [e1]})
    assert r.json()["data"]["duplicates"] == 1
    feed = owner.get(f"/api/v1/homes/{owner_home}/events").json()["data"]
    assert len(feed) == 2
    by_type = {e["type"]: e for e in feed}
    assert by_type["cover.sensor_conflict"]["severity"] == "critical"
    assert by_type["cover.left_open"]["data"] == {"open_s": 900}
    assert by_type["cover.left_open"]["device_name"] == "Darvoza"
    crit = owner.get(f"/api/v1/homes/{owner_home}/events?severity=critical").json()["data"]
    assert [e["type"] for e in crit] == ["cover.sensor_conflict"]


def test_events_not_in_contract_or_wrong_device_are_rejected(owner, owner_home, hub, gate, light):
    batch = [ev("cover.exploded"), ev("alarm.triggered"), ev(key="nope"),
             ev("cover.left_open", key="garden_lights")]
    r = hub.post("/api/v1/hub/events", json={"schema": 1, "events": batch})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["accepted"] == 0 and len(data["rejected"]) == 4
    r = hub.post("/api/v1/hub/events", json={"schema": 1, "events": [{**ev(), "severity": "panic"}]})
    assert r.status_code == 422


def test_event_feed_is_private_to_the_home(owner_home, hub, gate, outsider):
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [ev()]})
    assert outsider.get(f"/api/v1/homes/{owner_home}/events").status_code == 404


def test_event_feed_pagination(owner, owner_home, hub, gate):
    batch = [{**ev(), "ts": TS(timedelta(minutes=-i))} for i in range(5)]
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": batch})
    page1 = owner.get(f"/api/v1/homes/{owner_home}/events?limit=2").json()["data"]
    assert len(page1) == 2 and page1[0]["ts"] > page1[1]["ts"]
    page2 = owner.get(f"/api/v1/homes/{owner_home}/events",
                      params={"limit": 10, "before": page1[-1]["ts"]}).json()["data"]
    assert len(page2) == 3


def test_capability_config_is_checked_against_contract(owner, owner_home):
    url = f"/api/v1/homes/{owner_home}/devices"
    assert owner.post(url, json=ALARM).status_code == 201
    bad = [
        {**GATE, "key": "g2", "capabilities": {"cover": {"left_open_after_s": 5}}},
        {**GATE, "key": "g3", "capabilities": {"cover": {"colour": "red"}}},
        {**ALARM, "key": "a2", "capabilities": {"alarm": {}}},
        {**ALARM, "key": "a3", "capabilities": {"alarm": {"zones": [
            {"device_key": "x1", "capability": "switch", "mode": "entry"}]}}},
    ]
    for body in bad:
        r = owner.post(url, json=body)
        assert r.status_code == 422, body
    # Common keys still work everywhere.
    ok = {**GATE, "key": "g4", "capabilities": {"cover": {"confirm_timeout_s": 40}}}
    assert owner.post(url, json=ok).status_code == 201


def test_retention_purges_old_events(owner_home, hub, gate, dbs):
    from app.jobs import retention
    from app.models import Event
    hub.post("/api/v1/hub/events", json={"schema": 1, "events": [
        {**ev(), "ts": TS(timedelta(days=-200))}, ev()]})
    assert retention.run(dbs)["events"] == 1
    assert dbs.query(Event).count() == 1
