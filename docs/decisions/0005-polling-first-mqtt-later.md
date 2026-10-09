# 0005 — Avval HTTPS polling, MQTT broker keyin (polling zaxira bo'lib qoladi)

- Holat: qabul qilingan
- Sana: 2026-10-07

## Kontekst
- Shared hostingda doimiy jarayon va WebSocket server yo'q (ADR 0001).
- Managed MQTT broker (EMQX Cloud Serverless, HiveMQ Cloud) — tashqi xizmat: bepul limitlar, ACL, HTTP publish API hali tekshirilmagan.
- Birinchi navbatda **ishonchli** zanjir kerak, tezlik keyin.

## Qaror
1. **Faza 3–4:** Hub `GET /api/v1/hub/commands` ni har 1–2 s da so'raydi (outbox polling). Backend buyruqni atomik ravishda bir marta beradi (`queued → sent`). Xatoda — exponential backoff. PWA holatni `GET /state` bilan har ~3 s da yangilaydi.
2. **Faza 5:** managed MQTT broker qo'shiladi (tanlov alohida ADR'da, limitlar tekshirilgandan keyin). Backend buyruqni broker'ga HTTP publish API orqali ham e'lon qiladi; PWA faqat o'qish huquqi bilan WSS orqali holatni oladi.
3. **Polling o'chirilmaydi** — broker ishlamasa tizim avtomatik polling'da davom etadi. Hub bir xil `command_id` ni ikki yo'ldan olsa ham bir marta bajaradi.

## Ko'rib chiqilgan muqobillar
- **Darhol MQTT** — tashqi xizmatga birinchi kundan bog'lanish; xato manbai ko'p, test qiyin.
- **Long polling / SSE cPanel'da** — Passenger worker'larini band qiladi, timeout'lar noaniq.
- **O'z broker'imizni Hub'da ochish** — kiruvchi port kerak (taqiqlangan).

## Oqibatlar
### Ijobiy
- Shared hostingda 100% ishlaydigan yo'l birinchi bo'lib quriladi va doim zaxira bo'lib qoladi.
### Salbiy / xavflar
- Polling kechikishi: buyruq ~1–2 s, PWA holati ~3 s gacha.
- So'rov soni: 1 Hub × 1 so'rov/s ≈ 86 400 so'rov/kun — hosting "entry process"/CPU limitlariga to'g'ri kelishi **tekshirilishi kerak**. Zarur bo'lsa: bo'sh navbatda interval 5 s gacha oshiriladi (adaptive polling).
- Cloud broker yo'q va polling ham ishlamasa (cloud yoki internet yo'q) — masofaviy buyruq `503 HUB_UNREACHABLE` bilan rad etiladi, buyruq yaratilmaydi.
