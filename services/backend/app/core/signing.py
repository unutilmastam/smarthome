"""Command signing (ARCHITECTURE 4.4, ADR 0004/0007).

home_signing_key = HMAC-SHA256(SIGNING_MASTER_KEY, "home-signing:" + home_id)
The derived key is never stored in the database.
"""

import hashlib
import hmac
import uuid


def derive_home_key(master_key: str, home_id: uuid.UUID) -> bytes:
    return hmac.new(
        master_key.encode("utf-8"), f"home-signing:{home_id}".encode("utf-8"), hashlib.sha256
    ).digest()
