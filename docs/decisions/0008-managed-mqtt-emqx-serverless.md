# 0008 — Managed MQTT: EMQX Cloud Serverless

- Holat: qabul qilingan (real hisobda sinalishi kerak — pastga qarang)
- Sana: 2026-10-07
- ADR 0005 ni davom ettiradi: polling **zaxira bo'lib qoladi**.

## Kontekst
Faza 5: ilova holatni sekundiga ko'rishi va buyruq Hub'ga tezroq yetishi kerak. Shared hostingda doimiy MQTT ulanish yo'q (ADR 0001), shuning uchun Backend broker'ga faqat HTTP orqali e'lon qila oladi.

Tekshirilgan ma'lumotlar (2026-10, ommaviy manbalar):

| | EMQX Cloud Serverless (free) | HiveMQ Cloud Serverless (free) |
|---|---|---|
| Bepul limit | 1 000 000 sessiya-daqiqa/oy (≈ 23 ta doimiy ulangan mijoz), 1 GB trafik/oy, 1 000 000 rule action | 100 ulanish, 10 GB trafik/oy |
| Maks. sessiya | 1000 | 100 |
| HTTP publish API | **bor** (`POST {api}/publish`, basic auth AppID/AppSecret) | yo'q (REST API faqat Starter'da) |
| Foydalanuvchi va ACL API | bor (Authentication / ACL Management API) | yo'q |
| JWT auth | **yo'q** (parol va X.509) | yo'q (Starter'dan) |
| TLS / WSS | bor | bor |

## Qaror
- Broker: **EMQX Cloud Serverless** (bepul tarif). Uning HTTP publish API'si orqali shared hostingdagi Backend doimiy ulanishsiz e'lon qila oladi.
- Hisoblar:
  - `hub-{home_id}` — konsolda **qo'lda** yaratiladi; parol Hub `.env` iga yoziladi. ACL: `sh/v1/{home_id}/#` o'qish va yozish.
  - `app-{user_id}` — Backend API orqali yaratadi; parol har `GET /realtime/credentials` da almashtiriladi. ACL: faqat a'zo bo'lgan uylarning `sh/v1/{home_id}/#` topiklariga **subscribe**, publish taqiqlangan.
  - Backend broker'ga MQTT bilan ulanmaydi, faqat HTTP publish ishlatadi (AppID/AppSecret `.env` da).
  - Konsolda standart qoida "mos kelmasa → **rad et**" bo'lishi shart (qo'lda sozlanadi, runbook'da).
- JWT yo'qligi sababli "qisqa muddatli hisob" amalda parol rotatsiyasi bilan beriladi: har so'rovda yangi parol, client_id = username (yangi ulanish eskisini uzadi). Bu haqiqiy TTL emas — pastda xavf sifatida yozilgan.
- Buyruq yo'li: Backend buyruqni DB'ga yozadi → (best-effort) `sh/v1/{home}/cmd` ga imzolangan konvertni e'lon qiladi → Hub uni broker'dan yoki polling'dan oladi. Bir xil `command_id` ikki yo'ldan kelsa, Hub uni **bir marta** bajaradi va takroriy nusxa uchun ack yubormaydi.
- Broker'ga faqat holat (`state`, `availability`, `hub/health`) va buyruqlar boradi. Telemetriya broker'ga yuborilmaydi (1 GB limitni tejash uchun) — u HTTP orqali boradi.
- Broker xatosi hech qachon buyruqni to'xtatmaydi: publish muvaffaqiyatsiz bo'lsa buyruq tarixiga voqea yoziladi va polling ishlaydi.

## Ko'rib chiqilgan muqobillar
- **HiveMQ Cloud Serverless** — HTTP publish va foydalanuvchi API'si bepul tarifda yo'q, ya'ni shared hosting'dan e'lon qilib bo'lmaydi.
- **O'z broker'imiz (VPS)** — qo'shimcha xarajat va administratsiya (ADR 0001).
- **Faqat polling** — ishlaydi, lekin holat ~3 s kechikadi va hosting'ga so'rovlar ko'payadi.

## Oqibatlar
### Ijobiy
- Hosting o'zgarmasdan real-time imkoniyati paydo bo'ladi; broker yo'qolsa tizim polling'da ishlashda davom etadi.
### Salbiy / xavflar
- JWT yo'q → `app-*` paroli haqiqiy muddatga ega emas. Paroli sizgan hisob faqat **o'qiy** oladi (ACL), buyruq yubora olmaydi (ADR 0004). Hisobni o'chirish yoki rotatsiya qilish — cron (Faza 7).
- Bepul limit: har bir ochiq PWA oynasi sessiya-daqiqa sarflaydi. PWA fon holatiga o'tganda ulanishni uzishi kerak (Faza 6).
- Uchinchi tomon xizmatiga bog'liqlik (threat model T15): broker holat ma'lumotlarini ko'radi, lekin video va telemetriya u yerga bormaydi.

## Tasdiqlanishi kerak (real hisob ochilganda)
- Serverless API'ning foydalanuvchi va ACL endpoint yo'llari. Kod EMQX 5 REST API ko'rinishini ishlatadi: `/authentication/password_based:built_in_database/users`, `/authorization/sources/built_in_database/rules/users`. Hujjat sayti tekshiruv paytida tarmoqdan bloklangan edi, shuning uchun bu yo'llar **tasdiqlanmagan**.
- Standart "deny" sozlamasi va WSS URL formati.
- Holat kechikishi < 2 s ekanini real broker bilan o'lchash.
