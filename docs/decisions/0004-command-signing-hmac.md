# 0004 — Buyruq imzosi: HMAC-SHA256, master kalitdan hosil qilingan uy kaliti

- Holat: qabul qilingan
- Sana: 2026-10-07

## Kontekst
- Buyruqlar Hub'ga ikki yo'ldan yetadi: HTTPS polling (`GET /hub/commands`) va keyinchalik managed MQTT broker.
- Broker paroli yoki Hub tokeni o'g'irlansa, faqat ACL bilan himoya qilingan tizimda darvoza/qulfni ochish mumkin bo'lardi.
- Cloud DB sizishi ham hisobga olinishi kerak (shared hosting).
- Tarmoqda eski buyruqni qayta yuborish (replay) mumkin.

## Qaror
Har bir buyruq Backend'da imzolanadi, Hub esa imzosiz, muddati o'tgan yoki takroriy buyruqni **hech qachon bajarmaydi**.

```
payload          = {command_id, device_id, action, params, issued_at, expires_at, issued_by}
home_signing_key = HMAC-SHA256(SIGNING_MASTER_KEY, "home-signing:" + home_id)
signature        = HMAC-SHA256(home_signing_key, canonical_json(payload))
canonical_json   = UTF-8, kalitlar tartiblangan, separators (',', ':'), bo'sh joysiz
```

- `SIGNING_MASTER_KEY` — faqat cloud `.env` da (≥ 32 bayt tasodifiy). DB'da uy kaliti **saqlanmaydi**.
- Hub ro'yxatdan o'tganda `hub_token` va `signing_key_hex` bir marta ko'rsatiladi va Hub `.env` iga yoziladi. DB'da faqat `SHA-256(hub_token)`.
- Hub tekshiruvi (tartib bilan): imzo (`hmac.compare_digest`) → `expires_at` (soat farqi uchun ±5 s ruxsat) → `command_id` avval ko'rilmaganmi (SQLite) → payload'dagi rol/ruxsat → qurilmaning lokal xavfsizlik qoidasi.
- Muddat: standart 10 s, `risk: high` 5 s. Har buyruqda `command_id` (UUID) va `idempotency_key`.
- **Test vektorlari** `packages/contracts/test-vectors/signing.json` (Faza 3) — Backend va Hub ikkalasi ham shu vektorlar bilan tekshiriladi.
- Ack/holat Hub'dan Backend'ga `hub_token` bilan HTTPS orqali (TLS + token). Hub → Backend xabarlarini imzolash — Faza 14 da qayta ko'rib chiqiladi.

## Ko'rib chiqilgan muqobillar
- **Faqat broker ACL / TLS** — parol sizsa himoya yo'q.
- **Ed25519 (asimmetrik)** — Hub faqat ochiq kalitni saqlaydi, Hub o'g'irlansa ham imzo soxtalashtirib bo'lmaydi. Kuchliroq, lekin kalit rotatsiyasi va ESP/Python kutubxonalari murakkabroq. Hub uyda jismoniy himoyalangan, shuning uchun HMAC yetarli deb topildi. Agar Hub'lar soni ko'paysa yoki tahdid modeli o'zgarsa — yangi ADR.
- **Har bir uyga tasodifiy kalit DB'da** — DB sizsa buyruq soxtalashtiriladi.

## Oqibatlar
### Ijobiy
- DB yoki broker sizishi buyruq soxtalashtirishga olib kelmaydi.
- Replay — `command_id` + `expires_at` bilan bloklanadi.
### Salbiy / xavflar
- `SIGNING_MASTER_KEY` sizsa — barcha uylar kaliti hosil qilinadi. Rotatsiya: master kalit almashtiriladi → har bir Hub'ga yangi `signing_key_hex` (runbook, Faza 14). Kalitga versiya (`kid`) qo'shish Faza 3 da ko'rib chiqiladi.
- Hub soati noto'g'ri bo'lsa barcha buyruqlar rad etiladi → NTP majburiy, Hub salomatligida soat farqi ko'rsatiladi.
- Lokal rejimda (`hub.local`, internetsiz) buyruqlar cloud imzosisiz — Hub lokal sessiya bilan avtorizatsiya qiladi; audit keyin sinxronlanadi. Lokal autentifikatsiya dizayni — alohida ADR (ochiq).
