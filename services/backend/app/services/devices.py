import uuid
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contracts import Contracts
from app.core.errors import validation_error
from app.models import Device, DeviceCapability, Hub, Room

ALLOWED_CONFIG_KEYS = {"report_interval_s", "max_runtime_s", "confirm_timeout_s", "invert"}


def validate_capabilities(contracts: Contracts, caps: Dict[str, dict],
                          unsupported: List[str]) -> None:
    errors = []
    for name, cfg in caps.items():
        if not contracts.has_capability(name):
            errors.append(f"unknown capability '{name}'")
            continue
        if not isinstance(cfg, dict):
            errors.append(f"{name}: config must be an object")
            continue
        specific = {k: v for k, v in cfg.items() if k not in ALLOWED_CONFIG_KEYS}
        validator = contracts.config_validator(name)
        if validator is None:
            if specific:
                errors.append(f"{name}: unknown config keys {sorted(specific)}")
        else:
            # Capability-specific keys are checked against the contract (ADR 0012).
            errors += [f"{name}: {e.message}" for e in validator.iter_errors(specific)]
        for k in ("report_interval_s", "max_runtime_s", "confirm_timeout_s"):
            if k in cfg and (not isinstance(cfg[k], int) or isinstance(cfg[k], bool)
                             or cfg[k] <= 0):
                errors.append(f"{name}.{k}: must be a positive integer")
    valid_paths = set(contracts.all_attribute_paths([c for c in caps
                                                     if contracts.has_capability(c)]))
    for path in unsupported:
        if path not in valid_paths:
            errors.append(f"unsupported '{path}' is not an attribute of this device")
    if len(set(unsupported)) != len(unsupported):
        errors.append("unsupported contains duplicates")
    if errors:
        raise validation_error("Invalid device capabilities", errors)


def check_room(db: Session, home_id: uuid.UUID, room_id: Optional[uuid.UUID]) -> None:
    if room_id is None:
        return
    room = db.get(Room, room_id)
    if room is None or room.home_id != home_id:
        raise validation_error("room_id does not belong to this home")


def set_capabilities(device: Device, caps: Dict[str, dict]) -> None:
    keep = {c.capability: c for c in device.capabilities}
    device.capabilities = []
    for name, cfg in sorted(caps.items()):
        cap = keep.get(name) or DeviceCapability(capability=name)
        cap.config_json = dict(cfg)
        device.capabilities.append(cap)
    # Drop stored state of removed capabilities.
    device.states = [s for s in device.states if s.capability in caps]


def active_hub(db: Session, home_id: uuid.UUID) -> Optional[Hub]:
    return db.scalar(select(Hub).where(Hub.home_id == home_id, Hub.status == "active"))
