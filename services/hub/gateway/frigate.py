"""Frigate status -> camera capability (stream_available, recording, disk_usage_pct).

Reads Frigate's HTTP API on the hub's internal network. Only STATUS leaves the hub;
video, snapshots and clips never do (ADR 0006).
"""

from typing import Dict, Optional

import httpx

DISK_WARNING_PCT = 85.0
RECORDINGS_PATH = "/media/frigate/recordings"


class FrigateError(Exception):
    pass


class FrigateMonitor:
    def __init__(self, base_url: str, client: Optional[httpx.AsyncClient] = None):
        self.base = base_url.rstrip("/")
        self.client = client or httpx.AsyncClient(timeout=5.0)

    async def _get(self, path: str) -> dict:
        try:
            r = await self.client.get(self.base + path)
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise FrigateError(f"{path}: {exc.__class__.__name__}") from exc

    async def snapshot(self) -> dict:
        """{"cameras": {name: {"stream_available", "recording"}}, "disk_usage_pct": float|None}"""
        stats = await self._get("/api/stats")
        config = await self._get("/api/config")
        return parse(stats, config)


def parse(stats: dict, config: dict) -> dict:
    cams: Dict[str, dict] = {}
    for name, cfg in (config.get("cameras") or {}).items():
        st = (stats.get("cameras") or {}).get(name)
        fps = (st or {}).get("camera_fps")
        cams[name] = {
            # No stats for the camera -> we do not know; never assume it streams.
            "stream_available": (fps > 0) if isinstance(fps, (int, float)) else None,
            "recording": bool(((cfg or {}).get("record") or {}).get("enabled", False)),
        }
    storage = ((stats.get("service") or {}).get("storage") or {}).get(RECORDINGS_PATH) or {}
    total, used = storage.get("total"), storage.get("used")
    disk = round(used / total * 100.0, 1) if isinstance(total, (int, float)) and total > 0 \
        and isinstance(used, (int, float)) else None
    return {"cameras": cams, "disk_usage_pct": disk}
