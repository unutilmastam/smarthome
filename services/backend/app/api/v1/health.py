from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.responses import ok

router = APIRouter(tags=["health"])


def build_id() -> str:
    """Git commit of the deployed release (written by infra/cpanel/build_release.sh).

    The deploy health check waits for exactly this value, so an old Passenger process
    that is still answering can never be mistaken for a successful deploy."""
    try:
        from app._build import BUILD  # type: ignore[import-not-found]
    except ImportError:
        return "dev"
    return BUILD


@router.get("/health")
def health(settings: Settings = Depends(get_settings)):
    return ok({"status": "ok", "version": settings.app_version, "build": build_id()})
