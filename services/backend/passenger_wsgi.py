"""cPanel "Setup Python App" entry point (Passenger, WSGI).

FastAPI is ASGI; a2wsgi adapts it to WSGI. Passenger looks for `application`.
The app is mounted at Application URL "/api" (runbook: docs/runbooks/deploy.md),
so Passenger sends SCRIPT_NAME="/api" and PATH_INFO="/v1/...". Our routes are
"/api/v1/...", so the prefix is put back before FastAPI sees the request.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from a2wsgi import ASGIMiddleware  # noqa: E402

from app.main import app  # noqa: E402

_asgi = ASGIMiddleware(app)


def application(environ, start_response):
    script = environ.get("SCRIPT_NAME", "").rstrip("/")
    if script:
        environ = dict(environ)
        environ["PATH_INFO"] = script + environ.get("PATH_INFO", "")
        environ["SCRIPT_NAME"] = ""
    return _asgi(environ, start_response)
