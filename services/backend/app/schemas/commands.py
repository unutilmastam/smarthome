import uuid
from typing import Optional

from pydantic import Field

from app.schemas.common import Model


class CommandIn(Model):
    device_id: uuid.UUID
    capability: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=40)
    action: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=40)
    params: dict = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_\-:.]+$")
    confirm_pin: Optional[str] = Field(default=None, pattern=r"^\d{4,8}$")
