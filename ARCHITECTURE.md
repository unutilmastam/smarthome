# SmartHome Control Center — Arxitektura (v2, real hayotga moslangan)

> Bu hujjat repozitoriyning asosiy "manba haqiqati". AI agent (Claude Code va boshqalar) har bir ishni shu hujjatga qarab bajaradi. Hujjat bilan kod zid kelsa — avval hujjat yangilanadi, keyin kod.

---

## 0. Asl master promptdagi kamchiliklar va tuzatishlar

| # | Asl promptdagi muammo | Nima uchun xato | Tuzatish |
|---|---|---|---|
| 1 | Cloud = VPS + Docker + PostgreSQL + MQTT broker + Redis + WebSocket | hostmaster.uz **cPanel shared hosting**: Docker yo'q, doimiy ishlaydigan broker yo'q, WebSocket ishonchsiz, jarayonlar Passenger orqali uxlab qoladi | Cloud = **yengil API** (FastAPI → Passenger, PostgreSQL). Real-time = **managed MQTT broker** (EMQX Cloud Serverless yoki HiveMQ Cloud). Og'ir ish = **uydagi Hub** |
| 2 | Avtomatlashtirish cloud'da | Internet uzilsa uy "ko'r" bo'lib qoladi | Barcha avtomatika va xavfsizlik qoidalari **Hub'da lokal** ishlaydi. Cloud faqat tahrirlaydi va sinxronlaydi |
| 3 | Mobil (React Native) + Web (React) — 2 ta alohida ilova | Kompyutersiz ishlayotgan bitta dasturchi uchun 2x ish | **Bitta React PWA** (telefon, iPad, kompyuter). iOS 16.4+ da PWA Web Push ishlaydi. Expo — keyinroq, ixtiyoriy |
| 4 | Internet yo'q bo'lsa ilova qanday ishlaydi — aytilmagan | Uyda internet o'chsa, telefon cloud'ga ulana olmaydi | Hub o'zida ham shu PWA'ni beradi (`http://hub.local`). Ilova avval lokal Hub'ni tekshiradi, bo'lmasa cloud'ga ulanadi |
| 5 | Kamera masofadan ko'rish — "VPN yoki tunnel" deb noaniq | Shared hostingda video relay qilib bo'lmaydi | **Tailscale** (bepul) orqali Frigate'ga to'g'ridan-to'g'ri. Cloud video'ni umuman ko'rmaydi |
| 6 | Hub uchun elektr ta'minoti aytilmagan | Svet o'chsa — kamera yozuvi, gateway, router to'xtaydi | **UPS** majburiy: Hub + router + PoE switch + kameralar |
| 7 | Holat aniqlash: ACS712 hiylasi (eski loyihada) | Shovqinli, kalibrlash kerak, 220V yonida xavfli | **PZEM-004T v3** (arzon) yoki **Eastron SDM120/SDM630 Modbus** (DIN-rail, professional) |
| 8 | IR orqali konditsioner — holat "tasdiqlangan" deb ko'rsatilishi mumkin | IR'da qaytar aloqa yo'q | IR qurilmalar `assumed` holat bilan ko'rsatiladi; tasdiq — xona harorati yoki tok sensori orqali |
| 9 | Buyruqni kim yuborishi mumkin — faqat ACL | Broker paroli o'g'irlansa — darvozani ochish mumkin | Buyruqlar faqat Backend orqali, **HMAC imzo + muddat** bilan. Hub imzosiz buyruqni rad etadi |
| 10 | OTA (proshivka yangilash) yo'q | Har bir ESP32'ni qo'lda yangilash imkonsiz | ESPHome OTA (parol bilan) yoki imzolangan HTTPS OTA |
| 11 | Deploy jarayoni kompyuterni nazarda tutadi | Egasi faqat telefon/iPad'da ishlaydi | GitHub → **GitHub Actions** → cPanel (SSH/FTP deploy). Barcha build cloud'da |
| 12 | Bildirishnoma faqat push | iOS push ba'zan kechikadi | Push + **Telegram bot** (zaxira kanal, eng ishonchli) |
| 13 | Vaqt sinxronizatsiyasi yo'q | Jadval va loglar noto'g'ri bo'ladi | Hub va ESP32 — NTP. Ichkarida UTC, ko'rsatishda `Asia/Tashkent` |

---

## 1. Umumiy sxema

