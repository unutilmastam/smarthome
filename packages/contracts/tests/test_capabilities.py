import pytest
from jsonschema import Draft202012Validator

PERMISSIONS = {
    "view", "control_basic", "control_access", "control_power",
    "camera_live", "camera_archive", "configure", "manage_users", "view_audit",
}


def items(capabilities):
    return sorted(capabilities["capabilities"].items())


def test_registry_matches_its_schema(capabilities, validator_for):
    validator_for("capabilities.schema.json").validate(capabilities)


def test_every_capability_has_required_fields(capabilities):
    for name, cap in items(capabilities):
        for field in ("permission", "risk", "attributes", "actions"):
            assert field in cap, f"{name}: missing {field}"
        assert cap["permission"] in PERMISSIONS, name
        assert cap["risk"] in capabilities["risk_levels"], name


def test_attribute_specs_are_json_schemas(capabilities):
    for name, cap in items(capabilities):
        for attr, spec in cap["attributes"].items():
            Draft202012Validator.check_schema(spec)
            assert "type" in spec, f"{name}.{attr}: missing type"


def test_action_params_are_strict_object_schemas(capabilities):
    for name, cap in items(capabilities):
        for action, spec in cap["actions"].items():
            params = spec["params"]
            Draft202012Validator.check_schema(params)
            assert params.get("type") == "object", f"{name}.{action}"
            assert params.get("additionalProperties") is False, f"{name}.{action}"


def test_confirm_attribute_exists(capabilities):
    for name, cap in items(capabilities):
        if "confirm_attribute" in cap:
            assert cap["confirm_attribute"] in cap["attributes"], name


@pytest.mark.parametrize("name", ["cover", "lock", "contactor", "valve"])
def test_physical_actuators_require_feedback(capabilities, name):
    assert "confirm_attribute" in capabilities["capabilities"][name]


def test_high_risk_capabilities(capabilities):
    high = {n for n, c in items(capabilities) if c["risk"] == "high"}
    assert {"cover", "lock", "contactor"} <= high


def test_valve_open_requires_bounded_duration(capabilities):
    params = capabilities["capabilities"]["valve"]["actions"]["open"]["params"]
    assert "duration_s" in params["required"]
    assert params["properties"]["duration_s"]["maximum"] <= 3600


def test_sensors_have_no_actions(capabilities):
    for name in ("power_meter", "contact", "motion", "environment", "leak"):
        assert capabilities["capabilities"][name]["actions"] == {}, name


def test_roles_matrix_is_consistent(capabilities):
    from conftest import CONTRACTS_DIR, load_json
    roles = load_json(CONTRACTS_DIR / "roles.json")
    perms = set(roles["permissions"])
    assert perms == PERMISSIONS
    assert set(roles["roles"]) == {"owner", "admin", "family", "guest", "viewer"}
    for role, granted in roles["roles"].items():
        assert set(granted) <= perms, role
    assert set(roles["roles"]["owner"]) == perms
    assert "manage_users" not in roles["roles"]["admin"]
    for cap in capabilities["capabilities"].values():
        assert cap["permission"] in perms


def test_measurements_have_physical_bounds(capabilities):
    """Sensor garbage (e.g. -9999 V) must fail validation instead of reaching the UI."""
    caps = capabilities["capabilities"]
    for cap, attr in [("power_meter", "voltage"), ("power_meter", "current"),
                      ("power_meter", "frequency"), ("power_meter", "power"),
                      ("environment", "temperature"), ("climate", "current_temp")]:
        spec = caps[cap]["attributes"][attr]
        assert "minimum" in spec and "maximum" in spec, f"{cap}.{attr}"
    assert caps["power_meter"]["attributes"]["energy"]["minimum"] == 0
