import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

CONTRACTS_DIR = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = CONTRACTS_DIR / "schemas"


def load_json(path: Path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def all_schemas():
    return {p.name: load_json(p) for p in sorted(SCHEMAS_DIR.glob("*.schema.json"))}


def build_registry() -> Registry:
    resources = []
    for name, schema in all_schemas().items():
        res = Resource.from_contents(schema)
        resources.append((schema["$id"], res))
        resources.append((name, res))
    return Registry().with_resources(resources)


@pytest.fixture(scope="session")
def capabilities():
    return load_json(CONTRACTS_DIR / "capabilities.json")


@pytest.fixture(scope="session")
def validator_for():
    registry = build_registry()
    schemas = all_schemas()

    def make(name: str) -> Draft202012Validator:
        return Draft202012Validator(
            schemas[name],
            registry=registry,
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        )

    return make
