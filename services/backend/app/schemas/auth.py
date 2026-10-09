from typing import Optional

from pydantic import Field, field_validator

from app.schemas.common import Model

PASSWORD_MIN = 10


def normalize_email(v: str) -> str:
    v = v.strip().lower()
    if "@" not in v or v.startswith("@") or v.endswith("@") or " " in v or len(v) > 254:
        raise ValueError("invalid email")
    return v


class LoginIn(Model):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=256)

    _norm = field_validator("email")(normalize_email)


class RefreshIn(Model):
    refresh_token: str = Field(min_length=10, max_length=200)


class PasswordChangeIn(Model):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=PASSWORD_MIN, max_length=256)


class PinSetIn(Model):
    password: str = Field(min_length=1, max_length=256)
    pin: str = Field(pattern=r"^\d{4,8}$")


class UserOut(Model):
    id: str
    email: str
    name: str
    has_pin: bool


class TokenPairOut(Model):
    access_token: str
    access_expires_at: str
    refresh_token: str
    token_type: str = "bearer"
    user: Optional[UserOut] = None
