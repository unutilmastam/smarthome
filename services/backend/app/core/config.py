"""Application settings (pydantic-settings, loaded from environment / .env)."""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

DEV_JWT_SECRET = "dev-insecure-jwt-secret-change-me-0000000000"
DEV_SIGNING_MASTER_KEY = "dev-insecure-signing-master-key-change-me-00"
MIN_SECRET_LENGTH = 32
INSECURE_MARKERS = ("dev-insecure", "change-me", "changeme", "secret", "password")


class Environment(str, Enum):
    development = "development"
    test = "test"
    production = "production"


class ConfigError(ValueError):
    """Raised when settings are unsafe for the selected environment."""


def _default_contracts_dir() -> Path:
    # Repo layout: services/backend -> ../../packages/contracts.
    # Deployed layout (cPanel): contracts copied next to the app.
    repo = BACKEND_DIR.parents[1] / "packages" / "contracts"
    return repo if repo.is_dir() else BACKEND_DIR / "contracts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    env: Environment = Environment.development
    app_version: str = "0.1.0"
    database_url: str = "sqlite:///./dev.db"
    jwt_secret: str = Field(default="")
    signing_master_key: str = Field(default="")
    contracts_dir: Optional[Path] = None
    # Hub is considered online if its last heartbeat is newer than this.
    hub_online_window_s: int = 90
    # Values older than stale_factor x report_interval_s (if configured) are stale.
    stale_factor: int = 3

    @model_validator(mode="after")
    def _apply_defaults_and_check(self) -> "Settings":
        if self.contracts_dir is None:
            self.contracts_dir = _default_contracts_dir()

        if self.env is Environment.production:
            problems = []
            if self.database_url.lower().startswith("sqlite"):
                problems.append("DATABASE_URL: SQLite is not allowed in production")
            for name in ("jwt_secret", "signing_master_key"):
                value = getattr(self, name)
                if not value:
                    problems.append(f"{name.upper()}: required in production")
                elif len(value) < MIN_SECRET_LENGTH:
                    problems.append(
                        f"{name.upper()}: must be at least {MIN_SECRET_LENGTH} characters"
                    )
                elif any(marker in value.lower() for marker in INSECURE_MARKERS):
                    problems.append(f"{name.upper()}: development/placeholder value")
            if self.jwt_secret and self.jwt_secret == self.signing_master_key:
                problems.append("JWT_SECRET and SIGNING_MASTER_KEY must differ")
            if problems:
                raise ConfigError("Unsafe production configuration: " + "; ".join(problems))
        else:
            if not self.jwt_secret:
                self.jwt_secret = DEV_JWT_SECRET
            if not self.signing_master_key:
                self.signing_master_key = DEV_SIGNING_MASTER_KEY
        return self

    @property
    def is_production(self) -> bool:
        return self.env is Environment.production


@lru_cache
def get_settings() -> Settings:
    return Settings()
