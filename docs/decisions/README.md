# Arxitektura qarorlari (ADR)

Har bir muhim qaror shu papkada alohida faylda: `NNNN-qisqa-nom.md`.
Format: **Kontekst → Qaror → Oqibatlar** (+ ko'rib chiqilgan muqobillar).

Holatlar: `taklif` · `qabul qilingan` · `almashtirilgan (→ NNNN)` · `bekor qilingan`.
Qabul qilingan ADR o'zgartirilmaydi — yangi ADR bilan almashtiriladi.

| # | Qaror | Holat |
|---|---|---|
| [0001](0001-shared-hosting-and-home-hub.md) | Cloud = yengil API (cPanel shared hosting), og'ir ish = uydagi Hub | qabul qilingan |
| [0002](0002-postgresql.md) | Cloud DB — PostgreSQL (cPanel) | qabul qilingan |
| [0003](0003-single-pwa.md) | Bitta React PWA (React Native emas) | qabul qilingan |
| [0004](0004-command-signing-hmac.md) | Buyruq imzosi: HMAC-SHA256, master kalitdan hosil qilingan uy kaliti | qabul qilingan |
| [0005](0005-polling-first-mqtt-later.md) | Avval HTTPS polling, MQTT broker keyin (polling zaxira bo'lib qoladi) | qabul qilingan |
| [0006](0006-video-stays-home.md) | Video uydan chiqmaydi | qabul qilingan |
| [0007](0007-command-envelope-fields.md) | Buyruq payload'iga `device_key` va `capability` | qabul qilingan |
| [0008](0008-managed-mqtt-emqx-serverless.md) | Managed MQTT: EMQX Cloud Serverless (polling zaxira) | qabul qilingan |
| [0009](0009-web-token-storage.md) | PWA: access xotirada, refresh `HttpOnly` cookie | qabul qilingan |
| [0010](0010-esphome-speaks-local-contract.md) | ESPHome lokal shartnomani o'zi gapiradi (Hub adapteri yo'q) | qabul qilingan |
| [0011](0011-automatic-deploy-and-expand-only-migrations.md) | Avtomatik deploy, zaxira, avtomatik qaytish, expand-only migratsiyalar | qabul qilingan |
| [0012](0012-events-alarm-on-hub-and-feedback-attributes.md) | Voqealar oqimi, Hub'dagi xavfsizlik tizimi, qaytar aloqa atributlari (fotoelement, tok, oqim) | qabul qilingan |
| [0013](0013-automations-on-hub.md) | Avtomatika Hub'da: format, high-risk taqiqi, sikl tekshiruvi, qo'lda boshqaruv ustunligi | qabul qilingan |
| [0014](0014-notifications-push-telegram.md) | Bildirishnomalar: Web Push + Telegram, tasdiqlash, Hub nazoratchisi | qabul qilingan |

## Shablon

```
# NNNN — <Qaror nomi>

- Holat: taklif | qabul qilingan | almashtirilgan (→ NNNN)
- Sana: YYYY-MM-DD

## Kontekst
## Qaror
## Ko'rib chiqilgan muqobillar
## Oqibatlar
### Ijobiy
### Salbiy / xavflar
## Tasdiqlanishi kerak
```
