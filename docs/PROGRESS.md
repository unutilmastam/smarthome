# Progress

Har bir faza tugagach shu yerga hisobot qo'shiladi (shablon: `docs/PHASES.md`).
Belgilar: `[SIM]` — simulyatsiyada, `[REAL]` — haqiqiy apparatda sinalgan.

| Faza | Nomi | Holat |
|---|---|---|
| 0 | Tayyorgarlik (hujjatlar) | tugadi |
| 1 | Poydevor (monorepo, contracts, CI) | tugadi, CI yashil |
| 2 | Backend asosi (auth, uy, xona, qurilma reyestri) | tugadi, CI yashil |
| 3 | Buyruqlar (imzo, hayot sikli, Hub API) | tugadi `[SIM]` |
| 4 | Home Hub + simulyator | boshlanmagan |

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

Keyingi faza: 4 — Home Hub + simulyator.
