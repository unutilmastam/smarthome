"""Real-time broker access from the backend (ADR 0008).

The backend never keeps an MQTT connection (shared hosting): it publishes through
the broker's HTTP API. Every call is best-effort; polling stays the fallback.
"""

import json
import logging
from typing import List, Optional, Protocol

import httpx

log = logging.getLogger("realtime")


class RealtimeError(Exception):
    pass


def topic_cmd(home_id) -> str:
    return f"sh/v1/{home_id}/cmd"


def topic_home(home_id) -> str:
    return f"sh/v1/{home_id}/#"


class Realtime(Protocol):
    enabled: bool

    def publish(self, topic: str, payload: dict, qos: int = 1, retain: bool = False) -> None: ...

    def set_read_only_user(self, username: str, password: str, topics: List[str]) -> None: ...


class NullRealtime:
    enabled = False

    def publish(self, topic, payload, qos=1, retain=False):
        return None

    def set_read_only_user(self, username, password, topics):
        raise RealtimeError("realtime disabled")


class EmqxServerless:
    """EMQX Cloud Serverless HTTP API (basic auth with App ID / App Secret).

    publish: POST {api}/publish {"topic","payload","qos","retain"} (documented).
    users/ACL: EMQX 5 built-in database paths — NOT yet verified against a real
    Serverless deployment (ADR 0008, "Tasdiqlanishi kerak").
    """

    enabled = True
    USERS = "/authentication/password_based:built_in_database/users"
    RULES = "/authorization/sources/built_in_database/rules/users"

    def __init__(self, api_base: str, app_id: str, app_secret: str,
                 client: Optional[httpx.Client] = None, timeout: float = 3.0):
        self.base = api_base.rstrip("/")
        self.client = client or httpx.Client(timeout=timeout)
        self.auth = (app_id, app_secret)

    def _req(self, method: str, path: str, body) -> httpx.Response:
        try:
            return self.client.request(method, self.base + path, json=body, auth=self.auth)
        except httpx.HTTPError as exc:
            raise RealtimeError(f"{method} {path}: {exc.__class__.__name__}") from exc

    def _ok(self, r: httpx.Response, what: str) -> None:
        if r.status_code >= 300:
            raise RealtimeError(f"{what}: HTTP {r.status_code} {r.text[:200]}")

    def publish(self, topic: str, payload: dict, qos: int = 1, retain: bool = False) -> None:
        r = self._req("POST", "/publish", {
            "topic": topic, "payload": json.dumps(payload, separators=(",", ":")),
            "qos": qos, "retain": retain})
        self._ok(r, "publish")

    def set_read_only_user(self, username: str, password: str, topics: List[str]) -> None:
        r = self._req("PUT", f"{self.USERS}/{username}", {"password": password})
        if r.status_code == 404:
            r = self._req("POST", self.USERS, {"user_id": username, "password": password})
        self._ok(r, "user upsert")
        rules = [{"topic": t, "permission": "allow", "action": "subscribe"} for t in topics]
        rules.append({"topic": "#", "permission": "deny", "action": "all"})
        r = self._req("PUT", f"{self.RULES}/{username}", {"username": username, "rules": rules})
        if r.status_code == 404:
            r = self._req("POST", self.RULES, [{"username": username, "rules": rules}])
        self._ok(r, "acl upsert")


def build_realtime(settings) -> Realtime:
    if settings.realtime_provider == "emqx_serverless":
        return EmqxServerless(settings.emqx_api_base, settings.emqx_app_id,
                              settings.emqx_app_secret)
    return NullRealtime()
