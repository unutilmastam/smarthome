from typing import Optional

from fastapi import Query
from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class Page:
    def __init__(
        self,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        self.limit = limit
        self.offset = offset

    def meta(self, total: int) -> dict:
        return {"limit": self.limit, "offset": self.offset, "total": total}


def strip_or_none(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    return v or None
