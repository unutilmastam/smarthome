"""Application settings (pydantic-settings, loaded from environment / .env)."""

from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, model_validator
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
    # Command lifetimes (ARCHITECTURE 4.3).
    command_ttl_s: int = 10
    command_ttl_high_risk_s: int = 5
    # sent but never acked -> timeout this long after expires_at
    command_ack_grace_s: int = 30
    # acked but never confirmed (confirm_attribute capabilities) -> timeout
    command_confirm_timeout_s: int = 60
    command_rate_limit_per_min: int = 60
    # Login attempts per IP per 5 minutes (Faza 2). Raised only for local e2e runs.
    login_ip_limit: int = 20
    # Real-time (ADR 0008). "none" = polling only.
    realtime_provider: str = "none"
    emqx_api_base: Optional[str] = None
    emqx_app_id: Optional[str] = None
    emqx_app_secret: Optional[str] = None
    # What the PWA connects to, e.g. wss://xxxx.ala.eu-central-1.emqxsl.com:8084/mqtt
    realtime_wss_url: Optional[str] = None
    realtime_credentials_ttl_s: int = 12 * 3600
    # ADR 0009: refresh token cookie for the PWA
    cookie_secure: bool = True
    # OpenAPI/Swagger UI. Off in production unless explicitly enabled (ARCHITECTURE 8).
    docs_enabled: Optional[bool] = None
    # Notifications (ADR 0014). Secrets live only in .env (deploy.sh writes them on the server).
    public_base_url: Optional[str] = None            # https://home.example.uz (Telegram webhook)
    telegram_bot_token: Optional[str] = None
    telegram_webhook_secret: Optional[str] = None
    telegram_bot_username: Optional[str] = None      # optional: asked from getMe when missing
    vapid_private_key: Optional[str] = None          # raw P-256 scalar, base64url
    vapid_subject: Optional[str] = None              # mailto:... or https://... (defaults to public URL)
    # Watchdog: hub silent this long -> critical (cron runs every minute -> detected < 3 min).
    hub_offline_alert_s: int = 150
    device_offline_alert_s: int = 300
    # Critical and not acked after this long -> sent once more.
    notify_reminder_s: int = 600

    @model_validator(mode="after")
    def _apply_defaults_and_check(self) -> "Settings":
        if self.contracts_dir is None:
            self.contracts_dir = _default_contracts_dir()
        if self.docs_enabled is None:
            self.docs_enabled = self.env is not Environment.production

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
            if self.realtime_provider == "emqx_serverless":
                for name in ("emqx_api_base", "emqx_app_id", "emqx_app_secret",
                             "realtime_wss_url"):
                    if not getattr(self, name):
                        problems.append(f"{name.upper()}: required for emqx_serverless")
                if self.realtime_wss_url and not self.realtime_wss_url.startswith("wss://"):
                    problems.append("REALTIME_WSS_URL must use wss://")
            if not self.cookie_secure:
                problems.append("COOKIE_SECURE must be true in production")
            if self.telegram_bot_token and len(self.telegram_webhook_secret or "") < MIN_SECRET_LENGTH:
                problems.append("TELEGRAM_WEBHOOK_SECRET: required (>= 32 chars) with a bot token")
            if self.public_base_url and not self.public_base_url.startswith("https://"):
                problems.append("PUBLIC_BASE_URL must use https://")
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

    @field_validator("realtime_provider")
    @classmethod
    def _provider(cls, v: str) -> str:
        if v not in ("none", "emqx_serverless"):
            raise ValueError("REALTIME_PROVIDER must be 'none' or 'emqx_serverless'")
        return v

    @property
    def push_subject(self) -> Optional[str]:
        return self.vapid_subject or self.public_base_url

    @property
    def is_production(self) -> bool:
        return self.env is Environment.production


@lru_cache
def get_settings() -> Settings:
    return Settings()
