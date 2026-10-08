"""Uzbek texts for Telegram / Push (ADR 0014). The PWA uses its own i18n keys
(event.<type>, notify.<kind>) with the same data; these mirror apps/web uz.json."""

from datetime import datetime
from typing import Any, Callable, Dict
from zoneinfo import ZoneInfo

EVENT_TEXT: Dict[str, str] = {
    "cover.left_open": "Darvoza {minutes} daqiqadan beri ochiq qoldi",
    "cover.obstructed": "Fotoelement to'sildi",
    "cover.travel_timeout": "Darvoza oxiriga yetmadi (gerkon javob bermadi)",
    "cover.sensor_conflict": "Gerkonlar bir-biriga zid — darvoza bloklandi",
    "climate.no_effect": "Konditsioner ta'sir qilmayapti: {minutes} daqiqada harorat o'zgarmadi",
    "valve.runtime_limit": "Klapan maksimal vaqtda o'zi yopildi ({max_runtime_s} s)",
    "valve.no_flow": "Suv kelmayapti — klapan yopildi",
    "valve.flow_while_closed": "Yopiq klapandan suv oqyapti!",
    "valve.emergency_stop": "Favqulodda tugma bosildi — klapan yopildi",
    "alarm.armed": "Qo'riqlash yoqildi",
    "alarm.disarmed": "Qo'riqlash o'chirildi",
    "alarm.arm_refused": "Yoqilmadi: ochiq zona ({zones})",
    "alarm.entry_delay": "Kirish: {zone} — {seconds} s ichida o'chiring",
    "alarm.triggered": "SIGNAL: {zone}",
    "alarm.sensor_offline": "Zona datchigi aloqasiz: {zone}",
    "alarm.siren_timeout": "Sirena {seconds} s dan keyin to'xtadi (signal hali faol)",
}

SYSTEM_TEXT: Dict[str, str] = {
    "hub.offline": "Hub aloqasiz: {minutes} daqiqadan beri javob yo'q",
    "hub.online": "Hub qayta ulandi",
    "device.offline": "Qurilma aloqasiz: {device}",
    "device.online": "Qurilma qayta ulandi: {device}",
    "test": "Sinov xabari: bildirishnomalar ishlayapti",
    "hub.broker_down": "Uydagi MQTT broker ishlamayapti — qurilmalarga buyruq yetmaydi",
    "hub.broker_ok": "MQTT broker tiklandi",
    "hub.data_disk_full": "Hub diski to'lmoqda: {pct}% — navbatdagi ma'lumotlar yo'qolishi mumkin",
    "hub.data_disk_ok": "Hub diskida yana joy bor",
    "hub.nvr_disk_full": "Kamera yozuvlari diski {pct}% to'ldi",
    "hub.nvr_disk_ok": "Kamera yozuvlari diskida yana joy bor",
}

SEVERITY_MARK = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}


class _Safe(dict):
    def __missing__(self, key: str) -> str:   # never crash on a missing field; show "?"
        return "?"


def _fmt(template: str, data: Dict[str, Any]) -> str:
    return template.format_map(_Safe(data))


def event_params(data: Dict[str, Any], name: Callable[[str], str]) -> Dict[str, Any]:
    """Same derived params as apps/web EventFeed; zone keys become device names."""
    p = dict(data)
    if isinstance(p.get("open_s"), (int, float)):
        p["minutes"] = round(p["open_s"] / 60)
    if isinstance(p.get("open_zones"), list):
        p["zones"] = ", ".join(name(z) for z in p["open_zones"])
    if isinstance(p.get("zone"), str):
        p["zone"] = name(p["zone"])
    return p


def event_title(type_: str, data: Dict[str, Any], name: Callable[[str], str]) -> str:
    template = EVENT_TEXT.get(type_)
    return _fmt(template, event_params(data, name)) if template else type_


def system_title(kind: str, data: Dict[str, Any]) -> str:
    return _fmt(SYSTEM_TEXT.get(kind, kind), data)


def local_time(ts: datetime, tz: str) -> str:
    try:
        zone = ZoneInfo(tz)
    except Exception:  # unknown tz name: show UTC rather than guess
        return ts.strftime("%d.%m %H:%M UTC")
    return ts.astimezone(zone).strftime("%d.%m %H:%M")


def message(severity: str, title: str, body: str, where: str, when: str, reminder: bool) -> str:
    """Plain text (no parse_mode): nothing from a device can inject markup."""
    head = f"{SEVERITY_MARK.get(severity, '')} {title}".strip()
    if reminder:
        head = "🔁 Eslatma (hali tasdiqlanmagan)\n" + head
    lines = [head]
    if body:
        lines.append(body)
    lines.append(f"🏠 {where} · 🕒 {when}")
    return "\n".join(lines)
