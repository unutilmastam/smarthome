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
