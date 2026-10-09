"""Run by deploy.sh after a healthy deploy (ADR 0014): register the Telegram webhook.

Idempotent. Without TELEGRAM_BOT_TOKEN / PUBLIC_BASE_URL it says so and exits 0:
the rest of the system works without Telegram.
"""

import logging
import sys

from app.core.config import Settings, get_settings
from app.services import channels


def run(s: Settings) -> str:
    if not s.telegram_bot_token:
        return "skipped: TELEGRAM_BOT_TOKEN not set"
    if not s.public_base_url or not s.telegram_webhook_secret:
        return "skipped: PUBLIC_BASE_URL / TELEGRAM_WEBHOOK_SECRET not set"
    url = s.public_base_url.rstrip("/") + "/api/v1/telegram/webhook"
    channels.telegram(s, "setWebhook", {
        "url": url, "secret_token": s.telegram_webhook_secret,
        "allowed_updates": ["message", "callback_query"], "drop_pending_updates": False})
    channels.telegram(s, "setMyCommands", {"commands": [
        {"command": "start", "description": "Bog'lash (ilovadagi kod bilan)"},
        {"command": "stop", "description": "Bildirishnomalarni to'xtatish"}]})
    return f"webhook set: {url}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s telegram_setup %(message)s")
    try:
        logging.info(run(get_settings()))
    except channels.TelegramError as e:   # token itself is never logged
        logging.error("failed: %s", e)
        sys.exit(1)
