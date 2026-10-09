"""Every check a command must pass before it may reach a device.

Order (ADR 0004): envelope -> signature -> expiry -> replay -> device -> params
-> role -> local safety rules. A failed check NEVER executes the command.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

from gateway.contracts import Contracts
from gateway.signing import verify
from gateway.store import Store
from gateway.timeutil import parse_ts


@dataclass
class Verdict:
    ok: bool
    command_id: Optional[str]
    reason: Optional[str] = None
    detail: Optional[str] = None
    payload: Optional[dict] = None
    device: Optional[dict] = None


def reject(cid, reason, detail, payload=None) -> Verdict:
    return Verdict(False, cid, reason, detail, payload)


def verify_envelope(env: dict, *, key: bytes, contracts: Contracts, store: Store,
                    devices: Dict[str, dict], availability: Dict[str, str],
                    now: datetime, skew_s: float) -> Verdict:
    payload = env.get("payload") if isinstance(env, dict) else None
    cid = payload.get("command_id") if isinstance(payload, dict) else None
    if not isinstance(cid, str):
        cid = None

    errors = list(contracts.envelope.iter_errors(env))
    if errors:
        return reject(cid, "bad_signature", f"malformed envelope: {errors[0].message}"[:200])
    if not verify(key, payload, env["signature"]):
        return reject(cid, "bad_signature", "signature mismatch")

    skew = timedelta(seconds=skew_s)
    expires_at = parse_ts(payload["expires_at"])
    issued_at = parse_ts(payload["issued_at"])
    if now > expires_at + skew:
        return reject(cid, "expired", f"expired at {payload['expires_at']}")
    if issued_at > now + skew:
        return reject(cid, "expired", "issued_at is in the future (clock skew?)")
    if expires_at <= issued_at:
        return reject(cid, "expired", "expires_at <= issued_at")

    # Recorded before execution: the same command_id can never run twice.
    if not store.claim_command(cid):
        return reject(cid, "replay", "command_id already received")

    device = devices.get(payload["device_key"])
    if device is None or device["id"] != payload["device_id"]:
        return reject(cid, "unknown_device", "device_key/device_id not in hub config", payload)
    cap = payload["capability"]
    if cap not in device["capabilities"] or cap not in contracts.capabilities:
        return reject(cid, "invalid_params", f"device has no capability {cap}", payload)
    spec = contracts.capabilities[cap]
    if payload["action"] not in spec["actions"]:
        return reject(cid, "invalid_params", f"unknown action {payload['action']}", payload)
    perr = contracts.params_errors(cap, payload["action"], payload["params"])
    if perr:
        return reject(cid, "invalid_params", perr[0][:200], payload)

    role = payload["issued_by"]["role"]
    if not contracts.allowed(role, spec["permission"]):
        return reject(cid, "forbidden", f"role {role} lacks {spec['permission']}", payload)

    if not device.get("enabled", True):
        return reject(cid, "safety_rule", "device is disabled", payload)
    if availability.get(device["key"]) == "offline":
        return reject(cid, "device_offline", "device is offline (LWT)", payload)
    cfg = device["capabilities"].get(cap) or {}
    max_rt = cfg.get("max_runtime_s")
    dur = payload["params"].get("duration_s")
    if max_rt and isinstance(dur, int) and dur > max_rt:
        return reject(cid, "safety_rule", f"duration_s {dur} > max_runtime_s {max_rt}", payload)

    return Verdict(True, cid, payload=payload, device=device)
