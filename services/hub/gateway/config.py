from pathlib import Path
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

HUB_DIR = Path(__file__).resolve().parents[1]


def default_contracts_dir() -> Path:
    repo = HUB_DIR.parents[1] / "packages" / "contracts"
    return repo if repo.is_dir() else HUB_DIR / "contracts"


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(HUB_DIR / ".env"), extra="ignore")

    backend_url: str
    hub_token: str
    signing_key_hex: str

    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = "gateway"
    mqtt_password: Optional[str] = None

    # Managed cloud broker (ADR 0008). Empty host = polling only.
    cloud_mqtt_host: Optional[str] = None
    cloud_mqtt_port: int = 8883
    cloud_mqtt_tls: bool = True
    cloud_mqtt_username: Optional[str] = None
    cloud_mqtt_password: Optional[str] = None

    db_path: str = "hub.sqlite3"
    contracts_dir: Optional[Path] = None

    poll_interval_s: float = 1.5
    poll_max_backoff_s: float = 60.0
    heartbeat_interval_s: float = 30.0
    config_refresh_s: float = 60.0
    full_report_interval_s: float = 60.0
    flush_interval_s: float = 1.0
    clock_skew_s: float = 5.0
    device_ack_timeout_s: float = 5.0
    default_confirm_timeout_s: float = 30.0
    executed_retention_days: int = 7
    version: str = "0.1.0"

    @model_validator(mode="after")
    def _check(self):
        if self.contracts_dir is None:
            self.contracts_dir = default_contracts_dir()
        if not self.hub_token.startswith("hub_"):
            raise ValueError("HUB_TOKEN must start with 'hub_'")
        try:
            key = bytes.fromhex(self.signing_key_hex)
        except ValueError:
            raise ValueError("SIGNING_KEY_HEX must be hex")
        if len(key) != 32:
            raise ValueError("SIGNING_KEY_HEX must be 32 bytes (64 hex chars)")
        self.backend_url = self.backend_url.rstrip("/")
        return self

    @property
    def signing_key(self) -> bytes:
        return bytes.fromhex(self.signing_key_hex)
