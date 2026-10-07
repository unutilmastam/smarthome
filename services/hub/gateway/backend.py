"""Outbound HTTPS client to the cloud backend (the hub never accepts inbound connections)."""

from typing import List, Optional

import httpx


class BackendError(Exception):
    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status

    @property
    def permanent(self) -> bool:
        """4xx other than auth/rate limit: retrying the same payload will not help."""
        return self.status is not None and 400 <= self.status < 500 \
            and self.status not in (401, 408, 429)


class BackendClient:
    def __init__(self, base_url: str, hub_token: str,
                 client: Optional[httpx.AsyncClient] = None, timeout: float = 10.0):
        self.base = base_url.rstrip("/") + "/api/v1/hub"
        self._client = client or httpx.AsyncClient(timeout=timeout)
        self._headers = {"Authorization": f"Bearer {hub_token}"}

    async def close(self) -> None:
        await self._client.aclose()

    async def _call(self, method: str, path: str, **kw) -> dict:
        try:
            r = await self._client.request(method, self.base + path, headers=self._headers, **kw)
        except httpx.HTTPError as exc:
            raise BackendError(f"{method} {path}: {exc.__class__.__name__}") from exc
        if r.status_code >= 400:
            raise BackendError(f"{method} {path}: HTTP {r.status_code} {r.text[:200]}",
                               r.status_code)
        return r.json()

    async def heartbeat(self, version: str, health: dict) -> dict:
        return await self._call("POST", "/heartbeat", json={"version": version, "health": health})

    async def commands(self) -> List[dict]:
        return (await self._call("GET", "/commands"))["data"]

    async def acks(self, acks: List[dict]) -> dict:
        return (await self._call("POST", "/acks", json={"acks": acks}))["data"]

    async def report(self, report: dict) -> dict:
        return (await self._call("POST", "/report", json=report))["data"]

    async def telemetry(self, batch: dict) -> dict:
        return (await self._call("POST", "/telemetry:batch", json=batch))["data"]

    async def config(self) -> dict:
        return (await self._call("GET", "/config"))["data"]
