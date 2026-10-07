from typing import Optional

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings

API_PREFIX = "/api/v1"


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="SmartHome Control Center API",
        version=settings.app_version,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()
