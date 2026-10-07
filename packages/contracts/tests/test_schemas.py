import copy

import pytest
from jsonschema import Draft202012Validator

from conftest import all_schemas

EXPECTED = {
    "value.schema.json",
    "command-envelope.schema.json",
    "ack.schema.json",
    "state-report.schema.json",
    "capabilities.schema.json",
    "local-mqtt.schema.json",
}

UUID1 = "6f1c2a8e-3b5d-4c7e-9f10-1a2b3c4d5e6f"
UUID2 = "0b7a4c1e-8d2f-4e6a-b3c9-7d8e9f0a1b2c"
UUID3 = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
TS = "2026-10-07T12:50:03Z"


def test_expected_schemas_exist():
    assert EXPECTED <= set(all_schemas())


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_schema_is_valid_draft_2020_12(name):
    schema = all_schemas()[name]
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].endswith(name)


# ---- value -----------------------------------------------------------------

VALID_VALUES = [
    {"value": 231.4, "unit": "V", "source": "reported", "quality": "good", "ts": TS},
    {"value": True, "source": "assumed", "quality": "good", "ts": TS},
    {"value": 20.5, "source": "reported", "quality": "stale", "ts": TS},
    {"value": None, "source": "reported", "quality": "unknown", "ts": None},
    {"value": None, "source": "reported", "quality": "not_supported", "ts": None},
]

INVALID_VALUES = [
    # invented value while quality says unknown
    {"value": 0, "source": "reported", "quality": "unknown", "ts": None},
    # good quality without a value
    {"value": None, "source": "reported", "quality": "good", "ts": TS},
    # good quality without timestamp
    {"value": 1, "source": "reported", "quality": "good", "ts": None},
    # non-UTC timestamp
    {"value": 1, "source": "reported", "quality": "good", "ts": "2026-10-07T17:50:03+05:00"},
    {"value": 1, "source": "guessed", "quality": "good", "ts": TS},
    {"value": 1, "source": "reported", "quality": "good"},
    {"value": 1, "source": "reported", "quality": "good", "ts": TS, "extra": 1},
]


@pytest.mark.parametrize("doc", VALID_VALUES)
def test_value_valid(validator_for, doc):
    validator_for("value.schema.json").validate(doc)


@pytest.mark.parametrize("doc", INVALID_VALUES)
def test_value_invalid(validator_for, doc):
    assert not validator_for("value.schema.json").is_valid(doc)


# ---- command envelope ------------------------------------------------------

def envelope():
    return {
        "schema": 1,
        "payload": {
            "command_id": UUID1,
            "device_id": UUID2,
            "device_key": "garden_lights",
            "capability": "switch",
            "action": "turn_on",
            "params": {},
            "issued_at": "2026-10-07T12:50:00Z",
            "expires_at": "2026-10-07T12:50:10Z",
            "issued_by": {"user_id": UUID3, "role": "owner"},
        },
        "signature": "a" * 64,
    }


def test_envelope_valid(validator_for):
    validator_for("command-envelope.schema.json").validate(envelope())


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.pop("signature"),
        lambda e: e.__setitem__("signature", "A" * 64),
        lambda e: e.__setitem__("signature", "a" * 63),
        lambda e: e["payload"].pop("expires_at"),
        lambda e: e["payload"].__setitem__("command_id", "not-a-uuid"),
        lambda e: e["payload"]["issued_by"].__setitem__("role", "root"),
        lambda e: e["payload"].__setitem__("device_key", "Garden Lights"),
        lambda e: e["payload"].__setitem__("extra", 1),
        lambda e: e.__setitem__("schema", 2),
    ],
)
def test_envelope_invalid(validator_for, mutate):
    doc = envelope()
    mutate(doc)
    assert not validator_for("command-envelope.schema.json").is_valid(doc)


# ---- ack ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "doc",
    [
        {"schema": 1, "command_id": UUID1, "status": "acked", "ts": TS},
        {"schema": 1, "command_id": UUID1, "status": "confirmed", "ts": TS},
        {"schema": 1, "command_id": UUID1, "status": "rejected", "reason": "expired", "ts": TS},
        {"schema": 1, "command_id": UUID1, "status": "failed", "reason": "no_feedback", "ts": TS},
    ],
)
def test_ack_valid(validator_for, doc):
    validator_for("ack.schema.json").validate(doc)


@pytest.mark.parametrize(
    "doc",
    [
        {"schema": 1, "command_id": UUID1, "status": "rejected", "ts": TS},
        {"schema": 1, "command_id": UUID1, "status": "failed", "reason": "replay", "ts": TS},
        {"schema": 1, "command_id": UUID1, "status": "confirmed", "reason": "expired", "ts": TS},
        {"schema": 1, "command_id": UUID1, "status": "done", "ts": TS},
        {"schema": 1, "command_id": UUID1, "status": "acked"},
    ],
)
def test_ack_invalid(validator_for, doc):
    assert not validator_for("ack.schema.json").is_valid(doc)


# ---- state report -------------------------------------------------------------

def report():
    return {
        "schema": 1,
        "ts": TS,
        "devices": [
            {
                "device_key": "main_meter",
                "availability": "online",
                "states": {
                    "power_meter": {
                        "voltage": {"value": 231.4, "unit": "V", "source": "reported", "quality": "good", "ts": TS},
                        "frequency": {"value": None, "source": "reported", "quality": "not_supported", "ts": None},
                    }
                },
            },
            {"device_key": "garden_radar", "availability": "offline"},
        ],
    }


def test_report_valid(validator_for):
    validator_for("state-report.schema.json").validate(report())


def test_report_rejects_invented_value(validator_for):
    doc = copy.deepcopy(report())
    doc["devices"][0]["states"]["power_meter"]["frequency"]["value"] = 50
    assert not validator_for("state-report.schema.json").is_valid(doc)


def test_report_rejects_bad_availability(validator_for):
    doc = report()
    doc["devices"][1]["availability"] = "maybe"
    assert not validator_for("state-report.schema.json").is_valid(doc)


def test_local_mqtt_defs(validator_for):
    from jsonschema import Draft202012Validator
    from conftest import all_schemas
    schema = all_schemas()["local-mqtt.schema.json"]
    Draft202012Validator.check_schema(schema)
    fc = Draft202012Validator.FORMAT_CHECKER

    def v(name):
        return Draft202012Validator({**schema["$defs"][name], "$defs": schema["$defs"]},
                                    format_checker=fc)
    v("cmd").validate({"schema": 1, "command_id": UUID1, "capability": "switch",
                       "action": "turn_on", "params": {}})
    v("ack").validate({"schema": 1, "command_id": UUID1, "status": "acked"})
    v("state").validate({"schema": 1, "states": {"switch": {"on": True}}, "source": "reported"})
    assert not v("ack").is_valid({"schema": 1, "command_id": UUID1, "status": "confirmed"})
    assert not v("cmd").is_valid({"schema": 1, "command_id": "x", "capability": "switch",
                                  "action": "turn_on", "params": {}})
