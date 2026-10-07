from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.responses import ok

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    return ok({"status": "ok", "version": settings.app_version})
