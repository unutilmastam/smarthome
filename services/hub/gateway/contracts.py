"""packages/contracts, loaded by the hub (same files as the backend)."""

import json
from pathlib import Path
from typing import Dict

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


class Contracts:
    def __init__(self, contracts_dir: Path):
        d = Path(contracts_dir)
        self.dir = d
        self.capabilities: Dict[str, dict] = json.loads(
            (d / "capabilities.json").read_text(encoding="utf-8"))["capabilities"]
        roles = json.loads((d / "roles.json").read_text(encoding="utf-8"))
        self.roles = {r: frozenset(p) for r, p in roles["roles"].items()}
        schemas = {p.name: json.loads(p.read_text(encoding="utf-8"))
                   for p in (d / "schemas").glob("*.schema.json")}
        registry = Registry().with_resources(
            [(s["$id"], Resource.from_contents(s)) for s in schemas.values()]
            + [(n, Resource.from_contents(s)) for n, s in schemas.items()])
        fc = Draft202012Validator.FORMAT_CHECKER
        self.envelope = Draft202012Validator(schemas["command-envelope.schema.json"],
                                             registry=registry, format_checker=fc)
        local = schemas["local-mqtt.schema.json"]
        self.local = {n: Draft202012Validator({**local["$defs"][n], "$defs": local["$defs"]},
                                              format_checker=fc)
                      for n in ("cmd", "ack", "state", "event")}
        self._cache: Dict[tuple, Draft202012Validator] = {}

    def allowed(self, role: str, permission: str) -> bool:
        return permission in self.roles.get(role, frozenset())

    def params_errors(self, capability: str, action: str, params: dict) -> list:
        key = ("p", capability, action)
        if key not in self._cache:
            self._cache[key] = Draft202012Validator(
                self.capabilities[capability]["actions"][action]["params"])
        return [e.message for e in self._cache[key].iter_errors(params)]

    def value_errors(self, capability: str, attribute: str, value) -> list:
        key = ("a", capability, attribute)
        if key not in self._cache:
            spec = {k: v for k, v in self.capabilities[capability]["attributes"][attribute].items()
                    if k not in ("unit", "description")}
            self._cache[key] = Draft202012Validator(spec)
        return [e.message for e in self._cache[key].iter_errors(value)]
