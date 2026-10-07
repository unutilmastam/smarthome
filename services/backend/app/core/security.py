"""Password/PIN hashing (Argon2id), JWT access tokens, opaque token helpers."""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

ACCESS_TOKEN_TTL = timedelta(minutes=15)
REFRESH_TOKEN_TTL = timedelta(days=30)
JWT_ALG = "HS256"

_hasher = PasswordHasher()  # Argon2id by default
# Used when the email does not exist, so timing is the same as a real check.
_DUMMY_HASH = _hasher.hash("dummy-password-for-constant-time-" + secrets.token_hex(8))


def hash_secret(plain: str) -> str:
    return _hasher.hash(plain)


def verify_secret(stored_hash: Optional[str], plain: str) -> bool:
    try:
        return _hasher.verify(stored_hash or _DUMMY_HASH, plain) and stored_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _hasher.check_needs_rehash(stored_hash)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


# ---- refresh tokens: "<session_uuid>.<secret>" --------------------------------

def make_refresh_token(session_id: uuid.UUID) -> Tuple[str, str]:
    secret = new_token()
    return f"{session_id}.{secret}", sha256_hex(secret)


def parse_refresh_token(token: str) -> Optional[Tuple[uuid.UUID, str]]:
    sid, sep, secret = token.partition(".")
    if not sep or not secret:
        return None
    try:
        return uuid.UUID(sid), sha256_hex(secret)
    except ValueError:
        return None


# ---- access tokens ----------------------------------------------------------------

def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID, secret: str,
                        now: Optional[datetime] = None) -> Tuple[str, datetime]:
    now = now or datetime.now(timezone.utc)
    exp = now + ACCESS_TOKEN_TTL
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALG), exp


def decode_access_token(token: str, secret: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, secret, algorithms=[JWT_ALG], options={"require": ["exp", "sub", "sid"]}
        )
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "access":
        return None
    return payload
