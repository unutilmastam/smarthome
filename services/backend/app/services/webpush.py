"""Web Push without extra dependencies (ADR 0014).

RFC 8291 (message encryption, aes128gcm content coding, RFC 8188) and RFC 8292 (VAPID),
built on `cryptography` + PyJWT. Verified against the RFC 8291 Appendix A test vector.
"""

import base64
import hashlib
import hmac
import os
import time
from typing import Dict, Optional, Tuple
from urllib.parse import urlsplit

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RECORD_SIZE = 4096


def b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def private_key(raw_b64u: str) -> ec.EllipticCurvePrivateKey:
    """VAPID private key as stored in .env: the raw 32-byte scalar, base64url."""
    d = b64u_decode(raw_b64u)
    if len(d) != 32:
        raise ValueError("VAPID_PRIVATE_KEY must be 32 bytes (base64url)")
    return ec.derive_private_key(int.from_bytes(d, "big"), ec.SECP256R1())


def public_bytes(key: ec.EllipticCurvePrivateKey) -> bytes:
    return key.public_key().public_bytes(serialization.Encoding.X962,
                                         serialization.PublicFormat.UncompressedPoint)


def generate_private_key() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return b64u_encode(key.private_numbers().private_value.to_bytes(32, "big"))


def public_key_b64u(raw_private_b64u: str) -> str:
    """applicationServerKey for PushManager.subscribe()."""
    return b64u_encode(public_bytes(private_key(raw_private_b64u)))


def _hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def encrypt(plaintext: bytes, ua_public_b64u: str, auth_b64u: str, *,
            salt: Optional[bytes] = None,
            as_key: Optional[ec.EllipticCurvePrivateKey] = None) -> bytes:
    """One aes128gcm record (RFC 8291 section 3/4). salt/as_key are only fixed in tests."""
    ua_public = b64u_decode(ua_public_b64u)
    auth = b64u_decode(auth_b64u)
    if len(auth) != 16 or len(ua_public) != 65:
        raise ValueError("invalid subscription keys")
    salt = salt or os.urandom(16)
    as_key = as_key or ec.generate_private_key(ec.SECP256R1())
    as_public = public_bytes(as_key)
    peer = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_public)
    ecdh = as_key.exchange(ec.ECDH(), peer)
    prk_key = _hmac(auth, ecdh)
    ikm = _hmac(prk_key, b"WebPush: info\x00" + ua_public + as_public + b"\x01")
    prk = _hmac(salt, ikm)
    cek = _hmac(prk, b"Content-Encoding: aes128gcm\x00\x01")[:16]
    nonce = _hmac(prk, b"Content-Encoding: nonce\x00\x01")[:12]
    if len(plaintext) + 1 + 16 > RECORD_SIZE:
        raise ValueError("push payload too large")
    body = AESGCM(cek).encrypt(nonce, plaintext + b"\x02", None)
    header = salt + RECORD_SIZE.to_bytes(4, "big") + bytes([len(as_public)]) + as_public
    return header + body


def vapid_headers(endpoint: str, raw_private_b64u: str, subject: str,
                  now: Optional[float] = None) -> Dict[str, str]:
    """Authorization header (RFC 8292). Valid 12 h; aud = push service origin."""
    parts = urlsplit(endpoint)
    key = private_key(raw_private_b64u)
    claims = {"aud": f"{parts.scheme}://{parts.netloc}",
              "exp": int((now or time.time()) + 12 * 3600), "sub": subject}
    token = jwt.encode(claims, key, algorithm="ES256")
    return {"Authorization": f"vapid t={token}, k={b64u_encode(public_bytes(key))}"}


def build_request(endpoint: str, p256dh: str, auth: str, payload: bytes,
                  raw_private_b64u: str, subject: str, ttl: int = 3600,
                  urgency: str = "normal") -> Tuple[Dict[str, str], bytes]:
    body = encrypt(payload, p256dh, auth)
    headers = {"Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream",
               "TTL": str(ttl), "Urgency": urgency}
    headers.update(vapid_headers(endpoint, raw_private_b64u, subject))
    return headers, body
