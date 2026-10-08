"""Outbound channels (ADR 0014): Telegram Bot API and Web Push over HTTPS.

Only outbound connections from the cloud. Tests replace the HTTP transport
(set_transport) — nothing here pretends a message was sent when it was not.
"""

import json
from functools import lru_cache
from typing import Any, Dict, Optional

import httpx

from app.core.config import Settings
from app.services import webpush

_transport: Optional[httpx.BaseTransport] = None


def set_transport(t: Optional[httpx.BaseTransport]) -> None:
    """Tests only: route all channel HTTP through a mock transport."""
    global _transport
    _transport = t
    _bot_username.cache_clear()


def client(timeout: float = 5.0) -> httpx.Client:
    return httpx.Client(timeout=timeout, transport=_transport)


class TelegramError(Exception):
    def __init__(self, status: int, description: str):
        super().__init__(f"telegram {status}: {description}")
        self.status = status
        self.description = description


def telegram_enabled(s: Settings) -> bool:
    return bool(s.telegram_bot_token)


def telegram(s: Settings, method: str, payload: Dict[str, Any],
             http: Optional[httpx.Client] = None) -> Any:
    if not s.telegram_bot_token:
        raise TelegramError(0, "bot not configured")
    own = http is None
    http = http or client()
    try:
        r = http.post(f"https://api.telegram.org/bot{s.telegram_bot_token}/{method}", json=payload)
    except httpx.HTTPError as e:
        raise TelegramError(0, type(e).__name__)
    finally:
        if own:
            http.close()
    try:
        body = r.json()
    except ValueError:
        raise TelegramError(r.status_code, "non-JSON response")
    if not body.get("ok"):
        raise TelegramError(body.get("error_code", r.status_code), str(body.get("description", ""))[:150])
    return body.get("result")


@lru_cache(maxsize=4)
def _bot_username(token: str) -> Optional[str]:
    try:
        me = telegram(Settings(_env_file=None, telegram_bot_token=token), "getMe", {})
    except TelegramError:
        return None
    return me.get("username")


def bot_username(s: Settings) -> Optional[str]:
    if s.telegram_bot_username:
        return s.telegram_bot_username.lstrip("@")
    return _bot_username(s.telegram_bot_token) if s.telegram_bot_token else None


def push_enabled(s: Settings) -> bool:
    return bool(s.vapid_private_key and s.push_subject)


def push(s: Settings, endpoint: str, p256dh: str, auth: str, payload: Dict[str, Any],
         urgency: str = "normal", http: Optional[httpx.Client] = None) -> int:
    """Returns the push service HTTP status (201 = accepted). Network error -> 0."""
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    headers, body = webpush.build_request(endpoint, p256dh, auth, data, s.vapid_private_key,
                                          s.push_subject, ttl=24 * 3600, urgency=urgency)
    own = http is None
    http = http or client()
    try:
        return http.post(endpoint, content=body, headers=headers).status_code
    except httpx.HTTPError:
        return 0
    finally:
        if own:
            http.close()
