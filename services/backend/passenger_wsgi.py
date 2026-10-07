"""cPanel "Setup Python App" entry point (Passenger, WSGI).

FastAPI is ASGI; a2wsgi adapts it to WSGI. Passenger looks for `application`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from a2wsgi import ASGIMiddleware  # noqa: E402

from app.main import app  # noqa: E402

application = ASGIMiddleware(app)
