# Progress

Har bir faza tugagach shu yerga hisobot qo'shiladi (shablon: `docs/PHASES.md`).
Belgilar: `[SIM]` — simulyatsiyada, `[REAL]` — haqiqiy apparatda sinalgan.

| Faza | Nomi | Holat |
|---|---|---|
| 0 | Tayyorgarlik (hujjatlar) | tugadi |
| 1 | Poydevor (monorepo, contracts, CI) | tugadi, CI yashil |
| 2 | Backend asosi (auth, uy, xona, qurilma reyestri) | tugadi, CI yashil |
| 3 | Buyruqlar (imzo, hayot sikli, Hub API) | tugadi `[SIM]` |
| 4 | Home Hub + simulyator | tugadi `[SIM]`, CI yashil (Docker image build sinalmagan) |
| 5 | Real-time (managed MQTT) | qisman: `[SIM]` tugadi, haqiqiy EMQX hisobida sinalmagan |
| 6 | PWA (veb + telefon + iPad) | tugadi `[SIM]` (haqiqiy telefon/iPad'da emas, emulyatsiyada) |
| 7 | cPanel'ga deploy | boshlanmagan |

---

## Faza 0 — Tayyorgarlik (hujjatlar) — 2026-10-07
Holat: tugadi

Qilingan ishlar:
- 6 ta ADR yozildi (0001–0006) va ADR indeksi/shabloni.
- Tahdid modeli: 12 aktiv, 6 turdagi hujumchi, 15 tahdid (har biriga himoya, qolgan xavf, qaysi fazada amalga oshiriladi), ishonch chegaralari, ochiq savollar.
- Apparat inventari: ARCHITECTURE 18-bo'limdagi 8 savol (kichik savollarga bo'lingan) + ko'rib chiqishda aniqlangan 8 qo'shimcha savol. Har biri uchun "javobgacha standart" va bloklanadigan faza.
- Hujjatlar o'zaro tekshirildi; aniq nomuvofiqliklar ARCHITECTURE.md da tuzatildi (pastga qarang).

Yaratilgan/o'zgartirilgan fayllar:
- `docs/decisions/README.md` (yangi)
- `docs/decisions/0001-shared-hosting-and-home-hub.md` (yangi)
- `docs/decisions/0002-postgresql.md` (yangi)
- `docs/decisions/0003-single-pwa.md` (yangi)
- `docs/decisions/0004-command-signing-hmac.md` (yangi)
- `docs/decisions/0005-polling-first-mqtt-later.md` (yangi)
- `docs/decisions/0006-video-stays-home.md` (yangi)
- `docs/threat-model.md` (yangi)
- `docs/hardware/inventory.md` (yangi)
- `docs/PROGRESS.md` (yangi)
- `ARCHITECTURE.md` (nomuvofiqliklar tuzatildi)
- `docs/PHASES.md` (Faza 0 vazifalari belgilandi)

ARCHITECTURE.md dagi tuzatishlar:
1. 3-bo'lim: "Python 3.11+" → "Python 3.10+ (3.10 bilan mos)" — CLAUDE.md va PHASES.md bilan zid edi.
2. 4.1-bo'lim: `contactor` capability ro'yxatga qo'shildi (`capabilities.json` da bor edi, ro'yxatda yo'q edi).
3. 8-bo'lim: xato kodlariga `HUB_UNREACHABLE` qo'shildi (PHASES.md Faza 3 da ishlatiladi).
4. 12-bo'lim: "Cloud broker yo'q" qatori ADR 0005 ga moslandi — broker yo'q bo'lsa polling davom etadi; ikkalasi ham ishlamasa `503 HUB_UNREACHABLE`.
5. 13-bo'lim: eskirgan `home_secret` atamasi `hub_token` + `signing_key_hex` (4.4-bo'lim) bilan almashtirildi.

Testlar: kod yo'q — testlar mavjud emas (Faza 0 tugash mezoni: "hujjatlar bor, kod yo'q"). Faqat `docs/spec/capabilities.json` JSON sifatida o'qilishi tekshirildi: `python3 -c "import json; json.load(open('docs/spec/capabilities.json'))"` → xatosiz.

Hal qilinmagan xavflar:
- Hosting cheklovlari (Python/PostgreSQL versiyasi, cron oralig'i, so'rovlar limiti) tasdiqlanmagan — 1 s polling hosting limitlariga sig'ishi noma'lum (ADR 0005).
- `http://hub.local` — secure context emas: lokal rejimda Service Worker/Push ishlamasligi mumkin (ADR 0003).
- Internetsiz lokal autentifikatsiya dizayni yo'q (ADR 0004, threat model).
- Router VLAN qo'llashi noma'lum — tarmoq tekis bo'lishi mumkin (T6).
- Hub disk shifrlash va avtomatik yuklanish ziddiyati (T9).

Tasdiqlanmagan taxminlar:
- `docs/hardware/inventory.md` dagi barcha "noma'lum" qatorlar (H-01b…H-16) — hammasi egasidan javob kutadi.
- Hosting PostgreSQL ≥ 12 va Python ≥ 3.10 deb hisoblanmoqda.
- Managed MQTT bepul limitlari uy uchun yetarli deb hisoblanmoqda (Faza 5 da tekshiriladi).

Keyingi faza: 1 — Poydevor (monorepo, contracts, CI). Faza 1 inventar javoblarisiz boshlanishi mumkin.

---

## Faza 1 — Poydevor (monorepo, contracts, CI) — 2026-10-07
Holat: tugadi