```
                    ┌──────────────────────────────────────────┐
                    │  CLOUD — hostmaster.uz (cPanel shared)   │
                    │                                          │
 Telefon/iPad ─────▶│  PWA (static, public_html)               │
 (internetdan)      │  API: FastAPI (Passenger + a2wsgi)       │
                    │  PostgreSQL                              │
                    │  cron: retention, hisobotlar             │
                    └──────────┬───────────────────────────────┘
                               │ HTTPS (faqat Hub → Cloud yo'nalishida)
                               │
        ┌──────────────────────┴───────────────┐
        │  MANAGED MQTT BROKER (EMQX Serverless)│◀── PWA: faqat o'qish (WSS, ACL)
        │  TLS 8883 / WSS 8084                  │
        └──────────────────────┬───────────────┘
                               │ TLS (Hub chiqadi, kiruvchi port yo'q)
 ══════════════════════════════╪══════════ UY (LAN) ═══════════════════
                               │
                    ┌──────────┴───────────────────────────────┐
                    │  HOME HUB (mini PC / Raspberry Pi 5)     │
                    │  + UPS + HDD                             │
                    │                                          │
                    │  gateway-agent (Python) — "miya"         │
                    │  Mosquitto (lokal broker)                │
                    │  automation-engine (lokal)               │
                    │  Frigate NVR + go2rtc (video)            │
                    │  SQLite (bufer + lokal tarix)            │
                    │  Lokal PWA: http://hub.local             │
                    │  Tailscale (masofaviy kamera/SSH)        │
                    └──────────┬───────────────────────────────┘
                               │ Lokal MQTT / RTSP / Modbus
        ┌────────────┬─────────┼──────────┬────────────┬───────────┐
     ESP32 rele   ESP32 IR   PZEM/SDM   Darvoza     Sensorlar   IP kameralar
     (chiroq,     (konditsio- (energiya) kontrolleri (PIR, radar, (RTSP/ONVIF,
     rozetka,      ner)                  + datchik   eshik, suv)  alohida VLAN)
     nasos)
```

### Asosiy qoidalar
1. **Uy cloud'siz ham to'liq ishlaydi.** Internet faqat masofadan boshqarish va tarix uchun.
2. **Xavfsizlik qurilmaning o'zida.** Nasos maksimal vaqti, darvoza fotoelementi — ESP32 proshivkasida va apparatda. Dastur faqat qo'shimcha himoya.
3. **Video uydan chiqmaydi.** Cloud'da faqat kamera nomi, ID, holati, ruxsatlar.
4. **Hech qanday kiruvchi port ochilmaydi.** Hub hamma joyga o'zi ulanadi (outbound).
5. **Hech qanday qiymat o'ylab topilmaydi.** Ma'lumot yo'q → `unknown` / `offline` / `not_supported`.

---

## 2. Zonalar va mas'uliyat

### A. Cloud (hostmaster.uz cPanel)
**Qiladi:** autentifikatsiya, foydalanuvchi/rollar, uy/xona/qurilma reyestri, buyruqni qabul qilish va imzolash, holat va telemetriya tarixini saqlash (agregatlangan), avtomatika qoidalarini tahrirlash, audit log, bildirishnomalar (Web Push, Telegram), Hub va kamera serveri salomatligini kuzatish.

**Qilmaydi:** video saqlash, doimiy fon jarayonlari, WebSocket server, avtomatikani bajarish.

**Texnik cheklovlar va yechimlar:**
- FastAPI ASGI → Passenger WSGI: `a2wsgi` adapter (`passenger_wsgi.py`).
- Fon vazifalar yo'q → cPanel **cron** `python -m app.jobs.<name>` (har 5 daqiqa / soatlik / kunlik).
- DB: **PostgreSQL** (hostingda mavjud: "PostgreSQL Databases"). Versiya juda eski bo'lsa — MySQL zaxira; SQLAlchemy tufayli kod o'zgarmaydi.
- Real-time: broker orqali (pastga qarang). Broker bo'lmasa — PWA har 3 soniyada `GET /state` (fallback).
- **Portativlik:** kod `Docker Compose` profili bilan ham ishlaydi. Kelajakda hostmaster VDS'ga o'tish = konfiguratsiya o'zgarishi, qayta yozish emas.

### B. Managed MQTT broker
- Tavsiya: **EMQX Cloud Serverless** (bepul limit uy uchun yetarli). Zaxira: HiveMQ Cloud Free.
- Hisoblar:
  - `hub-{home_id}` — o'z uyining hamma topiklariga yozish/o'qish.
  - `backend` — faqat `.../commands` ga yozish, `.../ack` va `.../state` o'qish.
  - `app-{user_id}` — **faqat o'qish**: `state`, `availability`, `events`. Buyruq yuborish TAQIQLANGAN.
- Bepul limit/API tafsilotlari Faza 0 da tekshiriladi va `docs/decisions/` ga yoziladi.
- **Broker'siz zaxira yo'l (birinchi quriladi):** Hub har 1–2 s da `GET /api/v1/hub/commands` bilan navbatdagi buyruqlarni oladi (outbox polling). Bu shared hostingda 100% ishlaydi. MQTT broker Faza 5 da tezlik uchun qo'shiladi; polling zaxira sifatida qoladi.

