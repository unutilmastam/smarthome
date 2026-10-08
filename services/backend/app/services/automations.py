"""Automation validation and views (ARCHITECTURE 11, ADR 0013).

Validation is the safety gate: the hub executes whatever is stored here.
- JSON Schema from packages/contracts (automation.schema.json)
- every device/capability/attribute exists in this home; values match the contract
- command actions: action exists, params valid, risk is NOT high
- sun triggers/conditions need home coordinates
- no loops: rule A acting on (device, capability) that rule B triggers on -> edge A->B;
  any cycle (including A->A) is refused
"""

import json
import uuid
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Set, Tuple

from jsonschema import Draft202012Validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contracts import Contracts
from app.core.errors import validation_error
from app.models import Automation, AutomationRun, Device, Home
from app.services.device_view import iso


@lru_cache(maxsize=4)
def _schema(path: str) -> Draft202012Validator:
    with open(path, encoding="utf-8") as fh:
        return Draft202012Validator(json.load(fh))


def _edges(defn: dict) -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]]]:
    """(capabilities this rule acts on, capabilities this rule triggers on)."""
    acts = {(a["device"], a["capability"]) for a in defn.get("actions", []) if a["type"] == "command"}
    trig = {(t["device"], t["capability"]) for t in defn.get("triggers", []) if t["type"] == "state"}
    return acts, trig


def find_cycle(rules: Dict[str, dict]) -> Optional[List[str]]:
    """rules: id -> definition. Returns a cycle as a list of ids, or None."""
    edges: Dict[str, List[str]] = {r: [] for r in rules}
    info = {r: _edges(d) for r, d in rules.items()}
    for a, (acts, _) in info.items():
        for b, (_, trig) in info.items():
            if acts & trig:
                edges[a].append(b)
    state: Dict[str, int] = {}
    stack: List[str] = []

    def visit(n: str) -> Optional[List[str]]:
        state[n] = 1
        stack.append(n)
        for m in edges[n]:
            if state.get(m) == 1:
                return stack[stack.index(m):] + [m]
            if m not in state:
                found = visit(m)
                if found:
                    return found
        stack.pop()
        state[n] = 2
        return None

    for n in rules:
        if n not in state:
            found = visit(n)
            if found:
                return found
    return None


def validate(db: Session, contracts: Contracts, home: Home, defn: dict,
             self_id: Optional[uuid.UUID] = None, name: str = "") -> None:
    errors: List[str] = []
    for e in sorted(_schema(str(contracts.schema_path("automation.schema.json"))).iter_errors(defn),
                    key=lambda e: list(e.absolute_path)):
        errors.append(f"/{'/'.join(map(str, e.absolute_path))}: {e.message}")
    if errors:
        raise validation_error("Automation does not match the contract", errors[:20])

    devices = {d.key: d for d in db.scalars(select(Device).where(Device.home_id == home.id))}

    def cap_of(where: str, key: str, cap: str) -> Optional[Device]:
        d = devices.get(key)
        if d is None:
            errors.append(f"{where}: unknown device '{key}'")
            return None
        if cap not in {c.capability for c in d.capabilities}:
            errors.append(f"{where}: device '{key}' has no capability '{cap}'")
            return None
        return d

    def check_value(where: str, d: Device, cap: str, attr: str, value) -> None:
        if attr not in contracts.attributes(cap):
            errors.append(f"{where}: '{cap}' has no attribute '{attr}'")
            return
        if f"{cap}.{attr}" in (d.unsupported or []):
            errors.append(f"{where}: '{cap}.{attr}' is not supported by '{d.key}'")
            return
        if any(True for _ in contracts.attribute_validator(cap, attr).iter_errors(value)):
            errors.append(f"{where}: {value!r} is not a valid {cap}.{attr}")

    uses_sun = False
    for i, t in enumerate(defn["triggers"]):
        where = f"triggers[{i}]"
        if t["type"] == "state":
            d = cap_of(where, t["device"], t["capability"])
            if d:
                check_value(where, d, t["capability"], t["attribute"], t["to"])
        uses_sun |= t["type"] == "sun"
    for i, c in enumerate(defn.get("conditions", [])):
        where = f"conditions[{i}]"
        if c["type"] == "state":
            d = cap_of(where, c["device"], c["capability"])
            if d:
                check_value(where, d, c["capability"], c["attribute"], c["is"])
        elif c["type"] == "security_mode":
            if not any("alarm" in {x.capability for x in d.capabilities} for d in devices.values()):
                errors.append(f"{where}: this home has no security system")
        uses_sun |= c["type"] == "sun"
    for i, a in enumerate(defn["actions"]):
        where = f"actions[{i}]"
        if a["type"] != "command":
            continue
        d = cap_of(where, a["device"], a["capability"])
        if not d:
            continue
        spec = contracts.capability(a["capability"])
        if spec["risk"] == "high":
            errors.append(f"{where}: '{a['capability']}' is high risk - only a person with a PIN "
                          "may do this, never an automation")
            continue
        if a["action"] not in spec["actions"]:
            errors.append(f"{where}: '{a['capability']}' has no action '{a['action']}'")
            continue
        for e in contracts.params_validator(a["capability"], a["action"]).iter_errors(a.get("params") or {}):
            errors.append(f"{where}.params: {e.message}")
        if a["capability"] == "valve" and a["action"] == "open":
            cfg = next((c.config_json or {} for c in d.capabilities if c.capability == "valve"), {})
            dur = (a.get("params") or {}).get("duration_s")
            if isinstance(dur, int) and cfg.get("max_runtime_s") and dur > cfg["max_runtime_s"]:
                errors.append(f"{where}: duration_s exceeds the valve's max_runtime_s ({cfg['max_runtime_s']})")
        if "auto_off_after_s" in a and (a["capability"], a["action"]) != ("switch", "turn_on"):
            errors.append(f"{where}: auto_off_after_s is only for switch.turn_on")
    if uses_sun and (home.latitude is None or home.longitude is None):
        errors.append("sun trigger/condition needs the home coordinates (Settings -> home)")
    if errors:
        raise validation_error("Automation is not valid for this home", errors[:20])

    # Loops across all enabled rules of the home, with this one as it would be saved.
    rules: Dict[str, dict] = {
        str(a.id): a.definition for a in db.scalars(select(Automation).where(
            Automation.home_id == home.id, Automation.enabled.is_(True)))
        if a.id != self_id}
    me = str(self_id or "new")
    rules[me] = defn
    cycle = find_cycle(rules)
    if cycle:
        names = {str(a.id): a.name for a in db.scalars(select(Automation).where(
            Automation.home_id == home.id))}
        names[me] = name or "this rule"
        raise validation_error("Automations would trigger each other in a loop",
                               [" -> ".join(names.get(x, x) for x in cycle)])


def automation_out(a: Automation, last_run: Optional[AutomationRun] = None) -> dict:
    return {"id": str(a.id), "home_id": str(a.home_id), "name": a.name, "enabled": a.enabled,
            "definition": a.definition, "version": a.version,
            "created_at": iso(a.created_at), "updated_at": iso(a.updated_at),
            "last_run": run_out(last_run) if last_run else None}


def run_out(r: AutomationRun) -> dict:
    return {"id": str(r.id), "automation_id": str(r.automation_id), "version": r.version,
            "ts": iso(r.ts), "trigger": r.trigger, "result": r.result, "reason": r.reason,
            "actions": r.actions or []}


def hub_view(rows: Iterable[Automation]) -> List[dict]:
    return [{"id": str(a.id), "name": a.name, "version": a.version, "definition": a.definition}
            for a in rows if a.enabled]
