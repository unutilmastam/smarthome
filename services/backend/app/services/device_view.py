"""Builds the device representation (ARCHITECTURE 4.2).

Every attribute of every capability is present. Nothing is invented:
  - unsupported by hardware      -> quality not_supported, value null
  - never reported               -> quality unknown, value null
  - hub offline / device offline -> good values downgraded to stale
  - older than stale_factor x report_interval_s -> stale
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

from app.core.config import Settings
from app.core.contracts import Contracts
from app.db.types import utcnow
from app.models import Device, Hub


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat().replace("+00:00", "Z") if dt else None


def hub_is_online(hub: Optional[Hub], settings: Settings, now: Optional[datetime] = None) -> bool:
    if hub is None or hub.status != "active" or hub.last_seen is None:
        return False
    now = now or utcnow()
    return now - hub.last_seen <= timedelta(seconds=settings.hub_online_window_s)


def hub_view(hub: Hub, settings: Settings) -> dict:
    return {
        "id": str(hub.id),
        "home_id": str(hub.home_id),
        "name": hub.name,
        "status": hub.status,
        "online": hub_is_online(hub, settings),
        "last_seen": iso(hub.last_seen),
        "version": hub.version,
        "tailnet_host": hub.tailnet_host,
        "lan_host": hub.lan_host,
        "created_at": iso(hub.created_at),
        "revoked_at": iso(hub.revoked_at),
    }


def _value(value, unit, source, quality, ts) -> dict:
    out = {"value": value, "source": source, "quality": quality, "ts": iso(ts)}
    if unit:
        out["unit"] = unit
    return out


def device_view(device: Device, contracts: Contracts, settings: Settings,
                hub: Optional[Hub], now: Optional[datetime] = None) -> dict:
    now = now or utcnow()
    online_hub = hub_is_online(hub, settings, now)
    availability = device.availability if online_hub else "unknown"
    unsupported = set(device.unsupported or [])
    stored: Dict[tuple, object] = {(s.capability, s.attribute): s for s in device.states}

    caps = {}
    for cap in device.capabilities:
        spec = contracts.capability(cap.capability)
        interval = (cap.config_json or {}).get("report_interval_s")
        attrs = {}
        for attr in spec["attributes"]:
            unit = contracts.attribute_unit(cap.capability, attr)
            if f"{cap.capability}.{attr}" in unsupported:
                attrs[attr] = _value(None, unit, "reported", "not_supported", None)
                continue
            st = stored.get((cap.capability, attr))
            if st is None or st.quality == "unknown":
                attrs[attr] = _value(None, unit, "reported", "unknown", None)
                continue
            quality = st.quality
            if quality == "good":
                too_old = (
                    isinstance(interval, (int, float)) and interval > 0 and st.ts is not None
                    and now - st.ts > timedelta(seconds=interval * settings.stale_factor)
                )
                if not online_hub or availability == "offline" or too_old:
                    quality = "stale"
            value = st.value_json if quality in ("good", "stale") else None
            attrs[attr] = _value(value, unit, st.source, quality, st.ts)
        caps[cap.capability] = {
            "permission": spec["permission"],
            "risk": spec["risk"],
            "config": cap.config_json or {},
            "attributes": attrs,
        }

    return {
        "id": str(device.id),
        "home_id": str(device.home_id),
        "room_id": str(device.room_id) if device.room_id else None,
        "key": device.key,
        "name": device.name,
        "adapter": device.adapter,
        "protocol": device.protocol,
        "model": device.model,
        "icon": device.icon,
        "enabled": device.enabled,
        "fail_safe_state": device.fail_safe_state,
        "unsupported": sorted(unsupported),
        "availability": {"status": availability, "ts": iso(device.availability_ts)},
        "hub_online": online_hub,
        "capabilities": caps,
        "created_at": iso(device.created_at),
        "updated_at": iso(device.updated_at),
    }
