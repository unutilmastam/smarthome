import uuid
from typing import Dict, List, Optional

from pydantic import Field

from app.schemas.common import Model

KEY_PATTERN = r"^[a-z][a-z0-9_]{1,63}$"
# UI icon key only (apps/web/src/components/Icon.tsx); never affects state.
ICON_PATTERN = r"^[a-z][a-z0-9_]{0,31}$"


class DeviceIn(Model):
    key: str = Field(pattern=KEY_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    room_id: Optional[uuid.UUID] = None
    adapter: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_\-]+$")
    protocol: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_\-]+$")
    model: Optional[str] = Field(default=None, max_length=120)
    icon: Optional[str] = Field(default=None, pattern=ICON_PATTERN)
    # capability -> config (e.g. {"report_interval_s": 60})
    capabilities: Dict[str, dict] = Field(min_length=1)
    unsupported: List[str] = Field(default_factory=list)
    fail_safe_state: Optional[dict] = None
    enabled: bool = True


class DevicePatch(Model):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    room_id: Optional[uuid.UUID] = None
    model: Optional[str] = Field(default=None, max_length=120)
    icon: Optional[str] = Field(default=None, pattern=ICON_PATTERN)
    capabilities: Optional[Dict[str, dict]] = Field(default=None, min_length=1)
    unsupported: Optional[List[str]] = None
    fail_safe_state: Optional[dict] = None
    enabled: Optional[bool] = None
