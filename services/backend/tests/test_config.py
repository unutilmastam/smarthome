import secrets

import pytest

from app.core.config import DEV_JWT_SECRET, ConfigError, Settings

PG = "postgresql+psycopg://u:p@localhost:5432/smarthome"


def prod(**kw):
    base = dict(
        _env_file=None,
        env="production",
        database_url=PG,
        jwt_secret=secrets.token_hex(32),
        signing_master_key=secrets.token_hex(32),
    )
    base.update(kw)
    return Settings(**base)


def test_production_with_real_secrets_ok():
    s = prod()
    assert s.is_production


def test_dev_gets_dev_secrets():
    s = Settings(_env_file=None, env="development")
    assert s.jwt_secret == DEV_JWT_SECRET
    assert not s.is_production


@pytest.mark.parametrize(
    "overrides",
    [
        {"database_url": "sqlite:///./dev.db"},
        {"jwt_secret": ""},
        {"signing_master_key": ""},
        {"jwt_secret": DEV_JWT_SECRET},
        {"signing_master_key": "short"},
        {"jwt_secret": "x" * 20 + "change-me" + "x" * 20},
    ],
)
def test_production_rejects_unsafe_config(overrides):
    with pytest.raises((ConfigError, ValueError)):
        prod(**overrides)


def test_production_rejects_same_secret_twice():
    key = secrets.token_hex(32)
    with pytest.raises((ConfigError, ValueError)):
        prod(jwt_secret=key, signing_master_key=key)


def test_contracts_dir_resolves_to_repo():
    s = Settings(_env_file=None, env="test")
    assert (s.contracts_dir / "capabilities.json").is_file()
