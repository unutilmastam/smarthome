# 0007 — Buyruq payload'iga `device_key` va `capability` qo'shiladi

- Holat: qabul qilingan
- Sana: 2026-10-07
- ADR 0004 ni to'ldiradi (imzo algoritmi o'zgarmaydi).

## Kontekst
ADR 0004 dagi payload: `{command_id, device_id, action, params, issued_at, expires_at, issued_by}`.
Faza 1 da `command-envelope.schema.json` yozilganda ikki muammo topildi:
1. Harakat nomlari capability'lar orasida takrorlanadi: `open` — `cover`, `valve`, `contactor` da bor. Faqat `action` bilan Hub qaysi capability nazarda tutilganini bilmaydi.
2. Hub va MQTT qurilmani `device_key` bilan taniydi (ARCHITECTURE 4.1). Faqat `device_id` (UUID) bo'lsa, Hub qo'shimcha xaritaga muhtoj va xarita eskirsa noto'g'ri qurilmaga buyruq ketishi mumkin.

## Qaror
Payload (imzolanadigan qism):
```
{command_id, device_id, device_key, capability, action, params,
 issued_at, expires_at, issued_by: {user_id, role}}
```
- Ikkala identifikator ham imzo ostida. Hub `device_id` va `device_key` o'z konfiguratsiyasidagi bilan **mos kelishini** tekshiradi; mos kelmasa → `rejected: unknown_device`.
- `issued_by.role` — Hub ruxsatni qayta tekshirishi uchun (ADR 0004).
- Konvert: `{"schema": 1, "payload": {...}, "signature": "<64 hex>"}` — `packages/contracts/schemas/command-envelope.schema.json`.

## Oqibatlar
- Noaniqlik yo'qoladi; imzo algoritmi o'zgarmaydi.
- Payload biroz kattalashadi (ahamiyatsiz).
