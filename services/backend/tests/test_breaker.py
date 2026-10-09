"""ADR 0015: smart breakers in the panel — config is checked against the contract."""

import pytest

BASE = {"adapter": "esphome", "protocol": "mqtt"}


def make(owner, home, key, cfg, extra=None):
    body = {**BASE, "key": key, "name": key, "capabilities": {"breaker": cfg, **(extra or {})}}
    return owner.post(f"/api/v1/homes/{home}/devices", json=body)


def test_breaker_with_panel_position_and_rating(owner, owner_home):
    r = make(owner, owner_home, "breaker_kitchen",
             {"panel": "Asosiy shit", "position": 1, "rating_a": 16, "curve": "C", "poles": 1},
             {"power_meter": {}})
    assert r.status_code == 201, r.text
    cap = r.json()["data"]["capabilities"]["breaker"]
    assert cap["risk"] == "high" and cap["permission"] == "control_power"
    assert cap["config"]["position"] == 1 and cap["config"]["curve"] == "C"
    # Nothing reported yet: unknown, never "on" or "off".
    assert {a: v["quality"] for a, v in cap["attributes"].items()} == {"closed": "unknown", "tripped": "unknown"}


@pytest.mark.parametrize("cfg", [
    {"position": 0}, {"position": 100}, {"rating_a": 17}, {"curve": "Z"}, {"poles": 5},
    {"panel": ""}, {"color": "red"},
])
def test_bad_breaker_config_is_refused(owner, owner_home, cfg):
    r = make(owner, owner_home, "breaker_x", cfg)
    assert r.status_code == 422, r.text


def test_breaker_events_have_contract_severity_and_uzbek_text():
    from app.core.config import get_settings
    from app.core.contracts import load_contracts
    from app.services.notify_texts import EVENT_TEXT
    c = load_contracts(str(get_settings().contracts_dir))
    assert c.event_severity("breaker.tripped") == "critical"
    assert c.event_severity("breaker.close_refused") == "warning"
    assert "breaker.tripped" in EVENT_TEXT and "breaker.close_refused" in EVENT_TEXT
