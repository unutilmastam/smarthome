# packages/contracts — yagona shartnoma

Backend, Hub va PWA shu fayllardan foydalanadi. O'zgartirish faqat shu yerda.

| Fayl | Mazmuni |
|---|---|
| `capabilities.json` | Qurilma imkoniyatlari: atributlar, harakatlar (params — JSON Schema), ruxsat, xavf, `confirm_attribute` |
| `roles.json` | Rol → ruxsat matritsasi (ARCHITECTURE 9). Backend va Hub ikkalasi ham tekshiradi |
| `test-vectors/signing.json` | Buyruq imzosi test vektorlari (Backend va Hub) |
| `schemas/local-mqtt.schema.json` | Lokal MQTT xabarlari Hub ↔ qurilma (ARCHITECTURE 5) |
| `schemas/capabilities.schema.json` | `capabilities.json` formati |
| `schemas/value.schema.json` | Qiymat + ishonch (`source`, `quality`, `ts`) — ARCHITECTURE 4.2 |
| `schemas/command-envelope.schema.json` | Imzolangan buyruq Backend → Hub — ARCHITECTURE 4.4, ADR 0004, 0007 |
| `schemas/ack.schema.json` | Buyruq natijasi Hub → Backend |
| `schemas/state-report.schema.json` | Holat hisoboti Hub → Backend (`POST /hub/report`) |

Barcha sxemalar JSON Schema draft 2020-12. Vaqt — faqat UTC (`...Z`).

Test: `pip install -r requirements-test.txt && python -m pytest packages/contracts`