### C. Home Hub (uyda)
**Apparat (tavsiya):** Intel N100 mini PC (8–16 GB RAM, 256 GB SSD) + 2–4 TB surveillance HDD + UPS (≥600 VA). Kamera ≤4 ta bo'lsa — Raspberry Pi 5 + Coral/Hailo ham bo'ladi.
**OS:** Ubuntu Server 24.04 LTS, Docker Compose.

| Servis | Vazifa |
|---|---|
| `gateway-agent` | Cloud ↔ lokal ko'prik, buyruq imzosini tekshirish, holatni yig'ish, Hub salomatligi |
| `automation-engine` | Trigger/shart/harakat, jadvallar, cooldown, loop himoyasi — **lokal** |
| `mosquitto` | Lokal broker (ESP32'lar faqat shu bilan gaplashadi) |
| `frigate` + `go2rtc` | Kamera yozish, aniqlash, WebRTC live-view |
| `local-api` | LAN ichida PWA uchun API + statik PWA |
| `tailscale` | Masofadan kamera va SSH (port ochmasdan) |
| SQLite | Offline bufer (internet yo'qda telemetriya to'planadi, keyin yuboriladi) |

### D. Qurilmalar (ESP32 va boshqalar)
- Standart qurilmalar: **ESPHome** (rele, sensor, IR, PZEM) — tez, ishonchli, OTA bor.
- Maxsus mantiq (darvoza, nasos, kupyura va h.k.): **Arduino/PlatformIO** proshivka, bir xil MQTT shartnoma bilan.
- Har bir qurilmada: lokal watchdog, maksimal ishlash vaqti, aloqa uzilsa xavfsiz holat (`fail_safe_state`).

---

## 3. Texnologiyalar (yakuniy)

| Qatlam | Tanlov |
|---|---|
| Backend (cloud) | Python 3.10+ (3.10 bilan mos; hosting versiyasi tasdiqlanguncha), FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, a2wsgi |
| DB (cloud) | PostgreSQL (cPanel) |
| Gateway / automation (hub) | Python 3.10+, asyncio, aiomqtt, Pydantic, SQLite |
| Frontend | React 18 + TypeScript + Vite, TanStack Query, Zustand, i18next (uz → ru, en), PWA (vite-plugin-pwa) |
| Real-time (frontend) | mqtt.js (WSS), fallback — polling |
| Video | Frigate + go2rtc (WebRTC), Tailscale |
| Proshivka | ESPHome YAML + PlatformIO (C++) |
| Bildirishnoma | Web Push (VAPID) + Telegram Bot API |
| Test | pytest, httpx, Vitest + Testing Library, Playwright (asosiy oqimlar) |
| CI/CD | GitHub Actions: test → build PWA → deploy (cPanel SSH/FTP) |

---

## 4. Qurilma modeli (eng muhim qism)

### 4.1 Qurilma = imkoniyatlar (capabilities) to'plami
Qurilma turi qattiq kodlanmaydi. Har bir qurilma imkoniyatlar ro'yxatiga ega:

```
switch        : on/off
dimmer        : brightness 0–100
color         : rgb / color_temp
power_meter   : voltage, current, power, energy, power_factor, frequency
climate       : current_temp, target_temp, mode, fan, power
cover         : position, open/close/stop  (darvoza, jalyuzi)
lock          : locked/unlocked
contact       : open/closed  (eshik/deraza datchigi)
motion        : detected/clear  (PIR, radar)
environment   : temperature, humidity, soil_moisture
leak          : wet/dry
valve         : open/closed + max_runtime  (sug'orish)
camera        : stream_available, recording, disk_usage
contactor     : commanded_closed, aux_contact_closed  (liniya o'chirish; tasdiq — yordamchi kontakt)
```

Yangi qurilma qo'shish = adapter + mavjud capability'lardan foydalanish. UI capability'ga qarab avtomatik boshqaruv elementini chizadi.

**To'liq spetsifikatsiya:** `packages/contracts/capabilities.json` — atributlar, birliklar, harakatlar (parametrlar JSON Schema), ruxsat, xavf darajasi, `confirm_attribute`. Yagona manba (Faza 1 da `docs/spec/` dan ko'chirildi).

Qurilma ikki identifikatorga ega: `id` (UUID, API uchun) va `key` (`garden_lights` kabi, uy ichida yagona — MQTT va Hub uchun). Har bir qurilma `unsupported` atributlar ro'yxatiga ega: hisoblagich o'lchamaydigan narsa `not_supported` bo'lib ko'rinadi.

