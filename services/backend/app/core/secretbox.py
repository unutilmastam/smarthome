"""Small secrets stored in the database, encrypted (ADR 0016): Tuya local keys, the Yandex
token. AES-256-GCM; the key is derived from SIGNING_MASTER_KEY with HKDF (its own label, so
it is never the signing key itself). The device/integration id is the associated data: a
sealed value copied to another row does not open.

Format: "v1:" + base64url(nonce(12) + ciphertext+tag).
"""
import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class SecretBoxError(ValueError):
    pass


def _key(master_key: str) -> bytes:
    if not master_key:
        raise SecretBoxError("SIGNING_MASTER_KEY is not set")
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=b"smarthome secret-box v1").derive(master_key.encode("utf-8"))


def seal(master_key: str, plaintext: str, aad: str) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_key(master_key)).encrypt(nonce, plaintext.encode("utf-8"), aad.encode("utf-8"))
    return "v1:" + base64.urlsafe_b64encode(nonce + ct).decode("ascii")


def open_(master_key: str, token: str, aad: str) -> str:
    if not token.startswith("v1:"):
        raise SecretBoxError("unknown secret format")
    try:
        raw = base64.urlsafe_b64decode(token[3:].encode("ascii"))
        return AESGCM(_key(master_key)).decrypt(raw[:12], raw[12:], aad.encode("utf-8")).decode("utf-8")
    except Exception as exc:  # wrong key, tampered, other row
        raise SecretBoxError("secret does not open (SIGNING_MASTER_KEY changed?)") from exc
