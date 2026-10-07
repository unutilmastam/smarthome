"""Independent check of the signing test vectors (no backend code imported)."""

import hashlib
import hmac
import json

from conftest import CONTRACTS_DIR, load_json


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def test_vectors_reproduce(validator_for):
    v = load_json(CONTRACTS_DIR / "test-vectors" / "signing.json")
    key = hmac.new(v["master_key"].encode(), f"home-signing:{v['home_id']}".encode(),
                   hashlib.sha256).digest()
    assert key.hex() == v["home_signing_key_hex"]
    envelope = validator_for("command-envelope.schema.json")
    assert len(v["cases"]) >= 5
    for case in v["cases"]:
        assert canonical(case["payload"]).decode("utf-8") == case["canonical"], case["name"]
        sig = hmac.new(key, case["canonical"].encode("utf-8"), hashlib.sha256).hexdigest()
        assert sig == case["signature"], case["name"]
        envelope.validate({"schema": 1, "payload": case["payload"], "signature": sig})
    for case in v["negative"]:
        sig = hmac.new(key, canonical(case["payload"]), hashlib.sha256).hexdigest()
        assert hmac.compare_digest(sig, case["signature"]) is case["valid"], case["name"]