### 4.2 Har bir qiymat "ishonch" bilan keladi
```json
{
  "value": 231.4,
  "unit": "V",
  "source": "reported",        // reported | assumed | computed
  "quality": "good",           // good | stale | unknown | not_supported
  "ts": "2026-10-07T12:50:03Z"
}
```
- `reported` — qurilma o'zi aytdi (tasdiqlangan).
- `assumed` — buyruq yuborildi, lekin qaytar aloqa yo'q (IR konditsioner).
- `stale` — `ts` muddati o'tgan (masalan, 3× hisobot intervali).
UI har doim farqlaydi: tasdiqlangan holat ✓, kutilayotgan ⏳, taxminiy ≈, noma'lum ?.

### 4.3 Buyruq hayot sikli
```
requested → signed → sent → acked → confirmed
                  ↘ expired   ↘ rejected   ↘ failed / timeout
```
- `acked` = qurilma buyruqni oldi. `confirmed` = holat haqiqatan o'zgardi (datchik/tok bo'yicha).
- Darvoza uchun `confirmed` faqat oxirgi holat datchigi (geркон) bilan.
- Har bir buyruq: `command_id` (UUID), `expires_at` (standart 10 s, darvoza 5 s), `idempotency_key`.

### 4.4 Buyruq imzosi (Backend → Hub)
```
payload = {command_id, device_id, device_key, capability, action, params,
           issued_at, expires_at, issued_by: {user_id, role}}     -- ADR 0007
home_signing_key = HMAC-SHA256(SIGNING_MASTER_KEY, "home-signing:" + home_id)
signature        = HMAC-SHA256(home_signing_key, canonical_json(payload))
canonical_json   = UTF-8, kalitlar tartiblangan, separators (',', ':'), bo'sh joysiz
```
- `home_signing_key` DB'da saqlanmaydi — `.env` dagi master kalitdan hosil qilinadi. DB o'g'irlansa ham buyruq soxtalashtirib bo'lmaydi.
- Hub yaratilganda `hub_token` va `signing_key_hex` **bir marta** ko'rsatiladi (Hub `.env` iga yoziladi). Hub token DB'da faqat SHA-256 sifatida turadi.
Hub tekshiradi: imzo to'g'ri, muddati o'tmagan, `command_id` avval bajarilmagan, foydalanuvchi ruxsati (payload'da rol), qurilmaning lokal xavfsizlik qoidasi ruxsat beradimi.

---

## 5. MQTT topiklari

**Lokal (Hub ↔ ESP32):**
```
home/{device_id}/state          (retained)  — joriy holat
home/{device_id}/telemetry                  — o'lchovlar
home/{device_id}/availability   (retained, LWT) — online/offline
home/{device_id}/cmd                        — buyruq (faqat gateway yozadi)
home/{device_id}/ack                        — buyruq natijasi
```

**Cloud broker (Hub ↔ Backend ↔ PWA):**
```
sh/v1/{home_id}/dev/{device_id}/state         (retained)
sh/v1/{home_id}/dev/{device_id}/availability  (retained)
sh/v1/{home_id}/cmd                           — imzolangan buyruqlar
sh/v1/{home_id}/ack
sh/v1/{home_id}/events                        — signal, harakat, xatolar
sh/v1/{home_id}/hub/health                    (retained)
```
- Xabarlar JSON, har birida `"schema": 1`.
- Telemetriya cloud broker'ga yuborilmaydi (trafik tejash) — Hub uni har 60 s da HTTPS bilan Backend'ga paket qilib jo'natadi.
- Lokal Mosquitto: har bir ESP32'ga alohida login + ACL. Anonim ulanish o'chirilgan.

---

## 6. Ma'lumot oqimlari

**Buyruq (masofadan):** PWA → `POST /api/v1/commands` → Backend (auth, ruxsat, audit, imzo) → broker `cmd` → Hub (tekshiruv) → lokal `cmd` → ESP32 → `ack` → Hub → broker `ack` + `POST /hub/acks` → PWA yangilanadi.

