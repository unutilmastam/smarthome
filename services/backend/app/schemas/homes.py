import uuid
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from app.schemas.auth import PASSWORD_MIN, normalize_email
from app.schemas.common import Model

Name = Field(min_length=1, max_length=120)


def _tz(v: str) -> str:
    try:
        ZoneInfo(v)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("unknown timezone")
    return v


class HomeIn(Model):
    name: str = Name
    timezone: str = "Asia/Tashkent"
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    _tz = field_validator("timezone")(_tz)

    @model_validator(mode="after")
    def _both_coords(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be set together")
        return self


class HomePatch(Model):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    timezone: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @field_validator("timezone")
    @classmethod
    def _tzv(cls, v):
        return None if v is None else _tz(v)


AssignableRole = Literal["admin", "family", "guest", "viewer"]


class MemberIn(Model):
    email: str = Field(max_length=254)
    role: AssignableRole
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    # Required only when the user does not exist yet (no public registration).
    initial_password: Optional[str] = Field(default=None, min_length=PASSWORD_MIN, max_length=256)

    _norm = field_validator("email")(normalize_email)


class MemberPatch(Model):
    role: AssignableRole


class FloorIn(Model):
    name: str = Name
    level: int = Field(default=0, ge=-10, le=200)


class FloorPatch(Model):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    level: Optional[int] = Field(default=None, ge=-10, le=200)


class RoomIn(Model):
    name: str = Name
    type: Literal["indoor", "outdoor"] = "indoor"
    floor_id: Optional[uuid.UUID] = None


class RoomPatch(Model):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    type: Optional[Literal["indoor", "outdoor"]] = None
    floor_id: Optional[uuid.UUID] = None


class HubIn(Model):
    name: str = Name
