"""Uniform API response envelope: {"data": ..., "error": ..., "meta": {...}}."""

from typing import Any, Dict, Optional


def ok(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"data": data, "error": None, "meta": meta or {}}


def error_body(code: str, message: str, details: Any = None) -> Dict[str, Any]:
    err: Dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {"data": None, "error": err, "meta": {}}