**Buyruq (uyda, internet yo'q):** PWA → `hub.local` local-api → Hub (lokal sessiya bilan) → ESP32. Keyin audit Backend'ga sinxronlanadi.

**Telemetriya:** ESP32 → lokal broker → Hub (SQLite, 1-daqiqalik agregatsiya) → har 60 s `POST /api/v1/hub/telemetry:batch` → PostgreSQL.

**Holat:** ESP32 → Hub → broker `state` (retained) → PWA (real-time).

---

## 7. Ma'lumotlar bazasi (cloud, PostgreSQL)

```
users, roles, user_home_roles, sessions, password_resets
homes (timezone, lat/lon — quyosh chiqishi/botishi uchun)
floors, rooms (type: indoor/outdoor)
hubs (home_id, secret_hash, last_seen, version)
devices (room_id, adapter, protocol, model, fail_safe_state, enabled)
device_capabilities (device_id, capability, config_json)
device_state (device_id, capability, value_json, source, quality, ts)   -- joriy
commands (id, device_id, action, params, status, requested_by, created_at, expires_at)
command_results (command_id, status, detail, ts)
telemetry_1m   (device_id, metric, ts, avg, min, max)   -- 30 kun
telemetry_1h   (device_id, metric, ts, avg, min, max)   -- 2 yil
energy_daily   (device_id, date, kwh, cost)              -- doimiy
automations (json definition, version, enabled)
automation_runs (automation_id, trigger, result, error, ts)
schedules
notifications (severity, source, title, body, acked_by, acked_at)
push_subscriptions, telegram_links
cameras (hub_id, name, frigate_name, room_id)   -- VIDEO YO'Q
audit_log (actor, action, target, ip, ts, details)
```
- Hammasi UTC. Indekslar: `(device_id, ts)`.
- Retention cron: `telemetry_1m` > 30 kun → o'chiriladi (avval `1h` ga agregatsiya).
- Xom (raw) telemetriya faqat Hub'da (SQLite, 7 kun).

---

## 8. API (`/api/v1`)

```
auth:          POST /auth/login, /auth/refresh, /auth/logout, /auth/password-reset
users/roles:   GET/POST/PATCH /users, /homes/{id}/members
homes/rooms:   /homes, /homes/{id}/floors, /rooms
devices:       /devices (filter: room, type, status), /devices/{id}, /devices/{id}/history
commands:      POST /commands, GET /commands/{id}, POST /groups/{id}/commands
automations:   /automations, /automations/{id}/runs, POST /automations/validate
energy:        /energy/summary?period=, /energy/circuits/{id}
notifications: /notifications, POST /notifications/{id}/ack, /push/subscribe
cameras:       /cameras (metadata), GET /cameras/{id}/access  -> Tailscale/lokal URL
health:        /health, /homes/{id}/health
audit:         /audit
hub (Hub uchun, hub token bilan):
               POST /hub/heartbeat   (versiya, salomatlik)
               GET  /hub/commands    (navbatdagi imzolangan buyruqlar; bir marta beriladi → status 'sent')
               POST /hub/acks        (buyruq natijalari)
               POST /hub/report      (holatlar + availability, device_key bo'yicha)
               POST /hub/telemetry:batch, /hub/events
               GET  /hub/config      (qurilmalar, avtomatikalar — sinxron)
```
- Javob formati: `{ "data": ..., "error": null, "meta": {...} }`.
- Xato kodlari: `AUTH_REQUIRED, INVALID_CREDENTIALS, FORBIDDEN, NOT_FOUND, CONFLICT, DEVICE_OFFLINE, CAPABILITY_NOT_SUPPORTED, COMMAND_EXPIRED, RATE_LIMITED, VALIDATION_ERROR, HUB_UNREACHABLE, PIN_REQUIRED, PIN_INVALID, DEVICE_DISABLED`.
- A'zo bo'lmagan uyning resurslari → `404 NOT_FOUND` (403 emas, ID taxmin qilinmasin). A'zo, lekin ruxsat yo'q → `403 FORBIDDEN`.
- OpenAPI `/api/v1/docs` (productionda faqat admin).

---

## 9. Rollar va ruxsatlar

| Ruxsat | Owner | Admin | Oila | Mehmon | Ko'ruvchi |
|---|---|---|---|---|---|
| Ko'rish | ✓ | ✓ | ✓ | tanlangan | ✓ |
| Chiroq/konditsioner | ✓ | ✓ | ✓ | tanlangan | – |
| Darvoza/qulf | ✓ | ✓ | ✓ | vaqt bilan | – |
| Kamera live | ✓ | ✓ | sozlanadi | – | – |
| Kamera arxiv | ✓ | ✓ | – | – | – |
| Elektr liniyani o'chirish | ✓ | ✓ (PIN) | – | – | – |
| Konfiguratsiya | ✓ | ✓ | – | – | – |
| Foydalanuvchilar | ✓ | – | – | – | – |

Yuqori xavfli harakatlar (`risk: high` — darvoza, qulf, kontaktor) — buyruqda `confirm_pin` majburiy (PIN Argon2id bilan saqlanadi). WebAuthn — keyinroq.

**Mehmon:** qurilma/vaqt bo'yicha ruxsatlar (grants) alohida faza. U tayyor bo'lmaguncha mehmon faqat ko'radi — "tayyor" deb ko'rsatilmaydi.

Ruxsat nomlari: `view, control_basic, control_access, control_power, camera_live, camera_archive, configure, manage_users, view_audit`. Har bir capability qaysi ruxsatni talab qilishi `packages/contracts/capabilities.json` da.

---

## 10. Bo'limlar bo'yicha real apparat talablari

| Bo'lim | Apparat | Holatni tasdiqlash |
|---|---|---|
| Chiroq | ESP32 + rele / Sonoff (ESPHome), dimmer uchun MOSFET/triac modul | Rele holati + ixtiyoriy tok |
| Elektr panel | SDM120 (1 faza) / SDM630 (3 faza) Modbus RTU → RS485 → ESP32 yoki Hub USB; arzon variant PZEM-004T v3 | Faqat hisoblagich ko'rsatgani. **Avtomat (breaker) holatini dastur bilmaydi** — faqat yordamchi kontakt bo'lsa |
| Liniya o'chirish | Kontaktor (DIN) + yordamchi kontakt (NO/NC) holat uchun | Yordamchi kontakt |
| Darvoza | Mavjud darvoza blokining "start/open/close" kirishi + rele; ochiq/yopiq gerkon datchiklari | Gerkon. **Fotoelement apparatda qoladi** |
| Konditsioner | ESP32 + IR LED (ESPHome climate_ir) yoki ishlab chiqaruvchi API | `assumed` + xona harorati/tok |
| Xavfsizlik | PIR, LD2410 radar, gerkonlar, sirena | Datchik o'zi |
| Sug'orish | 24V AC klapanlar + rele, tuproq namligi (sig'imli), oqim datchigi | Oqim datchigi; ESP32'da `max_runtime` majburiy |
| Suv oqishi | Leak datchiklar + elektromagnit klapan | Datchik |
| Kamera | ONVIF/RTSP IP kameralar (PoE), alohida VLAN, internetga chiqish yopiq | Frigate holati |
| Tarmoq | Router (OpenWrt/MikroTik bo'lsa API), ping monitoring | Ping/API |

**Elektr ishlari faqat malakali elektrik tomonidan va amaldagi normalarga muvofiq bajariladi.**

---

## 11. Avtomatika (Hub'da bajariladi)

```yaml
id: garden_night_motion
enabled: true
trigger:
  - type: state
    device: garden_radar
    capability: motion
    to: detected
conditions:
  - type: sun
    after: sunset
  - type: security_mode
    is: armed
actions:
  - type: command
    device: garden_lights
    action: turn_on
    auto_off_after: 300        # soniya
  - type: notify
    severity: warning
    text: "Bog'da harakat aniqlandi"
cooldown: 120
max_runs_per_hour: 20
```
- Validatsiya: mavjud qurilma va capability, sikl (A → B → A) aniqlanadi va rad etiladi.
- Har bir ishga tushish `automation_runs` ga yoziladi.
- Qo'lda boshqaruv (manual override) avtomatikani belgilangan vaqtga to'xtatadi.
- Vizual muharrir UI'da shu YAML/JSON'ni yaratadi.

---

## 12. Offline va nosozlik stsenariylari

| Hodisa | Xatti-harakat |
|---|---|
| Internet uzildi | Hub, avtomatika, kamera yozuvi ishlashda davom etadi. Telemetriya SQLite'da to'planadi. Uyda PWA `hub.local` orqali ishlaydi |
| Internet qaytdi | Hub buferni yuboradi, holatlarni qayta e'lon qiladi, muddati o'tgan buyruqlarni bajarmaydi |
| Svet o'chdi, qaytdi | Har bir rele `restore_mode` bo'yicha (standart: OFF; chiroqlar sozlanadi). Nasos — har doim OFF |
| ESP32 uzildi | LWT → `offline`, UI'da kulrang, bildirishnoma (5 daqiqadan keyin) |
| Lokal broker yiqildi | Docker `restart: always`, Hub salomatligi `degraded` |
| Cloud broker yo'q | Buyruqlar HTTPS polling orqali davom etadi (ADR 0005). Hub ham yetib bo'lmasa (`last_seen` eskirgan) — `503 HUB_UNREACHABLE`, buyruq yaratilmaydi, PWA aniq xabar ko'rsatadi |
| HDD to'ldi | Frigate eski yozuvni o'chiradi; 85% da ogohlantirish |
| Hub o'zi o'chdi | Cloud `hubs.last_seen` > 3 daq → kritik bildirishnoma (Telegram) |

---

## 13. Xavfsizlik

- HTTPS hamma joyda (cPanel AutoSSL). MQTT faqat TLS/WSS.
- Parollar: Argon2id. Access token 15 daq, refresh token 30 kun (rotatsiya, bekor qilish mumkin, `HttpOnly` cookie).
- Login: rate limit (IP + akkaunt), 5 xatodan keyin kechikish.
- Sirlar: `.env` (gitda yo'q), GitHub Actions Secrets. Repo'da faqat `.env.example`.
- Hub sirlari: `hub_token` (DB'da faqat SHA-256) va `signing_key_hex` (DB'da saqlanmaydi, master kalitdan hosil qilinadi — 4.4) faqat Hub `.env` ida.
- Kameralar alohida VLAN'da, internetga chiqishi bloklangan, RTSP portlari tashqariga ochilmagan.
- Router'da port forwarding **yo'q**. Masofaviy kirish faqat Tailscale.
- ESPHome: API shifrlash kaliti + OTA paroli har qurilmada alohida.
- Audit log: kim, nima, qachon, qaysi IP — o'chirib bo'lmaydi (faqat qo'shiladi).
- Zaxira: cPanel avtomatik backup + kunlik `pg_dump` cron; Hub konfiguratsiyasi — shifrlangan arxiv.

---

## 14. Repozitoriy tuzilmasi

```
smarthome/
├── ARCHITECTURE.md            ← shu hujjat
├── CLAUDE.md                  ← AI agent uchun qisqa qoidalar
├── .env.example
├── .github/workflows/
│   ├── test.yml
│   ├── deploy-cloud.yml       ← cPanel'ga deploy
│   └── build-hub.yml          ← Hub Docker image'lar (GHCR)
├── apps/
│   └── web/                   ← React PWA (cloud + hub.local)
├── services/
│   ├── backend/               ← FastAPI (cloud)
│   │   ├── app/
│   │   │   ├── api/v1/        ← routerlar
│   │   │   ├── core/          ← config, security, signing
│   │   │   ├── models/        ← SQLAlchemy
│   │   │   ├── schemas/       ← Pydantic
│   │   │   ├── services/      ← biznes mantiq
│   │   │   └── jobs/          ← cron vazifalar
│   │   ├── alembic/
│   │   ├── passenger_wsgi.py
│   │   └── tests/
│   └── hub/
│       ├── gateway/           ← cloud ↔ lokal ko'prik
│       ├── automation/        ← qoidalar dvigateli
│       ├── adapters/          ← esphome, modbus, ir, frigate, network
│       ├── local_api/
│       ├── simulator/         ← virtual qurilmalar (test uchun)
│       ├── tests/
│       └── docker-compose.yml ← mosquitto, frigate, tailscale, gateway...
├── packages/
│   └── contracts/             ← JSON Schema: capability, state, command, events
│                                (backend, hub, web — hammasi shundan foydalanadi)
├── devices/
│   ├── esphome/               ← YAML: light-relay, pzem, ir-climate, sensors
│   └── firmware/              ← PlatformIO: gate, irrigation (maxsus)
├── infra/
│   ├── cpanel/                ← deploy skriptlar, .htaccess, cron ro'yxati
│   └── hub/                   ← Ubuntu o'rnatish skripti, UPS (NUT), backup
└── docs/
    ├── decisions/             ← ADR: har bir muhim qaror
    ├── hardware/              ← ulanish sxemalari, qurilma ro'yxati
    ├── runbooks/              ← "Hub o'chsa nima qilish" va h.k.
    └── threat-model.md
```

`packages/contracts` — eng muhim papka: bitta joyda yozilgan sxema, uch tomon ham undan foydalanadi, nomuvofiqlik bo'lmaydi.

---

## 15. Kompyutersiz ishlash jarayoni

1. Kod — GitHub'da (Claude Code / GitHub Codespaces telefon yoki iPad brauzerida).
2. Har bir push → GitHub Actions: testlar + build.
3. `main` ga merge → `deploy-cloud.yml`: PWA build `public_html` ga, backend SSH orqali (cPanel "SSH Access" → kalit), `alembic upgrade head`, Passenger restart (`tmp/restart.txt`). Zaxira yo'l: cPanel **Git Version Control** + `.cpanel.yml`. Qo'lda buyruqlar — cPanel **Terminal** (iPad brauzerida ishlaydi).
4. Hub: `build-hub.yml` Docker image'larni GHCR'ga yuklaydi; Hub'da Watchtower yoki `docker compose pull` (Tailscale SSH orqali, iPad'dan Termius bilan).
5. ESPHome: Hub'dagi ESPHome Dashboard (brauzer orqali) — kompyutersiz OTA.
6. Hub'ga birinchi marta Ubuntu o'rnatish — USB flesh kerak (Android'da EtchDroid bilan yozish mumkin) yoki OS oldindan o'rnatilgan mini PC sotib olish.

---

## 16. Bosqichlar

Batafsil vazifalar, testlar va tugash mezonlari: **`docs/PHASES.md`**. Qisqacha:

| Faza | Natija |
|---|---|
| 0 | Hujjatlar, ADR, threat model, apparat savollari |
| 1 | Monorepo, contracts, CI |
| 2 | Backend: auth, rollar, uy/xona/qurilma, hub ro'yxati, audit |
| 3 | Buyruqlar: imzo, hayot sikli, Hub API (polling) |
| 4 | Home Hub + simulyator — to'liq zanjir `[SIM]` |
| 5 | Real-time: managed MQTT (polling zaxira bo'lib qoladi) |
| 6 | PWA: telefon, iPad, veb |
| 7 | hostmaster.uz cPanel'ga deploy |
| 8 | Birinchi real qurilma (ESP32 rele) |
| 9 | Elektr monitoring |
| 10 | Kameralar (Frigate, lokal) |
| 11 | Darvoza, konditsioner, xavfsizlik, sug'orish |
| 12 | Avtomatika (Hub'da) |
| 13 | Bildirishnomalar (Push + Telegram) |
| 14 | Mustahkamlash: xavfsizlik, backup/restore |
| 15 | Uyni to'liq ishga tushirish |

Har faza oxirida `docs/PROGRESS.md` ga hisobot: o'zgarishlar, fayllar, **haqiqiy** test natijalari (`[SIM]`/`[REAL]`), qolgan xavflar, keyingi faza.

---

## 17. Qabul mezonlari

- [ ] Uy internetsiz to'liq boshqariladi (`hub.local`).
- [ ] Internet orqali boshqaruv imzolangan buyruqlar bilan ishlaydi.
- [ ] Har bir qiymat `reported / assumed / stale / unknown / not_supported` bilan ko'rsatiladi.
- [ ] Buyruq holati `confirmed` faqat haqiqiy qaytar aloqa bilan.
- [ ] Nasos/klapan internet uzilsa ham `max_runtime` da o'chadi (sinaldi).
- [ ] Video cloud'da yo'q (DB va hosting fayllari tekshirildi).
- [ ] Kamera yozuvi internet o'chiq paytda davom etdi (sinaldi).
- [ ] Hech qanday port tashqariga ochilmagan (tashqi port skan bilan tekshirildi).
- [ ] Backup'dan to'liq tiklash sinaldi.
- [ ] Rollar: mehmon darvozani faqat ruxsat etilgan vaqtda ocha oladi (test).
- [ ] Mock bilan ishlaydigan funksiya "tayyor" deb belgilanmaydi.

---

## 18. Tasdiqlanishi kerak (Faza 0 da javob olinadi)

1. ✅ hostmaster.uz cPanel'da bor: Setup Python App, Setup Node.js App, SSH Access, Terminal, PostgreSQL, Git Version Control, Cron Jobs. Qoldi: Python App'dagi eng yuqori Python versiyasi (≥3.10 kerak) va PostgreSQL versiyasi. Subdomen tavsiyasi: `home.<domen>.uz`.
2. Hub uchun byudjet: N100 mini PC yoki Raspberry Pi 5?
3. Kameralar: soni, modeli (ONVIF/RTSP qo'llaydimi), PoE switch bormi?
4. Elektr: 1 faza yoki 3 faza? Nechta liniyani kuzatish va qaysilarini o'chirish kerak?
5. Darvoza blokining modeli (qaysi kirishlar bor: open/close/step)?
6. Konditsionerlar modeli (IR yoki Wi-Fi moduli bor)?
7. Router modeli (OpenWrt/MikroTik — VLAN qilish mumkinmi)?
8. Elektr montajini kim bajaradi (malakali elektrik)?

Javob bo'lmaguncha: xavfsiz standart qiymatlar + simulyator bilan ishlanadi.

---

## 19. AI agent uchun qat'iy qoidalar (CLAUDE.md ga ham ko'chiriladi)

1. Ishni boshlashdan oldin shu hujjatni va `packages/contracts` ni o'qi.
2. Bir vaqtda bitta faza. Katta "hammasini birdan" kod yozma.
3. Qiymat o'ylab topma. Ma'lumot yo'q → `unknown`.
4. Video bilan bog'liq hech narsani cloud'ga yozma.
5. Sir/parolni kodga yozma — faqat `.env`.
6. Har bir yangi qurilma turi = adapter + contract + simulyator + test.
7. Xavfsizlik chegaralari (max_runtime, fail_safe) proshivkada bo'lishi shart; dasturdagi tekshiruv — qo'shimcha.
8. Simulyatsiyada o'tgan testni "real apparatda ishladi" deb yozma.
9. Mavjud ishni o'chirma; o'zgarishni ADR bilan asosla.
10. Har faza oxirida `docs/PHASES.md` dagi shablon bo'yicha hisobot ber.
