from typing import Optional

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.db.session import Database

API_PREFIX = "/api/v1"


def create_app(settings: Optional[Settings] = None,
               database: Optional[Database] = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="SmartHome Control Center API",
        version=settings.app_version,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=None,
    )
    app.state.settings = settings
    app.state.db = database or Database(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    install_error_handlers(app)
    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()
