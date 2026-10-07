# Bosqichma-bosqich reja (AI agent uchun)

> Bu fayl — ishning tartibi. `ARCHITECTURE.md` — **nima** qurilishi, bu fayl — **qaysi tartibda** va **qachon tugagan hisoblanadi**.
> Agent har safar faqat **bitta fazani** bajaradi, oxirida hisobot beradi va to'xtaydi.

## Har bir fazani boshlash

Claude Code'ga shunday yozing:

```
CLAUDE.md, ARCHITECTURE.md va docs/PHASES.md ni o'qi. Faza N ni bajar.
```

Agent fazani tugatgach `docs/PROGRESS.md` ga hisobot yozadi va keyingi fazani boshlamaydi.

## Umumiy qoidalar (har bir fazaga tegishli)

- Kod tili: **ingliz** (o'zgaruvchi, funksiya, commit). UI matnlari: **o'zbek** (i18n kalitlari orqali). Hujjat va hisobot: **o'zbek**.
- Python **3.10** bilan mos bo'lsin (hosting versiyasi tasdiqlanguncha). `match`, `ExceptionGroup`, 3.11+ sintaksis ishlatilmaydi.
- Har bir fazada testlar yoziladi va **haqiqatan ishga tushiriladi**. Natija hisobotga ko'chiriladi.
- Simulyatsiya testi va real apparat testi alohida belgilanadi: `[SIM]` / `[REAL]`.
- Sir, parol, token — faqat `.env`. Repo'da `.env.example`.
- Har bir muhim qaror — `docs/decisions/NNNN-nom.md` (ADR: kontekst → qaror → oqibat).
- Avvalgi fazalarda yozilgan kodni sababsiz o'chirmaslik.

## Faza hisoboti shabloni (`docs/PROGRESS.md` ga qo'shiladi)

```
## Faza N — <nomi> — <sana>
Holat: tugadi | qisman | to'xtadi (sabab)
Qilingan ishlar: ...
Yaratilgan/o'zgartirilgan fayllar: ...
Testlar: <buyruq> → <natija: X passed, Y failed> [SIM|REAL]
Hal qilinmagan xavflar: ...
Tasdiqlanmagan taxminlar: ...
Keyingi faza: N+1 — <nomi>
```

---

## Faza 0 — Tayyorgarlik (hujjatlar)

**Maqsad:** qarorlar yozilgan, savollar ro'yxati aniq.

Vazifalar:
- [x] `docs/decisions/` ga ADR'lar: 0001 shared hosting + Hub arxitekturasi, 0002 PostgreSQL, 0003 bitta PWA (React Native emas), 0004 buyruq imzosi (HMAC, hosil qilingan kalit), 0005 polling birinchi, MQTT keyin, 0006 video uydan chiqmaydi.
- [x] `docs/threat-model.md`: aktivlar (darvoza, qulf, kamera, elektr), tahdidlar (token o'g'irlash, broker paroli, DB sizishi, replay, LAN'dagi begona qurilma), har biriga himoya.
- [x] `docs/hardware/inventory.md`: ARCHITECTURE.md 18-bo'limdagi savollar jadvali (javob / "noma'lum").
- [x] `docs/PROGRESS.md` yaratiladi.

Tugash mezoni: hujjatlar bor, kod yo'q.

---

## Faza 1 — Poydevor (monorepo, contracts, CI)

**Maqsad:** bo'sh, lekin to'g'ri tuzilgan va CI'dan o'tadigan repo.

Vazifalar:
- [x] ARCHITECTURE.md 14-bo'limdagi papka tuzilmasi.
- [x] `docs/spec/capabilities.json` → `packages/contracts/capabilities.json`. Qo'shimcha JSON Schema'lar `packages/contracts/schemas/`: `value`, `command-envelope`, `ack`, `state-report` (ARCHITECTURE 4.2–4.4).
- [x] `packages/contracts/tests/`: barcha schema'lar o'zi to'g'ri JSON Schema ekanini tekshiruvchi test; har bir capability'da `permission`, `risk`, `attributes`, `actions` borligi.
- [x] `services/backend/` skeleti: `pyproject.toml` yoki `requirements.txt` (versiyalar qotirilgan), `app/main.py` faqat `GET /api/v1/health`, `passenger_wsgi.py` (a2wsgi), `.env.example`.
- [x] Konfiguratsiya: pydantic-settings. `ENV=production` da dev-sirlar yoki SQLite bilan ishga tushish **xato beradi**.
- [x] `.github/workflows/test.yml`: Python 3.10 va 3.12 matritsa, PostgreSQL service, `pytest`.
- [x] `.gitignore`, `.editorconfig`.

Testlar: contracts testi, health testi, "production + dev sir → xato" testi.
Tugash mezoni: CI yashil.

---

## Faza 2 — Backend asosi (auth, uy, xona, qurilma reyestri)

**Maqsad:** foydalanuvchi kiradi, uy/xona/qurilma yaratadi; hamma narsa DB'da va audit'da.

Vazifalar:
- [x] SQLAlchemy 2 modellari + Alembic birinchi migratsiya: `users, auth_sessions, homes, home_members, floors, rooms, hubs, devices, device_capabilities, device_state, cameras, audit_log`.
- [x] Vaqt: DB'da UTC; ORM'da `UTCDateTime` turi (SQLite va Postgres'da bir xil, naive datetime taqiqlangan).
- [x] Auth: Argon2id parol, access JWT 15 daq, refresh token 30 kun (DB'da faqat SHA-256), **rotatsiya**; eski refresh qayta ishlatilsa — userning barcha sessiyalari bekor. `logout`, `logout-all`, `me`, `password` (boshqa sessiyalar bekor), `pin`.
- [x] Login himoyasi: IP bo'yicha rate limit + DB'da `failed_logins/locked_until` (5 xato → 5 daq blok). Mavjud bo'lmagan email uchun ham bir xil vaqt (dummy hash).
- [x] Ommaviy ro'yxatdan o'tish **yo'q**. Birinchi owner: `python -m app.cli create-owner --email ...` (cPanel Terminal'da ishlaydi).
- [x] Rollar va ruxsatlar: `app/core/permissions.py` (ARCHITECTURE 9-bo'lim). Faqat owner a'zo qo'sha oladi; ikkinchi owner yaratib bo'lmaydi; owner'ni o'chirib bo'lmaydi.
- [x] A'zo bo'lmagan uy/qurilmaga so'rov → **404** (403 emas — ID'ni taxmin qilib bo'lmasin).
- [x] CRUD: homes, members, floors, rooms, devices (capabilities bilan), hubs (yaratishda `hub_token` + `signing_key_hex` bir marta qaytadi), `revoke`.
- [x] Qurilma yaratishda capability va `unsupported` atributlar contracts bo'yicha tekshiriladi.
- [x] Qurilma javobi: har bir capability'ning **har bir atributi** chiqadi; ma'lumot yo'q → `quality: unknown`, `not_supported`, eskirgan → `stale`; Hub offline → availability `unknown` (ARCHITECTURE 4.2).
- [x] Javob formati `{data, error, meta}`, xato kodlari ARCHITECTURE 8-bo'limdagidek. Ro'yxatlarda `limit/offset`.
- [x] Audit: login, a'zo, qurilma, hub o'zgarishlari. API'da audit'ni o'zgartirish/o'chirish yo'q.

Testlar (SQLite + PostgreSQL'da): login/refresh/rotatsiya/reuse, lock, rollar matritsasi, 404 izolyatsiyasi, qurilma atributlari `unknown/not_supported`, `alembic upgrade head` toza Postgres'da.
Tugash mezoni: barcha testlar o'tadi; OpenAPI `/api/v1/docs` ochiladi.

---

## Faza 3 — Buyruqlar (imzo, hayot sikli, Hub API)

**Maqsad:** buyruq yuboriladi, imzolanadi, Hub uni oladi va natija qaytadi — hali haqiqiy Hub yo'q, test mijozi bilan.

Vazifalar:
- [x] `commands`, `command_events` jadvallari + migratsiya.
- [x] `POST /api/v1/commands`: qurilma a'zolikda bormi → capability bormi → action/params contracts bo'yicha → rol ruxsati → `risk: high` bo'lsa `confirm_pin` → qurilma yoqilganmi → Hub online'mi (aks holda **503 HUB_UNREACHABLE**, buyruq yaratilmaydi) → qurilma offline emasmi.
- [x] Idempotentlik: `(user, idempotency_key)` yagona; takror so'rov asl buyruqni qaytaradi (200).
- [x] Imzo: ARCHITECTURE 4.4 (hosil qilingan kalit, canonical JSON). `app/core/signing.py` + **test vektorlari** `packages/contracts/test-vectors/signing.json` (Hub ham shu vektorlar bilan tekshiriladi).
- [x] Muddat: oddiy 10 s, `high` 5 s (sozlanadi). Olinmagan → `expired`; olingan-javobsiz (+30 s) → `timeout`.
- [x] Hub API (hub token bilan): `POST /hub/heartbeat`, `GET /hub/commands` (atomik: har bir buyruq **bir marta** beriladi, `queued → sent`), `POST /hub/acks`, `POST /hub/report` (holat + availability, `device_key` bo'yicha, contracts bo'yicha tekshiriladi), `GET /hub/config`.
- [x] Holat faqat oldinga siljiydi (ack kech kelsa `confirmed` ni buzmaydi).
- [x] `GET /commands/{id}` voqealar tarixi bilan; `GET /devices/{id}/commands`.
- [x] Buyruq rate limit (foydalanuvchiga 60/daq).

Testlar: to'liq sikl (queued→sent→acked→confirmed), ikki marta claim qilinmasligi, muddati o'tishi, PIN'siz darvoza → rad, guest/viewer → rad, noto'g'ri params → 422, offline Hub → 503, imzo test vektorlari, boshqa uyning Hub'i ack qila olmasligi.
Tugash mezoni: testlar o'tadi `[SIM]`.

---

## Faza 4 — Home Hub + simulyator

**Maqsad:** haqiqiy Hub dasturi virtual qurilmalarni boshqaradi; backend bilan to'liq zanjir ishlaydi.

Vazifalar:
- [x] `services/hub/gateway`: asyncio; backend'ga heartbeat (30 s), `GET /hub/commands` polling (1–2 s, xatoda exponential backoff), imzo + muddat + takror `command_id` tekshiruvi (SQLite'da bajarilganlar ro'yxati), lokal MQTT'ga uzatish, ack qaytarish.
- [x] Imzosiz / muddati o'tgan / takror buyruq → `rejected` + sabab. **Hech qachon bajarilmaydi.**
- [x] `confirm_attribute` bor capability'larda (`cover`, `lock`, `contactor`, `valve`) `confirmed` faqat qurilma holati haqiqatan o'zgarganda; belgilangan vaqtda o'zgarmasa → `failed: no_feedback`.
- [x] `services/hub/simulator`: lokal MQTT'da virtual qurilmalar — chiroq (switch+dimmer), PZEM (power_meter, realistik shovqin), harorat sensori, harakat sensori, darvoza (ochilish 15 s, gerkon), IR konditsioner (`assumed`), sug'orish klapani (**`max_runtime` simulyator ichida majburiy**), suv oqishi sensori. Nosozlik rejimlari: qurilma uziladi, javob bermaydi, noto'g'ri qiymat.
- [x] Lokal MQTT topiklari ARCHITECTURE 5-bo'lim; LWT → availability.
- [x] Offline bufer: backend yo'q paytda holatlar SQLite'da yig'iladi, ulanish qaytsa yuboriladi; eskirgan buyruqlar bajarilmaydi.
- [x] `services/hub/docker-compose.yml`: mosquitto (ACL, anonim o'chiq), gateway, simulator. `docker compose up` bilan ishga tushadi.
- [x] Integratsion test: backend + hub + simulyator bir jarayonda (yoki compose) — telefon o'rniga test mijozi chiroqni yoqadi, holat `confirmed`.

Testlar: imzo vektorlari (backend bilan bir xil), replay rad etilishi, internet uzilishi stsenariysi, klapan internet yo'qda ham o'chishi.
Tugash mezoni: to'liq zanjir `[SIM]` da ishlaydi.

---

## Faza 5 — Real-time (managed MQTT)

**Maqsad:** ilova holatni sekundiga ko'radi; buyruqlar tezroq yetadi.

Vazifalar:
- [x] ADR: EMQX Serverless yoki HiveMQ (bepul limitlar, ACL va API tekshirilgan holda).
- [x] Cloud topiklar ARCHITECTURE 5-bo'lim. Hisoblar: `hub-{home}`, `backend`, `app-{user}` (**faqat o'qish**).
- [x] Backend buyruq yaratganda broker'ga ham e'lon qiladi (HTTP publish API — shared hostingda doimiy ulanish shart emas). Polling **zaxira bo'lib qoladi**.
- [x] Hub broker'dan buyruq oladi; bir xil `command_id` ikki yo'ldan kelsa bir marta bajariladi.
- [~] `GET /api/v1/realtime/credentials` (EMQX user/ACL API yo'llari tasdiqlanmagan) — foydalanuvchiga qisqa muddatli, faqat o'qish uchun broker hisobi (yoki broker qo'llasa JWT).
- [x] Broker ishlamasa: hammasi polling bilan davom etadi (test).

Tugash mezoni: broker o'chirilganda ham tizim ishlaydi; yoqilganda holat < 2 s da yetadi.

---

## Faza 6 — PWA (veb + telefon + iPad)

**Maqsad:** haqiqiy backend bilan ishlaydigan ilova. Soxta ekran yo'q.

Vazifalar:
- [x] React + TypeScript + Vite, TanStack Query, i18next (`uz` to'liq, `ru`/`en` kalitlar tayyor), dark/light, dizayn tokenlari.
- [x] Ekranlar: login, dashboard (sozlanadigan kartalar), xonalar/zonalar, qurilmalar markazi (qidiruv, filtr), qurilma sahifasi, buyruq tarixi, Hub holati, sozlamalar (PIN, parol, sessiyalar), a'zolar (owner).
- [x] Boshqaruv elementlari capability'dan avtomatik: switch, dimmer, climate, cover (PIN so'raydi), valve (davomiylik majburiy), sensorlar.
- [x] Holat belgilari: ✓ tasdiqlangan, ⏳ kutilmoqda, ≈ taxminiy, ⚠ eskirgan, ? noma'lum, "Qo'llab-quvvatlanmaydi", Hub offline banneri.
- [x] Buyruq tugmasi bosilganda: optimistik emas — `queued → sent → acked → confirmed` holatini ko'rsatadi.
- [x] Token: access xotirada, refresh xavfsiz saqlash (ADR'da yoziladi), avtomatik yangilash.
- [~] Lokal rejim: `hub.local` mavjud bo'lsa unga ulanadi (Hub local-api keyingi fazalarda to'ldiriladi; hozircha aniqlash va banner).
- [x] PWA: manifest, ikonkalar, offline sahifa, iOS'ga o'rnatish.
- [x] Testlar: Vitest + Testing Library (holat belgilari, PIN oqimi), Playwright: login → chiroq yoqish `[SIM]`.

Tugash mezoni: simulyator qurilmalari telefon va iPad'dan boshqariladi.

---

## Faza 7 — cPanel'ga deploy (hostmaster.uz)

**Maqsad:** tizim haqiqiy domenda ishlaydi.

Vazifalar:
- [x] `infra/cpanel/`: deploy skripti, `.htaccess` (PWA SPA marshrutlari, `/api` → Python app), cron ro'yxati.
- [x] `.github/workflows/deploy-cloud.yml` (yozildi; Secrets yo'qligi sababli ishga tushirilmagan): test → PWA build → SSH (GitHub Secrets) orqali yuklash → `pip install` (virtualenv) → `alembic upgrade head` → `tmp/restart.txt`.
- [x] Cron: `expire_due` (har daqiqa), retention (kunlik), `pg_dump` zaxira (kunlik).
- [x] `docs/runbooks/deploy.md`: iPad'dan qadamlar (cPanel → Setup Python App, PostgreSQL DB yaratish, SSL, birinchi owner).
- [ ] Hub (yoki simulyator) haqiqiy domen'ga ulanadi. — **egasi deploy qilgandan keyin**

Tugash mezoni: `https://<domen>/api/v1/health` → ok; telefondan simulyator boshqariladi.

---

## Faza 8 — Birinchi real qurilma (ESP32 rele + chiroq)

- [~] Hub apparati o'rnatiladi — yo'riqnoma `infra/hub/install.md` tayyor; apparat yo'q.
- [x] `devices/esphome/light-relay.yaml`: shifrlangan API kaliti, OTA paroli, MQTT (lokal), LWT, `restore_mode`, NTP.
- [x] ~~`services/hub/adapters/esphome`~~ → ADR 0010: ESPHome proshivkasi lokal shartnomani o'zi gapiradi (ack proshivkadan).
- [ ] Sinov (`docs/hardware/tests/light-relay.md`, `[REAL]` — apparat kerak): yoqish/o'chirish, Wi-Fi uzilishi, svet o'chib-yonishi, internet uzilishi (`hub.local`).

Tugash mezoni: `[REAL]` testlar hisobotda.

---

## Faza 9 — Elektr monitoring

- [x] Telemetriya jadvallari: `telemetry_1m` (30 kun), `telemetry_1h` (2 yil), `energy_daily`; Hub agregatsiya qiladi va paket yuboradi.
- [x] Adapterlar (ESPHome YAML, ADR 0010): PZEM-004T (ESPHome), SDM120/SDM630 (Modbus RTU).
- [x] Kontaktor: `commanded_closed` va `aux_contact_closed` alohida; tasdiq faqat yordamchi kontakt bilan. Avtomat (breaker) holati dasturda **ko'rsatilmaydi**, agar apparat bermasa.
- [x] Tarif sozlamasi, kunlik/oylik xarajat.
- [x] UI: elektr paneli (ARCHITECTURE asl talablar 5.5).

Tugash mezoni: o'lchov haqiqiy hisoblagich bilan solishtirilgan `[REAL]`.

---

## Faza 10 — Kameralar (lokal)

- [ ] Frigate + go2rtc Hub'da; HDD; retention; 85% disk ogohlantirishi.
- [ ] Kameralar alohida VLAN, internetga chiqish yopiq.
- [ ] Cloud: faqat metadata va `GET /cameras/{id}/access` (Tailscale/lokal URL, ruxsat tekshiruvi bilan).
- [ ] Test: internet o'chiq paytda yozuv davom etadi; cloud DB va hosting fayllarida video yo'qligi tekshiriladi.

---

## Faza 11 — Darvoza, konditsioner, xavfsizlik, sug'orish (bittadan)

Har bir tur uchun alohida qadam: contracts → ESPHome/PlatformIO proshivka → adapter → simulyator yangilanishi → UI → nosozlik testi → `[REAL]`.
- Darvoza: gerkon bilan tasdiq, fotoelement apparatda, "ochiq qoldi" ogohlantirishi.
- Konditsioner: IR, `assumed` holat, harorat/tok bilan tasdiq.
- Xavfsizlik: zonalar, armed/disarmed, kirish/chiqish kechikishi, voqealar tasmasi.
- Sug'orish: `max_runtime` proshivkada, oqim datchigi, favqulodda to'xtatish.

---

## Faza 12 — Avtomatika (Hub'da)

- [ ] Qoida formati ARCHITECTURE 11-bo'lim; JSON Schema `packages/contracts/schemas/automation.schema.json`.
- [ ] Backend: saqlash, validatsiya (mavjud qurilma/capability, sikl aniqlash), versiya; Hub `GET /hub/config` orqali oladi.
- [ ] Hub dvigateli: trigger/shart/harakat, quyosh vaqti (uy koordinatalari), cooldown, `max_runs_per_hour`, manual override, bajarilish tarixi.
- [ ] UI: vizual muharrir.
- [ ] Test: loop rad etilishi, internet yo'qda ishlashi.

---

## Faza 13 — Bildirishnomalar

- [ ] Web Push (VAPID) + Telegram bot (bog'lash kodi bilan).
- [ ] Hodisalar: ARCHITECTURE asl 5.13 ro'yxati; jiddiylik, tasdiqlash (ack).
- [ ] Hub o'chsa → cron 3 daq ichida aniqlaydi → Telegram.

---

## Faza 14 — Mustahkamlash

- [ ] Xavfsizlik tekshiruvi: `pip-audit`, `npm audit`, tashqi port skan, sirlar skan (gitleaks).
- [ ] Backup'dan tiklash **haqiqatan** bajariladi va hujjatlanadi.
- [ ] Runbook'lar: Hub o'chdi, broker yo'q, disk to'ldi, token o'g'irlandi (revoke), elektr uzildi.

## Faza 15 — Uyni ishga tushirish

- [ ] Qurilmalar bittadan ulanadi, har biri sinaladi va `docs/hardware/installed.md` ga yoziladi.
- [ ] ARCHITECTURE 17-bo'lim qabul mezonlari bittadan belgilanadi.
