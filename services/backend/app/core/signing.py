"""Command signing (ARCHITECTURE 4.4, ADR 0004/0007).

home_signing_key = HMAC-SHA256(SIGNING_MASTER_KEY, "home-signing:" + home_id)
signature        = HMAC-SHA256(home_signing_key, canonical_json(payload))  (lowercase hex)
canonical_json   = UTF-8, keys sorted, separators (',', ':'), no whitespace

The derived key is never stored in the database. Test vectors:
packages/contracts/test-vectors/signing.json (the Hub verifies the same vectors).
"""

import hashlib
import hmac
import json
import uuid
from typing import Any


def derive_home_key(master_key: str, home_id: uuid.UUID) -> bytes:
    return hmac.new(
        master_key.encode("utf-8"), f"home-signing:{home_id}".encode("utf-8"), hashlib.sha256
    ).digest()


def canonical_json(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sign(key: bytes, payload: dict) -> str:
    return hmac.new(key, canonical_json(payload), hashlib.sha256).hexdigest()


def verify(key: bytes, payload: dict, signature: str) -> bool:
    return hmac.compare_digest(sign(key, payload), signature)
