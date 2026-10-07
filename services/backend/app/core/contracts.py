"""Loads packages/contracts (single source of truth for capabilities)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from jsonschema import Draft202012Validator


class Contracts:
    def __init__(self, contracts_dir: Path):
        self.dir = Path(contracts_dir)
        with (self.dir / "capabilities.json").open(encoding="utf-8") as fh:
            self.registry = json.load(fh)
        self.capabilities: Dict[str, dict] = self.registry["capabilities"]
        self._param_validators: Dict[tuple, Draft202012Validator] = {}

    def has_capability(self, name: str) -> bool:
        return name in self.capabilities

    def capability(self, name: str) -> dict:
        return self.capabilities[name]

    def attributes(self, capability: str) -> Dict[str, dict]:
        return self.capabilities[capability]["attributes"]

    def attribute_unit(self, capability: str, attribute: str) -> Optional[str]:
        return self.attributes(capability)[attribute].get("unit")

    def all_attribute_paths(self, capabilities: List[str]) -> List[str]:
        return [f"{c}.{a}" for c in capabilities for a in self.attributes(c)]

    def params_validator(self, capability: str, action: str) -> Draft202012Validator:
        key = (capability, action)
        if key not in self._param_validators:
            schema = self.capabilities[capability]["actions"][action]["params"]
            self._param_validators[key] = Draft202012Validator(schema)
        return self._param_validators[key]

    def attribute_validator(self, capability: str, attribute: str) -> Draft202012Validator:
        key = (capability, "@" + attribute)
        if key not in self._param_validators:
            spec = dict(self.attributes(capability)[attribute])
            spec.pop("unit", None)
            spec.pop("description", None)
            self._param_validators[key] = Draft202012Validator(spec)
        return self._param_validators[key]

    def config_validator(self, capability: str) -> Optional[Draft202012Validator]:
        """Capability-specific device config schema (ADR 0012), if the contract has one."""
        spec = self.capabilities[capability].get("config")
        if spec is None:
            return None
        key = (capability, "#config")
        if key not in self._param_validators:
            self._param_validators[key] = Draft202012Validator(spec)
        return self._param_validators[key]

    def event_severity(self, event_type: str) -> Optional[str]:
        """'cover.left_open' -> 'warning'; None if the contract does not list it."""
        cap, _, name = event_type.partition(".")
        spec = self.capabilities.get(cap, {}).get("events", {}).get(name)
        return spec["severity"] if spec else None

    def schema_path(self, name: str) -> Path:
        return self.dir / "schemas" / name


@lru_cache(maxsize=4)
def load_contracts(contracts_dir: str) -> Contracts:
    return Contracts(Path(contracts_dir))
