"""Command signature verification (ARCHITECTURE 4.4). Must match the backend exactly;
both are checked against packages/contracts/test-vectors/signing.json."""

import hashlib
import hmac
import json
from typing import Any


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sign(key: bytes, payload: dict) -> str:
    return hmac.new(key, canonical_json(payload), hashlib.sha256).hexdigest()


def verify(key: bytes, payload: dict, signature: str) -> bool:
    if not isinstance(signature, str):
        return False
    return hmac.compare_digest(sign(key, payload), signature)