Qilingan ishlar:
- ARCHITECTURE 14-bo'limdagi papka tuzilmasi yaratildi. Hali kodi yo'q papkalarda faqat README bor; ularda qaysi fazada to'ldirilishi yozilgan (tayyor deb belgilanmagan).
- `docs/spec/capabilities.json` → `packages/contracts/capabilities.json` ga ko'chirildi (`git mv`). CLAUDE.md, ARCHITECTURE.md, README.md dagi havolalar yangilandi.
- JSON Schema'lar (draft 2020-12): `value`, `command-envelope`, `ack`, `state-report`, `capabilities` (registry formati).
  - `value`: `quality` = `unknown`/`not_supported` bo'lsa `value` faqat `null` bo'lishi mumkin. Shu tarzda o'ylab topilgan qiymat sxema darajasida taqiqlangan. Vaqt faqat UTC (`Z`).
  - `ack`: `rejected`/`failed` uchun `reason` majburiy, `acked`/`confirmed` da `reason` taqiqlangan.
- ADR 0007: buyruq payload'iga `device_key` va `capability` qo'shildi (harakat nomlari capability'lar orasida takrorlanadi: `open`).
- Backend skeleti: FastAPI, `GET /api/v1/health`, `{data, error, meta}` formati, OpenAPI `/api/v1/docs`, `passenger_wsgi.py` (a2wsgi), `.env.example`, qotirilgan `requirements.txt`/`requirements-dev.txt`.
- Konfiguratsiya (pydantic-settings): `ENV=production` da SQLite, bo'sh, qisqa (< 32 belgi), dev/placeholder sir yoki bir xil JWT/signing kaliti bo'lsa **ishga tushmaydi**.
- `.github/workflows/test.yml`: Python 3.10 va 3.12 matritsa, PostgreSQL 16 service, contracts va backend testlari. Action'lar commit SHA bilan qotirilgan (threat model T11).
- `.editorconfig`, `.gitignore` to'ldirildi.

Yaratilgan/o'zgartirilgan fayllar:
- `packages/contracts/`: `capabilities.json` (ko'chirildi), `schemas/*.schema.json` (5), `tests/` (conftest, test_schemas, test_capabilities), `requirements-test.txt`, `README.md`
- `services/backend/`: `app/main.py`, `app/core/config.py`, `app/core/responses.py`, `app/api/v1/{health,router}.py`, `passenger_wsgi.py`, `requirements*.txt`, `pyproject.toml`, `.env.example`, `tests/` (conftest, test_health, test_config)
- `.github/workflows/test.yml`, `.editorconfig`, `.gitignore`
- `docs/decisions/0007-command-envelope-fields.md`, `docs/decisions/README.md`, `ARCHITECTURE.md` (4.4, havolalar), `CLAUDE.md`, `README.md`, `docs/PHASES.md`
- Placeholder README: `apps/web`, `services/hub`, `devices/esphome`, `devices/firmware`, `infra/cpanel`, `infra/hub`, `docs/runbooks`

Testlar (lokal, cloud konteynerda):
- `python3.10 -m pytest packages/contracts -q` → 52 passed [SIM]
- `cd services/backend && python3.10 -m pytest -q` → 13 passed [SIM]
- Xuddi shu testlar Python 3.12 da → 52 passed, 13 passed [SIM]
- Testlar: barcha sxemalar to'g'ri JSON Schema; har capability'da `permission`, `risk`, `attributes`, `actions`; to'g'ri/noto'g'ri namunalar; health (TestClient va Passenger WSGI orqali); production + dev sir/SQLite → xato.
- GitHub Actions: `test` workflow, run #1 (commit `7039b22`) → **success** (Python 3.10 va 3.12).

Hal qilinmagan xavflar:
- PostgreSQL service CI'da ko'tariladi, lekin Faza 1 da DB'dan foydalanilmaydi (Faza 2 dan).
- cPanel'ga deploy paytida `packages/contracts` ilova yoniga (`contracts/`) nusxalanishi kerak — `CONTRACTS_DIR` bunga tayyor (Faza 7).
- Starlette testclient `httpx` uchun deprecation ogohlantirishi beradi (funksional ta'siri yo'q).

Tasdiqlanmagan taxminlar:
- Hosting Python versiyasi ≥ 3.10 (H-01b).

Keyingi faza: 2 — Backend asosi (auth, uy, xona, qurilma reyestri).

---

## Faza 2 — Backend asosi (auth, uy, xona, qurilma reyestri) — 2026-10-07
Holat: tugadi

Qilingan ishlar:
- SQLAlchemy 2 modellari: `users, auth_sessions, homes, home_members, floors, rooms, hubs, devices, device_capabilities, device_state, cameras, audit_log` va qo'shimcha `rate_limits` jadvali. Bu jadval login rate limit'i uchun: hisoblagich DB'da turadi, shuning uchun bir nechta Passenger jarayoni orasida umumiy bo'ladi.
- Alembic birinchi migratsiyasi `0001`. Toza PostgreSQL va SQLite'da `upgrade head` ishlaydi, model bilan farq yo'q (`compare_metadata` → bo'sh), `downgrade base` hammasini o'chiradi.
- DB cheklovlari: uyda faqat bitta owner va faqat bitta aktiv Hub (partial unique index), rol/holat/sifat qiymatlari uchun CHECK constraint'lar.
- `UTCDateTime` turi: naive datetime yozishga urinish xato beradi, o'qilganda doim UTC qaytadi (SQLite va Postgres'da bir xil).
- Auth:
  - Argon2id parol va PIN.
  - Access JWT 15 daqiqa; har so'rovda sessiya DB'da tekshiriladi, shuning uchun logout darhol kuchga kiradi.
  - Refresh token 30 kun, `<session_id>.<secret>` formatida; DB'da faqat SHA-256 saqlanadi. Har refresh'da rotatsiya bo'ladi; eski token qayta ishlatilsa foydalanuvchining **barcha** sessiyalari bekor qilinadi.
  - Endpoint'lar: `login`, `refresh`, `logout`, `logout-all`, `me`, `password` (boshqa sessiyalar bekor bo'ladi), `pin`.
- Login himoyasi:
  - IP bo'yicha limit: 5 daqiqada 20 urinish.
  - 5 ta xato urinishdan keyin akkaunt 5 daqiqaga bloklanadi.
  - Email mavjud bo'lmasa ham parol dummy hash bilan tekshiriladi va javob bir xil chiqadi.
- Ommaviy ro'yxatdan o'tish yo'q. Birinchi owner `python -m app.cli create-owner --email ... --name ... [--password-stdin]` bilan yaratiladi.
- Rollar: `app/core/permissions.py` (ARCHITECTURE 9).
  - Mehmon (guest) hozircha faqat ko'radi: alohida ruxsatlar (grants) qurilmagan.
  - Oila a'zosi (family) uchun `camera_live` standart holatda **yopiq**. ARCHITECTURE da bu "sozlanadi" deyilgan, lekin sozlash hali yo'q.
  - A'zolarni faqat owner qo'shadi. Ikkinchi owner yaratib bo'lmaydi, owner'ning rolini o'zgartirib yoki uni o'chirib bo'lmaydi.
- A'zo bo'lmagan uyning resurslariga so'rov → 404 (22 ta endpoint test bilan tekshirildi).
- CRUD: homes, members, floors, rooms, devices, hubs (+ `revoke`). Hub yaratilganda `hub_token` va `signing_key_hex` faqat bir marta qaytariladi; DB'da faqat token hash'i turadi, kalit esa saqlanmaydi (master kalitdan hosil qilinadi).
- Qurilma yaratishda capability'lar, `unsupported` atributlar va config kalitlari contracts bo'yicha tekshiriladi.
- Qurilma javobida har bir capability'ning har bir atributi chiqadi:
  - ma'lumot yo'q → `unknown`;
  - apparat o'lchamaydi → `not_supported`;
  - Hub offline yoki qurilma offline yoki `stale_factor × report_interval_s` dan eski → `stale`;
  - Hub yo'q yoki offline bo'lsa, qurilma holati (availability) `unknown`;
  - `assumed` manbasi saqlanadi.
- Javob formati `{data, error, meta}`, ro'yxatlarda `limit`/`offset`/`total`. Xato kodlari ARCHITECTURE 8 da kengaytirildi: `INVALID_CREDENTIALS`, `NOT_FOUND`, `CONFLICT`.
- Audit: login (muvaffaqiyatli, xato, blok), sessiyalar, parol, PIN, uy, a'zolar, qavat, xona, qurilma, Hub. API faqat o'qish uchun (`GET /homes/{id}/audit`); POST/PATCH/DELETE → 405. Audit'ga sir yozilmasligi test bilan tekshirildi.

Yaratilgan/o'zgartirilgan fayllar:
- `services/backend/app/`: `db/{types,base,session}.py`, `models/{user,auth,home,hub,device,audit}.py`, `core/{errors,security,contracts,permissions,signing}.py`, `services/{auth,audit,rate_limit,devices,device_view}.py`, `schemas/{common,auth,homes,devices}.py`, `api/deps.py`, `api/v1/{auth,homes,devices,hubs,router}.py`, `cli.py`, `main.py`, `core/config.py`
- `services/backend/alembic.ini`, `migrations/{env.py,script.py.mako,versions/0001_initial_schema.py}`
- `services/backend/tests/`: `conftest.py`, `test_auth.py`, `test_roles.py`, `test_isolation.py`, `test_devices.py`, `test_hubs.py`, `test_audit.py`, `test_cli_types.py`, `test_migrations.py`, `test_health.py`
- `services/backend/requirements.txt` (SQLAlchemy, Alembic, psycopg, argon2-cffi, PyJWT, tzdata), `.env.example`
- `ARCHITECTURE.md` (8-bo'lim: xato kodlari, 404 qoidasi)

Testlar (lokal):
- `cd services/backend && TEST_POSTGRES_URL=... python3.10 -m pytest -q` → 131 passed [SIM] (API testlari SQLite **va** PostgreSQL 16 da)
- Xuddi shu Python 3.12 da → 131 passed [SIM]
- `python -m pytest packages/contracts -q` → 52 passed [SIM]
- `alembic upgrade head` / `alembic check` / `downgrade base` — toza PostgreSQL 16 va SQLite'da xatosiz.
- OpenAPI: `/api/v1/docs` ochiladi (test).

Hal qilinmagan xavflar:
- Refresh token hozir JSON body'da qaytariladi. `HttpOnly` cookie bilan saqlash qarori Faza 6 ADR'ida qabul qilinadi.
- Akkaunt bloklanganda `429` qaytadi. Bu orqali mavjud email'ni aniqlash mumkin, lekin buning uchun 5 ta noto'g'ri urinish kerak va har bir urinish IP limitiga ham hisoblanadi.
- Agar hujumchi kimningdir sessiya ID'sini bilsa va soxta refresh token yuborsa, o'sha foydalanuvchining barcha sessiyalari bekor bo'ladi (logout qilinadi). Bu ataylab tanlangan konservativ xatti-harakat.
- `password_resets` (ARCHITECTURE 7) amalga oshirilmagan — Faza 2 vazifalari ro'yxatida yo'q. Hozircha parolni owner CLI orqali yoki foydalanuvchi o'zi `/auth/password` bilan o'zgartiradi.
- `rate_limits` jadvalini tozalash cron'i (`purge_old`) yozilgan, lekin cron'ga Faza 7 da ulanadi.
- OpenAPI hujjati production'da ham ochiq. ARCHITECTURE "productionda faqat admin" deydi — bu Faza 7 da yopiladi.

Tasdiqlanmagan taxminlar:
- Hub online oynasi 90 s (heartbeat 30 s × 3). Faza 4 da haqiqiy Hub bilan tekshiriladi.

CI: `test` workflow run #2 (commit `93311f8`) → **success**.

Keyingi faza: 3 — Buyruqlar (imzo, hayot sikli, Hub API).

---

## Faza 3 — Buyruqlar (imzo, hayot sikli, Hub API) — 2026-10-07
Holat: tugadi `[SIM]` (haqiqiy Hub yo'q; Hub o'rnida test mijozi ishlatildi)

Qilingan ishlar:
- `commands` va `command_events` jadvallari, migratsiya `0002`. `(requested_by, idempotency_key)` yagona.
- `POST /api/v1/commands`. Tekshiruvlar tartibi:
  1. rate limit (foydalanuvchiga daqiqasiga 60);
  2. idempotentlik;
  3. a'zolik (a'zo bo'lmasa 404);
  4. qurilmada shu capability bormi (`CAPABILITY_NOT_SUPPORTED`);
  5. action va params contracts bo'yicha (422);
  6. klapan uchun `duration_s` ≤ qurilmaning `max_runtime_s` i;
  7. rol ruxsati (403);
  8. `risk: high` bo'lsa PIN (`PIN_REQUIRED` / `PIN_INVALID`; 15 daqiqada 5 xato → keyin to'g'ri PIN ham rad etiladi);
  9. qurilma yoqilganmi (`DEVICE_DISABLED`);
  10. Hub online'mi (aks holda `503 HUB_UNREACHABLE`, buyruq yaratilmaydi);
  11. qurilma offline emasmi (`DEVICE_OFFLINE`).
- Idempotentlik: bir xil kalit va bir xil buyruq qayta yuborilsa → asl buyruq qaytadi (200, `meta.idempotent_replay`). Kalit bir xil, lekin buyruq boshqacha bo'lsa → 409.
- Imzo: `app/core/signing.py` (ADR 0004 + 0007). Imzolangan konvert buyruq bilan birga saqlanadi va Hub'ga aynan shu konvert beriladi.
- Test vektorlari: `packages/contracts/test-vectors/signing.json` (5 ta to'g'ri, 2 ta salbiy holat; float va UTF-8 matn bilan). Backend testi va contracts'dagi **mustaqil** test (backend kodisiz) ikkalasi ham shu vektorlarni tekshiradi.
- Muddat: oddiy buyruq 10 s, `high` risk 5 s (sozlanadi). Hub olmagan buyruq → `expired`. Hub olgan, lekin ack bermagan (`expires_at` + 30 s) → `timeout: no_ack`. `confirm_attribute` bor capability'da ack bor, tasdiq yo'q (60 + 30 s) → `timeout: no_feedback`.
- Hub API (`hub_token` bilan):
  - `POST /hub/heartbeat`;
  - `GET /hub/commands` — har bir buyruq shartli `UPDATE ... WHERE status='queued'` bilan atomik olinadi, ya'ni faqat bir marta beriladi; SQLite va Postgres'da bir xil ishlaydi;
  - `POST /hub/acks` — `ack.schema.json` bo'yicha tekshiriladi;
  - `POST /hub/report` — `state-report.schema.json` + atribut qiymatlari contracts bo'yicha; kelajak vaqtli, eski yoki `not_supported` atributga yozilgan qiymat rad etiladi;
  - `GET /hub/config`.
- Holat faqat oldinga siljiydi: kech kelgan ack `confirmed` ni buzmaydi. E'tiborsiz qolgan voqealar ham tarixda `applied: false` bilan saqlanadi.
- Boshqa uyning Hub'i bu uyning buyruqlarini ko'rmaydi va ack qila olmaydi (`not_found`). Bekor qilingan (revoked) Hub tokeni → 401.
- `GET /commands/{id}` (voqealar tarixi bilan), `GET /devices/{id}/commands` (sahifalab).
- Muddati o'tgan buyruqlarni tekshirish (`expire_due`) hozir so'rov paytida chaqiriladi (Hub polling, buyruqni o'qish). Faza 7 da cron'ga ham ulanadi.

Yaratilgan/o'zgartirilgan fayllar:
- `services/backend/app/models/command.py`, `migrations/versions/0002_commands.py`
- `services/backend/app/services/{commands,hub_reports}.py`, `app/api/hub_auth.py`, `app/api/v1/{commands,hub}.py`, `app/schemas/commands.py`, `app/core/signing.py`, `app/services/rate_limit.py`, `app/core/config.py`
- `packages/contracts/test-vectors/signing.json`, `packages/contracts/tests/test_signing_vectors.py`
- `services/backend/tests/{test_commands,test_hub_api}.py`
- `ARCHITECTURE.md` (xato kodlari: `PIN_REQUIRED`, `PIN_INVALID`, `DEVICE_DISABLED`)

Testlar (lokal):
- `python -m pytest packages/contracts -q` → 53 passed [SIM]
- `cd services/backend && TEST_POSTGRES_URL=... python3.10 -m pytest -q` → 204 passed [SIM] (SQLite + PostgreSQL 16)
- Xuddi shu Python 3.12 da → 204 passed [SIM]
- Faza talab qilgan testlar:
  - to'liq sikl `queued → sent → acked → confirmed`;
  - buyruq ikki marta olinmaydi;
  - muddati o'tadi va hech qachon yetkazilmaydi;
  - PIN'siz darvoza → 403;
  - guest va viewer → 403;
  - noto'g'ri params → 422;
  - offline Hub → 503, buyruq yaratilmaydi;
  - imzo vektorlari;
  - boshqa uyning Hub'i ack qila olmaydi.

Hal qilinmagan xavflar:
- Hub buyruqni imzosi bo'yicha tekshirishi Faza 4 da yoziladi. Hozir buni faqat testlar tekshiradi.
- Float qiymatli parametrlarning kanonik ko'rinishi Python `json` ga bog'liq. Hub ham Python bo'lgani uchun mos keladi. Boshqa tilda (masalan, ESP32) imzo tekshirilsa, float'lar ehtiyotkorlik talab qiladi; hozircha imzoni faqat Hub tekshiradi.
- 1 s polling'da `last_seen` faqat 5 s da bir marta yoziladi (DB yozuvlarini kamaytirish uchun).

CI: run #3 (commit `dd4b035`) → **success**.

Keyingi faza: 4 — Home Hub + simulyator.

---

## Faza 4 — Home Hub + simulyator — 2026-10-07
Holat: tugadi `[SIM]`. Istisno: `docker compose up` haqiqatan ishga tushirilmagan — muhitda Docker daemon yo'q. Faqat `docker compose config` tekshirildi (pastga qarang).

Qilingan ishlar:
- `services/hub/gateway` (asyncio). Sikllar:
  - heartbeat (30 s, sog'liq ma'lumoti bilan);
  - `GET /hub/commands` polling (1,5 s; xatoda exponential backoff, 60 s gacha);
  - config yangilash (oxirgi config SQLite'da saqlanadi, shuning uchun Hub internetsiz ham ishga tushadi);
  - lokal MQTT tinglovchi (uzilsa qayta ulanadi);
  - outbox flush;
  - har 60 s da to'liq holat hisoboti.
- Buyruq tekshiruvi (`gateway/verifier.py`), tartib ADR 0004 bo'yicha: konvert sxemasi → imzo → muddat (±5 s soat farqi) → replay (`command_id` SQLite'ga bajarishdan **oldin** yoziladi va qayta ishga tushirishdan keyin ham saqlanadi) → qurilma (`device_id` va `device_key` mos bo'lishi shart) → params → rol (`roles.json`) → lokal xavfsizlik qoidalari (o'chirilgan qurilma, LWT offline, `duration_s` > `max_runtime_s`). Tekshiruvdan o'tmagan buyruq **hech qachon** qurilmaga yetmaydi; backend'ga `rejected` + sabab yuboriladi.
- Tasdiq (`gateway/expectations.py`): `confirmed` faqat buyruq yuborilgandan **keyin** kelgan `reported` holat kutilgan qiymatga teng bo'lsa beriladi. `confirm_attribute` bor capability'larda (cover, lock, contactor, valve) holat vaqtida o'zgarmasa → `failed: no_feedback`. IR konditsioner (`assumed`) hech qachon `confirmed` bo'lmaydi va `acked` da qoladi. Qurilma ack bermasa → `failed: device_offline`.
- Offline bufer: ack'lar va holat hisobotlari SQLite outbox'ga yoziladi va internet qaytganda tartib bilan yuboriladi. Backend doimiy rad etgan (4xx) xabar navbatni to'sib qo'ymasligi uchun tashlab yuboriladi va log'ga yoziladi.
- Gateway qurilmadan kelgan qiymatlarni contracts bo'yicha tekshiradi; noto'g'ri qiymat backend'ga yuborilmaydi.
- `services/hub/simulator` (paho-mqtt). Har bir virtual qurilma o'z MQTT login'i va LWT'si bilan ulanadi:
  - chiroq (switch + dimmer);
  - PZEM (power_meter, Gauss shovqini; energiya faqat o'sadi);
  - harorat sensori;
  - harakat sensori;
  - darvoza (harakat vaqti sozlanadi, standart 15 s; `open`/`closed` faqat gerkon simulyatsiyasi bilan);
  - IR konditsioner (`assumed`; xona harorati `reported`);
  - sug'orish klapani (`max_runtime_s` **simulyator ichida majburiy**, ya'ni proshivka darajasida; Hub va internet yo'qolsa ham taymer klapanni yopadi);
  - suv oqishi sensori.
  
  Nosozlik rejimlari: `offline` (MQTT v5 "disconnect with will" → broker LWT yuboradi), `unresponsive`, `bad_values`, `stuck`.
- Lokal MQTT shartnomasi: `packages/contracts/schemas/local-mqtt.schema.json`, ARCHITECTURE 5 yangilandi (`{device_key}`, retained `state` qurilmaning to'liq holatini olib yuradi).
- `packages/contracts/roles.json`: rol matritsasi endi yagona manbada. Backend testi `permissions.py` shu fayl bilan bir xilligini tekshiradi; Hub uni bevosita o'qiydi.
- Mosquitto: `allow_anonymous false`, parol fayli, ACL. Gateway butun `home/#` ga kira oladi; qurilma (login = `device_key`) faqat o'z `state/telemetry/availability/ack` topiklariga yoza oladi va faqat o'z `cmd` topikini o'qiy oladi. `make-passwd.sh` parollarni `.env` dan oladi.
- `services/hub/docker-compose.yml` (mosquitto, gateway, `sim` profili bilan simulator) va `Dockerfile` (root bo'lmagan foydalanuvchi bilan).
- CI'ga `hub` job qo'shildi: Python 3.10/3.12, apt orqali mosquitto, testlar va `docker compose config`.

Testlar paytida topilgan va tuzatilgan haqiqiy xatolar:
1. Simulyatorda chiroq `switch` va `dimmer` holatini bitta retained topikka alohida xabar qilib yozgan; oxirgisi birinchisini o'chirib yuborgan. Tuzatildi: retained `state` doim qurilmaning to'liq holati. Bu qoida shartnoma tavsifiga va ARCHITECTURE 5 ga yozildi.
2. Contracts'da o'lchovlar uchun fizik chegaralar yo'q edi: -9999 V "to'g'ri" deb o'tib ketgan. Qo'shildi: kuchlanish 0–500 V, tok 0–1000 A, quvvat ±1 MW, energiya ≥ 0, chastota 40–70 Hz, harorat −60…100 °C, namlik 0–100 %, oqim ≥ 0. Shu chegaralarni tekshiruvchi test ham qo'shildi.
3. Integratsion testda darvoza 1 s da ochilib bo'lgani uchun test aynan `acked` holatini ba'zan ushlay olmagan. Test qayta yozildi: endi voqealar vaqti bo'yicha `confirmed` ack'dan kamida bir harakat vaqti keyin kelganini tekshiradi. Shundan keyin 10/10 va to'liq to'plam 6/6 marta o'tdi.

Yaratilgan/o'zgartirilgan fayllar:
- `services/hub/gateway/{config,contracts,signing,timeutil,store,backend,verifier,expectations,core,__main__}.py`
- `services/hub/simulator/{devices,__main__}.py`, `simulator/devices.example.json`
- `services/hub/mosquitto/{mosquitto.conf,acl,make-passwd.sh}`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `requirements*.txt`, `pyproject.toml`, `README.md`, `.gitignore`
- `services/hub/tests/{conftest,test_units,test_broker_acl,test_integration}.py`
- `packages/contracts/{roles.json,schemas/local-mqtt.schema.json,capabilities.json}`, contracts testlari
- `services/backend/tests/test_roles.py`, `ARCHITECTURE.md` (5-bo'lim), `.github/workflows/test.yml`

Testlar (lokal, haqiqiy Mosquitto 2.0.18 bilan):
- `cd services/hub && python3.10 -m pytest -q` → 25 passed [SIM]; Python 3.12 → 25 passed [SIM]
  - unit: imzo vektorlari (backend bilan bir xil), har bir rad etish sababi, Hub qayta ishga tushgandan keyin ham replay rad etilishi, kutilmalar, outbox tartibi;
  - broker: anonim va noto'g'ri parol rad etiladi; qurilma boshqa qurilma `cmd`/`state` topikiga yoza olmaydi va faqat o'z `cmd` ini oladi;
  - to'liq zanjir (backend + gateway + broker + simulyator bitta jarayonda):
    - chiroq `queued → sent → acked → confirmed`, holat backend'da `reported/good`;
    - darvoza faqat gerkon bilan tasdiqlanadi, tiqilib qolsa → `no_feedback`;
    - IR → `acked` + `assumed`;
    - javob bermaydigan qurilma → `device_offline`;
    - LWT → backend'da `offline`, keyingi buyruq 409;
    - replay va soxta imzoli konvert → qurilmaga yetmaydi;
    - **internet uzilganda klapan o'zi yopiladi**, holat buferda yig'iladi va ulanish qaytganda backend'ga yetadi;
    - muddati o'tgan buyruq internet qaytgandan keyin ham bajarilmaydi;
    - hisoblagich telemetriyasi `not_supported` bilan, noto'g'ri qiymatlar backend'ga yetmaydi.
- Integratsion to'plam ketma-ket 6 marta → har safar 9/9.
- `cd services/backend && python -m pytest -q` (SQLite + PostgreSQL) → 205 passed [SIM]
- `python -m pytest packages/contracts -q` → 57 passed
- `docker compose --profile sim config -q` → OK. **Image build va `docker compose up` sinalmagan** (Docker daemon yo'q).

Hal qilinmagan xavflar:
- ESP32 ↔ Mosquitto ulanishi TLS'siz (LAN). Threat model T6 dagi qolgan xavf.
- Simulyator va ESP32'lar uchun parollar `make-passwd.sh` orqali yaratiladi. Real qurilmalar uchun har birida alohida parol majburiy (`DEVICE_PASSWORD_<KEY>`); `SIM_DEVICE_PASSWORD` faqat simulyator uchun.
- Gateway buyruqni bajarish vaqtida config'ni keshdan oladi. Qurilma backend'da o'chirilgan bo'lsa-yu, Hub config'ni hali yangilamagan bo'lsa (≤ 60 s), backend baribir buyruq yaratmaydi, shuning uchun xavf past.
- Hub'ning `local-api` va `hub.local` PWA'si hali yo'q (Faza 6 va keyingi fazalar).

Tasdiqlanmagan taxminlar:
- Hub apparati (N100 yoki Pi 5) noma'lum (H-02). Kod `python:3.12-slim` ustida ishlaydi; u amd64 va arm64 uchun mavjud, lekin arm64'da sinalmagan.

CI: run #4 (commit `cb26ba8`) → **success**: 4 job — backend 3.10/3.12, hub 3.10/3.12; GitHub runner'ida apt orqali o'rnatilgan haqiqiy Mosquitto bilan.

Keyingi faza: 5 — Real-time (managed MQTT).

---

## Faza 5 — Real-time (managed MQTT) — 2026-10-07
Holat: **qisman**. Kod va `[SIM]` testlar tugadi. Haqiqiy EMQX Cloud Serverless hisobi yo'q (uni egasi ochishi kerak), shuning uchun haqiqiy broker bilan hech narsa sinalmagan.

Qilingan ishlar:
- ADR 0008 — EMQX Cloud Serverless tanlandi. Tekshirilgan ma'lumotlar:
  - bepul tarif: oyiga 1M sessiya-daqiqa (≈ 23 ta doimiy ulangan mijoz) va 1 GB trafik;
  - HTTP publish API bor;
  - foydalanuvchi va ACL API bor;
  - **JWT yo'q**.
  
  HiveMQ'ning bepul tarifida HTTP publish ham, foydalanuvchi API'si ham yo'q, shuning uchun u rad etildi.
- Backend:
  - `app/services/realtime.py` — EMQX HTTP API mijozi (basic auth AppID/AppSecret).
  - Buyruq yaratilgach imzolangan konvert `sh/v1/{home}/cmd` ga **best-effort** e'lon qilinadi. Xato bo'lsa buyruq baribir yaratiladi, tarixga "polling will deliver" yoziladi va polling yetkazadi.
- Hub broker'dan buyruq olib ack yuborsa (polling hali olmagan bo'lsa), backend buyruqni `sent` ga o'tkazadi ("delivered via realtime broker") va keyingi polling uni qayta bermaydi.
- `GET /api/v1/realtime/credentials`:
  - realtime yoqilmagan bo'lsa `{enabled: false, transport: "polling"}` qaytadi;
  - yoqilgan bo'lsa `app-{user_id}` hisobi yaratiladi yoki yangilanadi; har so'rovda **yangi parol** beriladi;
  - ACL: faqat a'zo bo'lgan uylarning `sh/v1/{home}/#` topiklariga `subscribe`, qolgan hamma narsa `deny`;
  - broker ishlamasa → `503 REALTIME_UNAVAILABLE` + polling ko'rsatmasi;
  - so'rov limiti: daqiqasiga 10.
- Production konfiguratsiyasi: `REALTIME_PROVIDER=emqx_serverless` bo'lsa API base, App ID/Secret va `wss://` URL majburiy. Ular bo'lmasa ilova ishga tushmaydi.
- Hub:
  - ixtiyoriy cloud MQTT ulanishi (TLS, `hub-{home}` hisobi);
  - `sh/v1/{home}/cmd` dan buyruq oladi;
  - har bir qurilmaning to'liq holatini va availability'ni **retained** qilib e'lon qiladi;
  - `hub/health` ni ham retained qilib e'lon qiladi;
  - telemetriya broker'ga **yuborilmaydi**.
  - Bir xil `command_id` ikki yo'ldan kelsa bir marta bajariladi. Takroriy nusxa jim tashlab yuboriladi (ack yo'q). Shu bilan buyruq o'zining nusxasi tufayli `rejected` bo'lib qolmaydi.
- Hub oxirgi config'ni (`home_id` bilan birga) SQLite'da saqlaydi, shuning uchun internetsiz qayta ishga tushganda ham qurilmalarni biladi.

Yaratilgan/o'zgartirilgan fayllar:
- `docs/decisions/0008-managed-mqtt-emqx-serverless.md`, `docs/decisions/README.md`
- `services/backend/app/services/realtime.py`, `app/api/v1/realtime.py`, `app/services/commands.py`, `app/api/v1/commands.py`, `app/api/deps.py`, `app/main.py`, `app/core/config.py`, `.env.example`, `requirements*.txt` (httpx runtime'ga ko'chdi)
- `services/backend/tests/test_realtime.py`, `tests/test_commands.py` (broker orqali yetkazilgan buyruq testi)
- `services/hub/gateway/{core,config}.py`, `.env.example`
- `services/hub/tests/{conftest,test_integration,test_realtime_chain}.py`

Testlar (lokal). "Cloud broker" o'rnida ikkinchi haqiqiy Mosquitto ishlatildi, ya'ni bu `[SIM]`:
- `services/hub`: 30 passed (Python 3.10 da ketma-ket 3 marta, Python 3.12 da 1 marta) [SIM]:
  - polling 30 s ga qo'yilganda buyruq broker orqali **< 2 s** da `confirmed` bo'ladi;
  - holat ilova-obunachiga **< 2 s** da yetadi (`reported/good`); telemetriya broker'da yo'q;
  - broker o'chirilganda buyruq polling bilan `confirmed` bo'ladi;
  - bir xil buyruq ikki yo'ldan kelganda qurilma uni faqat bir marta oladi va `rejected` voqeasi yo'q;
  - Hub internetsiz qayta ishga tushganda keshlangan config ishlatiladi.
- `services/backend`: 217 passed (SQLite + PostgreSQL) [SIM]. Ular orasida: EMQX so'rov formati (MockTransport), broker xatosi buyruqni to'xtatmasligi, credentials faqat o'qish uchun va boshqa uyni ko'rmasligi, parol rotatsiyasi, production konfiguratsiya tekshiruvi.

Hal qilinmagan xavflar:
- EMQX Serverless'ning foydalanuvchi va ACL endpoint yo'llari **tasdiqlanmagan** (hujjat sayti tarmoqdan bloklangan edi). Haqiqiy hisob ochilganda `/realtime/credentials` birinchi bo'lib sinalishi kerak.
- JWT yo'qligi sababli `app-*` paroli muddatsiz. Paroli sizgan hisob baribir faqat o'qiy oladi. Eski hisoblarni tozalash cron'i yo'q (Faza 7).
- Bepul limit: har bir ochiq PWA oynasi sessiya-daqiqa sarflaydi. PWA fon holatiga o'tganda ulanishni uzishi kerak (Faza 6).
- Hub ↔ EMQX TLS sertifikati tizimning standart CA ro'yxati bilan tekshiriladi; real ulanish sinalmagan.

Egasi bajarishi kerak bo'lgan qo'lda qadamlar (iPad'dan):
1. EMQX Cloud → Serverless deployment yaratish.
2. Authentication bo'limida `hub-<home_id>` foydalanuvchisini yaratish; ACL: `sh/v1/<home_id>/#` uchun pub/sub ruxsat.
3. Standart avtorizatsiya qoidasini "deny" qilish.
4. API bo'limida App ID/Secret yaratish → backend `.env` (`EMQX_*`, `REALTIME_WSS_URL`).
5. Hub `.env` ga `CLOUD_MQTT_*` yozish.

Keyingi faza: 6 — PWA.

---

## Faza 6 — PWA (veb + telefon + iPad) — 2026-10-07
Holat: tugadi `[SIM]`. Ilova haqiqiy backend, Hub, Mosquitto va simulyator bilan Chromium'da **telefon (Pixel 7) va iPad emulyatsiyasida** sinaldi. Haqiqiy iPhone/iPad'da va Safari'da sinalmagan. iOS'ga o'rnatish va Web Push Faza 7 dan keyin, haqiqiy domen va HTTPS bilan tekshiriladi.

Qilingan ishlar:
- ADR 0009: access token faqat JS xotirasida. Refresh token `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth` cookie'da. Brauzer `X-Client: web` sarlavhasini yuboradi (CSRF himoyasi); body rejimi Hub va CLI uchun saqlanib qoldi. Production'da `COOKIE_SECURE=false` bilan ilova ishga tushmaydi.
- Backend'ga qo'shildi: cookie rejimi, `GET /auth/sessions`, `DELETE /auth/sessions/{id}`.
- `apps/web` (React 18 + TS + Vite, TanStack Query, zustand, i18next, vite-plugin-pwa):
  - Ekranlar: login, bosh sahifa (★ bilan sozlanadigan kartalar), xonalar, qurilmalar markazi (qidiruv; tur, holat va xona bo'yicha filtr), qurilma sahifasi (barcha qiymatlar va buyruqlar tarixi), Hub holati, sozlamalar (til, mavzu, PIN, parol, sessiyalar, hamma joydan chiqish), a'zolar (faqat owner).
  - Boshqaruv elementlari capability'ga qarab avtomatik chiziladi:
    - switch, dimmer;
    - climate — IR, "taxminiy" belgisi bilan;
    - cover, lock, contactor — **PIN dialogi** bilan; kontaktorda holat faqat yordamchi kontakt bo'yicha ko'rsatiladi;
    - valve — **davomiylik majburiy**, qurilmaning `max_runtime_s` i bilan cheklangan;
    - sensorlar faqat ko'rsatiladi.
  - Holat belgilari: ✓ / ⏳ / ≈ / ⚠ / ? / "Qo'llab-quvvatlanmaydi". Noma'lum qiymat "—" bo'lib ko'rinadi, hech qachon "0" yoki "O'chirilgan" bo'lib emas.
  - Hub offline bo'lsa yoki Hub ulanmagan bo'lsa banner chiqadi va boshqaruv o'chiriladi.
  - Buyruq yuborilganda optimistik yangilanish **yo'q**: `queued → sent → acked → confirmed` bosqichlari haqiqiy backend holati bo'yicha ko'rsatiladi. Qurilma qiymati faqat qurilma xabar qilgandan keyin o'zgaradi.
  - Real-time: `/realtime/credentials` yoqilgan bo'lsa mqtt.js (WSS) ulanadi. Ilova fon holatiga o'tsa ulanish uziladi (bepul limitni tejash uchun). Realtime bo'lmasa har 3 s da polling. mqtt.js faqat kerak bo'lganda yuklanadi.
  - Lokal rejim: ilova `hub.local` dan ochilgan bo'lsa banner chiqadi. HTTPS sahifadan `http://hub.local` ni tekshirib bo'lmaydi (mixed content) — bu ADR 0003 dagi ochiq savol.
  - PWA: manifest, ikonkalar (SVG + PNG 192/512/180), offline sahifa. Service worker API javoblarini **keshlamaydi**, shunda eskirgan holat haqiqiy bo'lib ko'rinmaydi.
  - i18n: uz to'liq; ru va en ham to'liq tarjima qilindi; uchala tildagi kalitlar bir xil ekanini test tekshiradi.
  - Dizayn tokenlari (CSS o'zgaruvchilari), dark/light/system mavzu, 44 px tugmalar, `safe-area` qo'llab-quvvatlanadi.

Testlar paytida topilgan va tuzatilgan xatolar:
1. `not_supported` qiymat "—" bo'lib chiqib, "Qo'llab-quvvatlanmaydi" yozuvi ko'rinmagan (tekshiruvlar tartibi noto'g'ri edi). Unit test topdi.
2. Bosh sahifadagi zustand selektori har renderda yangi `[]` qaytargani uchun cheksiz render sikli bo'lgan (React #185). E2E topdi. Tuzatildi va regressiya testi qo'shildi.

Yaratilgan/o'zgartirilgan fayllar:
- `docs/decisions/0009-web-token-storage.md`
- `services/backend/app/api/v1/auth.py`, `app/services/auth.py`, `app/core/config.py`, `tests/test_web_auth.py`, `tests/conftest.py`
- `apps/web/` — `package.json` (versiyalar qotirilgan), `package-lock.json`, `vite.config.ts`, `tsconfig.json`, `playwright.config.ts`, `index.html`, `public/*`, `src/**` (api, auth, i18n, lib, components, pages, theme, test), `e2e/{stack.py,light.spec.ts,screens.spec.ts}`
- `services/hub/gateway/__main__.py` (httpx log'i jim), `.github/workflows/test.yml` (`web` job), `.gitignore`

Testlar (lokal):
- `npx tsc -b` → xatosiz.
- `npx vitest run` → 21 passed: holat belgilari, "qiymat o'ylab topilmaydi", optimistik emaslik, HUB_UNREACHABLE xabari, viewer cheklovi, Hub offline, PIN oqimi va bekor qilish, PIN o'rnatilmagan holat, klapan davomiyligi, IR "taxminiy", 401 → refresh → qayta so'rov, tokenlar web storage'da yo'qligi, i18n kalitlari.
- `npx playwright test` → 4 passed (telefon va iPad emulyatsiyasi × 2 stsenariy) [SIM]:
  - login → chiroqni yoqish → `confirmed` → sahifani yangilash (sessiya cookie orqali tiklanadi) → o'chirish;
  - darvoza → PIN → gerkon bilan `confirmed` → yopish.
- E2E ketma-ket 15 marta ishga tushirildi: 14 marta 4/4, **1 marta 3/4**. O'sha muvaffaqiyatsizlikning log'i saqlanmagan (`tail -1` bilan ishga tushirilgan edi), sababi **aniqlanmadi**. Shundan keyingi 12 ishga tushirish 4/4. Playwright `retries: 0` qoldirildi (xato yashirilmaydi), CI'da xato bo'lsa trace saqlanadi.
- `cd services/backend && pytest` → 230 passed (SQLite + PostgreSQL).

Hal qilinmagan xavflar:
- E2E'da bir marta sababi noma'lum muvaffaqiyatsizlik bo'ldi (yuqorida).
- Haqiqiy iOS Safari'da sinalmagan: PWA o'rnatish, `dialog` elementi va cookie xatti-harakati.
- Lokal rejim (`hub.local`) faqat aniqlash darajasida. Hub'da `local-api` yo'q, shuning uchun internetsiz telefondan boshqarish **hali ishlamaydi**.
- Web Push va bildirishnomalar — Faza 13.

Keyingi faza: 7 — cPanel'ga deploy (hostmaster.uz).
