import os

import pytest

# Tests must never pick up a developer's .env or production settings.
os.environ["ENV"] = "test"
os.environ.pop("DATABASE_URL", None)
os.environ.pop("JWT_SECRET", None)
os.environ.pop("SIGNING_MASTER_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def settings():
    return Settings(_env_file=None, env="test")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c
