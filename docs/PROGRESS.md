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
| 7 | cPanel'ga deploy | qisman: avtomatik deploy, zaxira va qaytish tayyor (ADR 0011), lokal PostgreSQL'da sinaldi; **haqiqiy hostingga deploy qilinmagan**: GitHub Secrets kiritilishi kutilmoqda |
| 8 | Birinchi real qurilma (ESP32 rele) | qisman: proshivka, o'rnatish yo'riqnomasi va UI tayyor; **apparatda sinalmagan** (`[REAL]` jadval bo'sh) |
| 9 | Elektr monitoring | qisman: `[SIM]` tugadi; haqiqiy hisoblagich bilan solishtirilmagan (`[REAL]` yo'q) |
| 10 | Kameralar (lokal) | qisman: bulut tomoni va Hub monitoringi `[SIM]`; Frigate va kameralar apparatda sinalmagan |
| 11 | Darvoza, konditsioner, xavfsizlik, sug'orish | qisman: shartnoma, Hub, proshivka, UI va nosozlik testlari `[SIM]` tugadi; **apparatda sinalmagan** (`[REAL]` jadvallar bo'sh, inventar H-05/H-06/H-11/H-13 ochiq) |
| 12 | Avtomatika (Hub'da) | tugadi `[SIM]`: format, validatsiya, Hub dvigateli, vizual muharrir; haqiqiy uyda sinalmagan |
| 13 | Bildirishnomalar | tugadi `[SIM]`: Telegram (webhook, bog'lash kodi, "Ko'rdim"), Web Push (VAPID), nazoratchi cron, tasdiqlash; haqiqiy bot va telefonda sinalmagan |
| 14 | Mustahkamlash | tugadi: skanlar (zaiflik va sir yo'q), port bog'lash xatosi tuzatildi, zaxiradan tiklash haqiqiy PostgreSQL'da bajarildi, 7 runbook; tashqi port skani va production'da tiklash mashqi `[REAL]` qoldi |

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

CI: run #6 (commit `feff73c`) → **failure** (`web` job: e2e stack ko'tarilmadi — CI'da `uvicorn` o'rnatilmagan edi; lokal venv'da bor edi). Tuzatish commit `7bf12c6` da: `requirements-dev.txt` o'rnatiladi, `stack.py` xatoda tez to'xtaydi va bola jarayonlarni o'chiradi. Xato CI'ga o'xshash toza venv'da qayta hosil qilindi, tuzatishdan keyin 4/4 o'tdi.

Keyingi faza: 7 — cPanel'ga deploy (hostmaster.uz).

---

## Faza 7 — cPanel'ga deploy (hostmaster.uz) — 2026-10-07
Holat: **qisman**. Deploy uchun kerakli hamma narsa yozildi va lokal sinaldi. **Haqiqiy hostingga deploy bajarilmadi**: buning uchun cPanel SSH kaliti, GitHub Secrets va subdomen kerak; ular egasida (runbook'da qadamma-qadam yozilgan). Tugash mezoni (`https://<domen>/api/v1/health` → ok; telefondan simulyatorni boshqarish) hali **bajarilmagan**.

Qilingan ishlar:
- `passenger_wsgi.py`: cPanel Python App `Application URL = /api` ga o'rnatiladi. Passenger `SCRIPT_NAME=/api` qilib prefiksni olib tashlaydi; uni FastAPI'ga qaytarib beradigan WSGI o'rami qo'shildi. Ilova domen ildiziga o'rnatilganda ham ishlaydi (ikkalasi test bilan tekshirilgan).
- Production'da OpenAPI va Swagger **o'chiq** (`DOCS_ENABLED` bilan ochish mumkin).
- Cron job'lar:
  - `python -m app.jobs.expire_due` (har daqiqa);
  - `python -m app.jobs.retention` (kunlik: rate limit hisoblagichlari, 30 kundan eski sessiyalar; audit va buyruqlar tarixi saqlanadi);
  - `backup.sh` (kunlik `pg_dump` → `~/backups`, 14 kun, ruxsat 600, parollar faqat `~/.pgpass` da).
- `infra/cpanel/build_release.sh`: release yig'adi.
  - `api/`: faqat runtime fayllar va `contracts/` nusxasi.
  - `web/`: PWA va `.htaccess`.
  - Release ichida `.env`, kalit yoki parol fayli bo'lsa **to'xtaydi**.
- `infra/cpanel/web.htaccess`:
  - HTTPS'ga yo'naltirish, SPA fallback (`/api` ga tegmaydi);
  - HSTS, CSP (`connect-src` faqat o'z domeni + EMQX WSS), `nosniff`, `frame-ancestors 'none'`;
  - `sw.js` va `index.html` keshlanmaydi, hash'li fayllar `immutable`.
- `.github/workflows/deploy-cloud.yml`:
  - `main` da `test` yashil bo'lsa yoki qo'lda ishga tushiriladi;
  - faqat `DEPLOY_ENABLED=true` bo'lganda ishlaydi;
  - qadamlar: PWA build → release → rsync (SSH, `StrictHostKeyChecking=yes`, `.env` ga tegmaydi) → `pip install` → `alembic upgrade head` → `tmp/restart.txt` → health check;
  - sirlar faqat GitHub Secrets'da.
- `docs/runbooks/deploy.md`: iPad'dan bajariladigan qadamlar — 2FA, subdomen + AutoSSL, PostgreSQL, Setup Python App, `.env`, SSH kalit va Secrets, birinchi deploy, `create-owner`, cron, Hub'ni ulash, muammolarni hal qilish.
- PWA'ga **Hub qo'shish va bekor qilish** qo'shildi (owner yoki admin): token va kalit bir marta ko'rsatiladi, "Nusxalash" tugmasi bor. Bu bo'lmasa egasi kompyutersiz Hub yarata olmasdi.

cPanel'ni imitatsiya qilib sinash (lokal, `[SIM]`):
- `build_release.sh` → release yig'ildi; ichida sir yo'q.
- Toza Python 3.10 venv + **faqat** release'dagi `requirements.txt` + `ENV=production` + toza PostgreSQL 16:
  - `alembic upgrade head` → OK;
  - Passenger orqali (`SCRIPT_NAME=/api`) `GET /v1/health` → `200 {"status":"ok"}`;
  - `contracts` release ichidan topildi; docs o'chiq;
  - `create-owner` → OK;
  - `expire_due` va `retention` job'lari → OK.
- `backup.sh` → `pg_dump` OK (16 jadval). Dump'dan **yangi bazaga tiklash** sinaldi: foydalanuvchi va uy qaytdi.
- `index.html` da inline skript yo'q, ya'ni CSP `script-src 'self'` bilan mos.

Testlar:
- `cd services/backend && pytest` → 237 passed (SQLite + PostgreSQL): Passenger prefiksi, production'da docs o'chiqligi, `expire_due` va `retention` job'lari.
- `apps/web`: `tsc` OK, `vitest` → 23 passed (Hub yaratish: sirlar bir marta ko'rsatiladi; family Hub qo'sha olmaydi).
- `deploy-cloud.yml` **ishga tushirilmagan** (Secrets yo'q).

Hal qilinmagan xavflar / egasi bajarishi kerak:
- Runbook bo'yicha hosting sozlamalari. Avval aniqlanishi kerak: H-01b (Python versiyasi), H-01c (PostgreSQL versiyasi), H-01e (cron oralig'i, 2FA).
- `.htaccess` dagi `Header` va `RewriteRule` lar hostmaster.uz Apache/LiteSpeed'da sinalmagan. Sarlavhalarni deploy'dan keyin tekshirish kerak (masalan, securityheaders.com).
- Hosting `a2wsgi`/Passenger bilan ko'p jarayonli rejimda real yuklama ostida sinalmagan.
- PWA'da qurilma va xona qo'shish UI'i hali yo'q — hozircha faqat API orqali. Bu Faza 8 dan oldin kerak bo'ladi.

Keyingi faza: 8 — Birinchi real qurilma (ESP32 rele + chiroq).

---

## Faza 8 — Birinchi real qurilma (ESP32 rele + chiroq) — 2026-10-07
Holat: **qisman**. Apparat yo'q (H-02, H-08), shuning uchun `[REAL]` testlarning **birortasi ham bajarilmagan**. Tugash mezoni ("`[REAL]` testlar hisobotda") **bajarilmagan**. Tayyorlangan narsalar pastda.

Qilingan ishlar:
- ADR 0010: ESPHome proshivkasi lokal MQTT shartnomasini **o'zi gapiradi** (`on_json_message` + `publish_json`). Ack proshivkadan keladi. Hub'da alohida "adapter" yo'q, PHASES dagi tegishli band ADR bilan almashtirildi. Sabab: standart ESPHome topiklarida ack yo'q, adapter ack'ni o'zi "yasashi" kerak bo'lardi.
- `devices/esphome/common/base.yaml`:
  - Wi-Fi (ochiq zaxira AP yo'q);
  - shifrlangan native API;
  - OTA paroli;
  - SNTP (UTC);
  - MQTT: login = `device_key`; standart topiklar o'chirilgan; `birth`/`will`/`shutdown` → `home/<key>/availability` (retained);
  - broker 15 daqiqa yo'q bo'lsa qayta yuklanish.
- `devices/esphome/light-relay.yaml`:
  - rele `restore_mode: ALWAYS_OFF`;
  - devordagi tugma Hub va internetsiz ham ishlaydi;
  - `cmd` → tekshiruv → ack (`acked` yoki `rejected: invalid_params`) → rele;
  - retained `state` doim to'liq holat;
  - `command_id` bo'lmagan xabar e'tiborsiz qoldiriladi.
- `devices/esphome/secrets.example.yaml` (`secrets.yaml` gitignore'da), har bir qurilmaga alohida kalit va parollar.
- `infra/hub/install.md`: Ubuntu 24.04 o'rnatish (kompyutersiz variantlar bilan), DHCP reservation, `hub.local` (avahi), ufw (faqat LAN va Tailscale), Tailscale SSH, UPS/NUT va "Restore on AC power loss", stack'ni ishga tushirish, ESPHome Dashboard, yangilanishlar va tekshiruv ro'yxati.
- `docker-compose.yml` ga ESPHome Dashboard qo'shildi (parol bilan, `network_mode: host`, ufw bilan faqat LAN/Tailscale).
- PWA: **qurilma qo'shish** (kalit, nom, xona, imkoniyatlar; klapan uchun `max_runtime_s` majburiy) va **xona qo'shish**. Usiz egasi kompyutersiz qurilma qo'sha olmasdi.
- `docs/hardware/tests/light-relay.md`: 12 bandli `[REAL]` sinov jadvali. Elektrik yoki egasi to'ldiradi.
- CI'ga `firmware` job qo'shildi: har bir YAML uchun `esphome config` va `esphome compile`.

Testlar:
- `esphome config light-relay.yaml` (ESPHome 2026.9.1) → **Configuration is valid** (lokal).
- `esphome compile` lokal **bajarilmadi**: muhitning tarmoq siyosati PlatformIO registry'ni bloklaydi (403). Kompilyatsiya, ya'ni lambda C++ kodini tekshirish, CI'dagi `firmware` job'da bo'ladi. Natija keyingi CI run'da ko'rinadi.
- `apps/web`: `tsc` OK, `vitest` → 26 passed (qurilma qo'shish, klapan uchun `max_runtime_s` majburiyligi, backend xatosini ko'rsatish).
- `docker compose --profile sim config` → OK. ESPHome image tegi (`2026.9.1`) Docker bilan tekshirilmagan.
- `[REAL]`: **0 / 12**.

Hal qilinmagan xavflar:
- Birinchi proshivkani yozish uchun USB va Chrome (Web Serial) kerak; iPad Safari'da bu ishlamaydi (install.md'da muqobillar yozilgan).
- Internet uzilganda telefondan boshqarish uchun Hub'da `local-api` kerak. U hali yo'q; hozircha faqat devordagi tugma ishlaydi.
- `on` holati — firmware boshqarayotgan rele chiqishi, chiroq haqiqatan yonganining isboti emas. Kuchliroq tasdiq uchun tok sensori (ARCHITECTURE 10) — ixtiyoriy.

Keyingi faza: 9 — Elektr monitoring.

---

## Faza 9 — Elektr monitoring — 2026-10-07
Holat: **qisman**. Kod va `[SIM]` testlar tugadi. Tugash mezoni ("o'lchov haqiqiy hisoblagich bilan solishtirilgan `[REAL]`") **bajarilmagan** — apparat yo'q (H-04, H-08).

Qilingan ishlar:
- Jadvallar va migratsiya `0003`:
  - `telemetry_1m` (30 kun) va `telemetry_1h` (2 yil): `avg/min/max/last/count`;
  - `energy_daily` (doimiy): kVt·soat va narx;
  - `homes.tariff_per_kwh` (standart holatda **yo'q**) va `currency` (UZS).
- Hub: har bir daqiqa uchun agregatsiya qiladi. Xom o'lchovlar Hub SQLite'da 7 kun saqlanadi. Agregatlar outbox orqali `POST /hub/telemetry:batch` ga yuboriladi, ya'ni internet uzilsa buferda kutib turadi. Faqat `reported` sonli qiymatlar hisoblanadi (`assumed` emas).
- Backend qabul qilishda tekshiradi: qurilma, metrika, sonli tur, `not_supported`, kelajak vaqti, `min ≤ avg ≤ max`, contracts chegaralari. Shu bucket qayta yuborilsa eskisi almashtiriladi (idempotent).
- `contracts/schemas/telemetry-batch.schema.json` (ts — daqiqa boshi, UTC).
- Hisob-kitob (`python -m app.jobs.energy`, soatlik cron):
  - 1m → 1h roll-up; oxirgi 3 soat qayta hisoblanadi, shunda kech kelgan ma'lumot ham o'z joyiga tushadi;
  - kunlik kVt·soat **uyning lokal kuni** bo'yicha (`Asia/Tashkent`), hisoblagich nolga qaytsa ham to'g'ri (`counter_delta`);
  - ma'lumot yo'q kun yozilmaydi, ya'ni "0" emas;
  - tarif kiritilmagan bo'lsa narx `null` qoladi.
- API:
  - `GET /homes/{id}/energy/summary?period=day|month`: jami va qurilmalar bo'yicha; ma'lumot yo'q bo'lsa `null`;
  - `GET /devices/{id}/telemetry?metric=&resolution=1m|1h&hours=`;
  - `PATCH /homes/{id}`: `tariff_per_kwh`, `currency`.
- Retention: 1m > 30 kun va 1h > 2 yil o'chiriladi.
- ESPHome:
  - `pzem-meter.yaml` (PZEM-004T v3, UART/Modbus);
  - `sdm-meter.yaml` (SDM120, RS485/Modbus);
  - `contactor.yaml` — bobina = `commanded_closed`, yordamchi kontakt = `aux_contact_closed`; tasdiq faqat yordamchi kontakt bo'yicha. O'lchov hali bo'lmasa (NaN) hech narsa yuborilmaydi.
- Simulyator: `ContactorSim`, nosozliklar `welded` (kontaktlar yopishib qolgan) va `aux_broken`.
- PWA "Elektr" sahifasi:
  - bugun va shu oy uchun kVt·soat va narx (ma'lumot yoki tarif bo'lmasa "Ma'lumot yo'q" / "Tarif kiritilmagan", hech qachon 0 emas);
  - har bir hisoblagich qiymati ishonch belgisi bilan;
  - oxirgi 6 soatlik quvvat grafigi (bo'shliqlar to'ldirilmaydi);
  - tarif sozlamasi;
  - eslatma: "avtomat (breaker) holati ko'rsatilmaydi".

Testlar:
- backend → 258 passed (SQLite + PostgreSQL). Shu jumladan: ingest rad etishlari (6 holat), idempotentlik, hisoblagich nolga qaytishi, lokal kun chegarasi, tarifsiz `null`, roll-up, purge, API.
- hub → 33 passed [SIM]:
  - PZEM simulyatori → gateway → backend `telemetry_1m`; `not_supported` chastota yuborilmaydi; xom o'lchovlar Hub'da qoladi;
  - kontaktor faqat yordamchi kontakt bilan `confirmed`; kontaktlar yopishib qolsa → `no_feedback` va haqiqiy holat (`aux=true`) ko'rinadi.
- web → `tsc` OK, vitest 27 passed, Playwright 4 passed [SIM].
- contracts → 59 passed.
- `esphome config`: pzem, sdm, contactor, light → hammasi valid. `esphome compile` CI'ning `firmware` job'ida bo'ladi (lokal tarmoq PlatformIO'ni bloklaydi).

Hal qilinmagan xavflar:
- O'lchov aniqligi haqiqiy hisoblagich bilan solishtirilmagan. `[REAL]` jadval Faza 15 da.
- Tarif bir xil narxda. O'zbekistonda pog'onali (ijtimoiy norma) tarif bo'lsa, model kengaytiriladi (H-04 bilan birga aniqlanadi).
- SDM630 (3 faza) uchun fazalar bo'yicha shartnoma hali yo'q (H-04a).
- Soatlik cron hostingda hali sozlanmagan (Faza 7 deploy'dan keyin).

Keyingi faza: 10 — Kameralar (lokal).

---

## Faza 10 — Kameralar (lokal) — 2026-10-07
Holat: **qisman**. Bulut tomoni, Hub'dagi Frigate monitoringi va "videosiz bulut" tekshiruvi tayyor. Frigate'ning o'zi, kameralar, HDD va VLAN apparatda **sinalmagan** (H-03, H-07). "Internet o'chiq paytda yozuv davom etadi" testi **bajarilmagan** — Frigate apparati kerak.

Qilingan ishlar:
- Migratsiya `0004`:
  - `cameras.device_id`: kamera holati `camera` capability'li qurilma orqali (contracts'dagi `stream_available`, `recording`, `disk_usage_pct`);
  - `hubs.tailnet_host` va `hubs.lan_host`: Hub'ning o'zi heartbeat'da yuboradi.
- API:
  - `GET/POST /homes/{id}/cameras` va `DELETE /cameras/{id}` (`configure`);
  - `GET /cameras/{id}/access` — `camera_live` ruxsati bilan faqat **havolalar** qaytaradi (Tailscale va LAN, Frigate'ning login talab qiladigan porti 8971). Har bir kirish audit'ga yoziladi. Family uchun standart holatda 403 (ARCHITECTURE 9: "sozlanadi").
- Bulut videoni hech qachon saqlamaydi, proxy qilmaydi va relay qilmaydi (ADR 0006). Avtomatik tekshiruvlar:
  - testlar: DB sxemasida binary ustun yo'q va video/snapshot/clip/image nomli ustun yo'q; API faqat `application/json` qabul qiladi (fayl yuklash endpoint'i yo'q);
  - `python -m app.jobs.no_video_check [papkalar]`: **jonli DB** (bytea/blob ustunlar) va **hosting fayllari** (kengaytma va fayl signaturasi bo'yicha, nomi o'zgartirilgan fayllar ham) tekshiriladi. CI'da release'ga qarshi va deploy'dan keyin serverning o'zida ishlaydi.
- Hub:
  - `gateway/frigate.py`: Frigate API'dan faqat `/api/stats` va `/api/config` o'qiladi (media yo'q);
  - stats bo'lmasa `stream_available` noma'lum qoladi, ya'ni taxmin qilinmaydi;
  - disk ≥ 85% → log va `health.disk_warning`;
  - Frigate ishlamasa kameralar availability'si `unknown`;
  - heartbeat'da `tailnet_host` va `lan_host` yuboriladi.
- `docker-compose.yml` ga Frigate qo'shildi (`cameras` profili). Image `ghcr.io/blakeblackshear/frigate:0.18.0` — teg registry'da **tekshirildi**; ESPHome `2026.9.1` tegi ham tekshirildi. Konfiguratsiya namunasi `frigate/config.example.yml`: auth yoqilgan, RTSP sirlari env'dan olinadi, kameralar alohida VLAN'da.
- PWA "Kameralar" sahifasi:
  - holat belgilari;
  - disk ≥ 85% ogohlantirishi;
  - "Jonli ko'rish" → Hub'dagi Frigate'ga havola (sahifada `<video>` yoki `<img>` **yo'q**);
  - ruxsat bo'lmasa tugma ko'rsatilmaydi;
  - kamera qo'shish.

Faza 9 CI'sida topilgan va shu fazada tuzatilgan xatolar (run #7):
1. **Telefonda gorizontal overflow** (haqiqiy UI xatosi). `.app` CSS grid'ida bolalar `min-width:auto` bo'lgani uchun nav (yangi "Elektr" va "Kameralar" bilan) butun sahifani 763 px'ga kengaytirgan. Telefonda sahifa kichraygan, tugmalar ekrandan chiqib ketgan. Tuzatildi (`minmax(0,1fr)`) va regressiya testi qo'shildi: telefon va iPad'da 8 ta sahifada gorizontal overflow yo'q.
2. **PIN dialogidagi race**: dialog ochilgandan keyin, paint'dan so'ng ishlaydigan effekt PIN'ni tozalagan — tez kiritilgan PIN o'chib ketgan, iPad'da "Tasdiqlash" faol bo'lmagan. Tuzatildi: PIN dialog yopilganda tozalanadi.
3. **Buyruq kuzatuvidagi race**: eski buyruqning kechikkan javobi yangi buyruq holatining ustiga yozilishi mumkin edi. Tuzatildi (generation hisoblagichi). Test tuzatishsiz yiqiladi, tuzatish bilan o'tadi.
4. **Simulyator**: qurilma SUBACK'dan oldin "online" deb hisoblangan. Sekin CI'da birinchi buyruq yo'qolishi mumkin edi. `hub 3.10` dagi IR test xatosining ehtimoliy sababi shu: lokal 15/15 o'tdi, qayta hosil qilinmadi. Endi `wait_status` xato bo'lganda buyruqning holati va voqealarini chiqaradi.
5. E2E ko'p marta login qilgani uchun o'zimizning **login limitiga** (IP bo'yicha 20/5 daq) tushgan — himoya ishlayapti. Limit sozlanadigan qilindi (`LOGIN_IP_LIMIT`) va faqat E2E stack'da oshirildi.
- Avvalgi (Faza 6) bitta noma'lum E2E xatosi va CI'dagi telefondagi xato, katta ehtimol bilan, 1 va 2-xatolar edi.

Testlar (lokal):
- backend → 271 passed (SQLite + PostgreSQL), shu jumladan 15 ta kamera testi.
- hub → 36 passed (Python 3.10 va 3.12) [SIM]: Frigate holati bulutga yetadi; Frigate o'chsa `unknown`; disk ogohlantirishi; Frigate'dan faqat holat endpoint'lari o'qiladi; kamera havolalari heartbeat'dagi manzillardan tuziladi.
- web → vitest 30 passed; Playwright: to'liq to'plam 4 marta takrorlandi → **24/24** (telefon + iPad, layout testi bilan).
- `no_video_check`: PostgreSQL sxemasi va release fayllari → `NO VIDEO: OK`.

Hal qilinmagan xavflar:
- Frigate, kameralar, HDD retention va internet o'chiq paytdagi yozuv — `[REAL]` emas.
- PWA'dagi havola Frigate UI'ning bosh sahifasini ochadi; kameraning to'g'ridan-to'g'ri deep-link formati sinalmagan.
- Telefonda kamerani ko'rish uchun Tailscale ilovasi yoqilgan bo'lishi shart.
- Family uchun `camera_live` sozlamasi (har bir a'zoga alohida) hali yo'q.

Keyingi faza: 11 — Darvoza, konditsioner, xavfsizlik, sug'orish.

---

## Qo'shimcha: Avtomatik rejim va yangi dizayn — 2026-10-07
Holat: tugadi `[SIM]`. Haqiqiy hostingda hali ishga tushmagan.

Qilingan ishlar:
- **Avtomatik deploy (ADR 0011).** `main` ga har bir merge'dan keyin quyidagi ketma-ketlik ishlaydi:
  1. testlar;
  2. migratsiyalar expand-only ekani tekshiriladi;
  3. toza PostgreSQL'da `alembic upgrade head`;
  4. `deploy.sh` stsenariylari sinaladi;
  5. faqat hammasi o'tsa — serverda `pg_dump` (oxirgi 10 ta saqlanadi), so'ng kod → migratsiya → restart → `/api/v1/health` (aynan yangi build javob berishi shart);
  6. xato bo'lsa — kod va DB zaxiradan avtomatik qaytariladi va Telegram'ga xabar ketadi.
- Secrets yo'q bo'lsa, deploy job'i yiqilmaydi, faqat o'tkazib yuboriladi.
- `CLAUDE.md` ga "Avtomatik rejim" bo'limi qo'shildi.
- **PWA dizayni yangilandi:**
  - SVG ikonkalar;
  - holatga qarab rangli qurilma kartalari (chiroq, darvoza, sovutish, suv, quvvat, signal);
  - siljiydigan animatsiyali yoqish/o'chirish tugmasi;
  - buyruq bosqichlari animatsiyali stepper sifatida: Navbat → Hub → Qurilma → Tasdiq;
  - telefonda pastki tab panel, iPad'da yon panel;
  - bosh sahifada statistik plitkalar.
- Statistika faqat tasdiqlangan (reported) qiymatlardan olinadi. Noma'lum qiymat "—" bo'lib ko'rinadi. Tugma "yoqilgan" holatini faqat qurilma tasdiqlagan holatdan oladi.
- Animatsiyalar `prefers-reduced-motion` sozlamasida o'chadi.

Testlar:
- `deploy.sh` stsenariylari — 5/5 `[SIM]`, lokal PostgreSQL bilan: birinchi deploy, buzuq migratsiya → qaytish, buzuq ilova → kod va DB qaytishi, zaxira rotatsiyasi, lock va pg_dump xatosi.
- Expand-only tekshiruvchi — 5 ta test.
- Backend — 278 ta test.
- Web vitest — 30 ta test.
- Playwright E2E — 6 ta o'tdi (telefon + iPad emulyatsiyasi) `[SIM]`.

Sinalmagan:
- haqiqiy hostmaster.uz serverida deploy va qaytish;
- Telegram xabarlari (bot tokeni hali yo'q);
- dizayn haqiqiy telefon va iPad'da (faqat emulyatsiyada ko'rildi).

## Qo'shimcha: Qurilma va bo'limlarni ilovadan boshqarish — 2026-10-07
Holat: tugadi `[SIM]`.

Qilingan ishlar:
- **Qurilma qo'shish ustasi.** "+" tugmasi orqali ochiladi va 2 qadamdan iborat:
  1. tur tanlanadi — 19 ta tur SVG ikonkalari bilan: chiroq, rozetka, darvoza, konditsioner, datchiklar va boshqalar;
  2. nom, bo'lim va ikonka tanlanadi.
- **Kalit (`device_key`)** nomdan avtomatik taklif qilinadi (lotin/kirill transliteratsiyasi). U proshivka bilan bir xil bo'lishi kerak, shuning uchun qo'lda tahrirlash mumkin.
- **Qurilmani tahrirlash va olib tashlash.** Nom, bo'lim va ikonkani o'zgartirish mumkin. Olib tashlashdan oldin tasdiq so'raladi.
- **Bo'limlar (xonalar).**
  - Ikonkali plitkalar ko'rsatiladi: qurilmalar soni va nechtasi yoniqligi. Yoniqlar soni faqat tasdiqlangan holatdan hisoblanadi.
  - Bo'lim qo'shish, tahrirlash va o'chirish mumkin. O'chirishda tasdiq so'raladi, qurilmalar "Bo'limsiz" bo'lib qoladi.
- **Ikonkalar.** 36 ta qurilma va 17 ta bo'lim ikonkasi (inline SVG). Backend'da `devices.icon` va `rooms.icon` ustunlari qo'shildi (migratsiya 0005, expand-only). Ikonka faqat ko'rinish uchun, holatga ta'sir qilmaydi.
- **Real ko'rinishdagi kalit (switch).** Holat qurilmadan tasdiqlangan bo'lsa, kalit shu holatda turadi. Bosilganda teskari buyruq ketadi, buyruq bajarilayotganda aylanuvchi indikator ko'rinadi. Holat noma'lum bo'lsa, kalit holatini taxmin qilmaydi — o'rniga ikkita aniq tugma ko'rsatiladi.
- **Konditsioner** — quvvat kaliti va harorat stepperi. **Darvoza va qulf** tugmalarida ikonkalar bor.
- Yangi qo'shilgan qurilmaning holati Hub uni ko'rmaguncha "Noma'lum" bo'ladi. Bu foydalanuvchiga ochiq aytiladi.

Testlar:
- Backend: 156 o'tdi (ikonka testi bilan). Migratsiya testi PostgreSQL'da o'tdi.
- Web vitest: 35 o'tdi.
- Playwright E2E: 8 o'tdi (telefon + iPad) `[SIM]`. Yangi stsenariy: bo'lim qo'shish → qurilma qo'shish → "Noma'lum" holat → olib tashlash.

Sinalmagan: haqiqiy telefon va iPad'da (faqat emulyatsiya).

---

## Faza 11 — Darvoza, konditsioner, xavfsizlik, sug'orish — 2026-10-07
Holat: qisman.
- `[SIM]` bo'yicha tugadi: har bir tur uchun shartnoma → proshivka → Hub → simulyator → UI → nosozlik testi.
- `[REAL]` yo'q: apparat ma'lum emas (inventar H-05, H-06, H-11, H-13). Firmware C++ kompilyatsiyasi lokal tekshirilmadi (pastga qarang).

Qilingan ishlar:

**Umumiy (ADR 0012)**
- Voqealar oqimi:
  - qurilma yoki Hub `home/{key}/event` ga yozadi;
  - gateway voqeani shartnoma bo'yicha tekshiradi va unga `id` beradi;
  - internet bo'lmasa, voqea outbox'da kutadi;
  - so'ng `POST /hub/events` orqali `events` jadvaliga tushadi (180 kun saqlanadi);
  - foydalanuvchi uni `GET /homes/{id}/events` va "Voqealar" sahifasida ko'radi.
- Voqea turlari va ularning muhimligi (`severity`) `capabilities.json` da belgilanadi. Hub yuborgan muhimlik inobatga olinmaydi.
- `capabilities.json` da har bir capability uchun `config` sxemasi bor. Backend qurilma sozlamalarini shu sxema bilan tekshiradi.

**Darvoza**
- `cover.obstructed` (fotoelement) atributi qo'shildi.
- Proshivka `gate.yaml`:
  - ochiq/yopiq holat faqat gerkondan olinadi;
  - ikkala gerkon bir vaqtda faol bo'lsa → `unknown`, buyruqlar rad etiladi, `cover.sensor_conflict` voqeasi;
  - nur to'silgan paytda "yopish" rad etiladi;
  - darvoza `max_travel_s` ichida oxiriga yetmasa → `cover.travel_timeout`.
- Fotoelement darvoza blokida apparat sifatida ishlashda davom etadi.
- Hub'da "ochiq qoldi" kuzatuvchisi bor (`left_open_after_s`, standart 600 s). U bitta ochiq turish davri uchun bir marta xabar beradi. `unknown` holat "ochiq" deb hisoblanmaydi.

**Konditsioner**
- `climate.running` atributi qo'shildi: CT tok qisqichi orqali o'lchanadi.
- `set_power` faqat `running` bilan `confirmed` bo'ladi. CT bo'lmasa, buyruq halol tarzda `acked` da qoladi.
- IR signal yetib bormasa (`ir_blocked`) buyruq tasdiqlanmaydi.
- Hub'da "ta'sir yo'q" kuzatuvchisi bor: harorat 15 daqiqada ≥ 0.5 °C o'zgarmasa, `climate.no_effect` voqeasi chiqadi. Bu faqat ogohlantirish, tasdiq emas. Hisoblash birinchi ma'lum haroratdan boshlanadi.
- Proshivka: `ir-climate.yaml` (IR + DHT22 + CT).

**Xavfsizlik**
- Yangi `alarm` capability qo'shildi (`control_access`, high risk — PIN so'raladi).
- Dvigatel Hub'da ishlaydi (`gateway/alarm.py`) va internetsiz ham ishlaydi:
  - zonalar: kirish (kechikish bilan) yoki darhol;
  - "Uydaman" rejimi: faqat perimetr;
  - chiqish va kirish kechikishlari;
  - ochiq zona bo'lsa yoqishdan bosh tortadi;
  - signal bo'lsa sirena yoqiladi va `siren_max_s` dan keyin to'xtaydi;
  - zona datchigi oflayn bo'lsa xabar beradi;
  - holat Hub qayta yongandan keyin ham saqlanadi.
- Proshivka: `security-sensor.yaml` va `siren.yaml` (`max_on_s` proshivkada).
- UI: "Xavfsizlik" sahifasi (holat halqasi, 3 ta tugma, zonalar, sozlash oynasi, voqealar). Bosh sahifada holat banneri.

**Sug'orish**
- `valve.open` buyrug'i oqim datchigi bo'lsa `open` **va** `flow > 0` bilan tasdiqlanadi.
- Proshivka `irrigation-valve.yaml`:
  - `max_runtime_s` dan uzun so'rov kesiladi (`valve.runtime_limit`);
  - quruq ishlash himoyasi (`valve.no_flow`);
  - yopiq klapandan oqim (`valve.flow_while_closed`);
  - favqulodda tugma (`valve.emergency_stop`);
  - tok uzilsa — klapan YOPIQ.
- UI: "Hammasini to'xtatish" banneri. U faqat ochiq ekani **tasdiqlangan** klapanlarga yopish buyrug'ini yuboradi.

**Topilgan va tuzatilgan xato**
- Backend `expire_due` da eski (sessiya keshidagi) holat bilan ishlaganligi sababli, ack kelgan buyruq soniyalar ichida noto'g'ri `timeout/no_ack` bo'lib qolardi.
- Bu Hub integratsiya testida kamdan-kam paydo bo'ladigan nosozlikdan topildi.
- Tuzatish: `populate_existing` va vaqtni Python'da qayta tekshirish. Regressiya testi tuzatishsiz yiqiladi, tuzatish bilan o'tadi.
- CI (`hub 3.10`, oldingi commit) yana bitta haqiqiy xatoni ko'rsatdi:
  - Hub'da ikkita `flush_once` bir vaqtda ishlab, bitta telemetriya paketini ikki marta yuborgan;
  - backend esa "o'qi → qo'sh" usulida yozgani uchun unique-key xatosi (500) bergan.
- Tuzatish: Hub'da flush qulf bilan bajariladi, backend'da `INSERT … ON CONFLICT DO UPDATE` (SQLite va PostgreSQL). Ikkala regressiya testi tuzatishsiz yiqiladi.

Yaratilgan/o'zgartirilgan fayllar:
- `packages/contracts/capabilities.json`, `schemas/{capabilities,local-mqtt,hub-events}.schema.json`;
- `docs/decisions/0012-*.md`;
- `services/backend/`: `models/event.py`, `services/events.py`, `api/v1/events.py`, `api/v1/hub.py`, migratsiya `0006_events` (expand), `services/devices.py`, `services/commands.py`;
- `services/hub/gateway/`: `alarm.py`, `watchers.py`, `core.py`, `expectations.py`; `simulator/devices.py`; `mosquitto/acl` (`event`);
- `devices/esphome/`: `gate.yaml`, `ir-climate.yaml`, `irrigation-valve.yaml`, `security-sensor.yaml`, `siren.yaml`;
- `apps/web/`: `pages/{Security,Events}.tsx`, `components/{EventFeed,IrrigationStop}.tsx`, `AlarmCtl`, atributga xos so'zlar (`To'silgan!`, `Ishlayapti`);
- `docs/hardware/tests/{gate,climate-ir,irrigation,security}.md` — `[REAL]` jadvallar (bo'sh).

Testlar:
- Contracts: `pytest packages/contracts` → 66 passed.
- Backend: `cd services/backend && pytest` → 163 passed. PostgreSQL migratsiya testi → 2 passed. Expand-only → OK (6 ta migratsiya).
- Hub: `cd services/hub && pytest` → 66 passed `[SIM]`. Shulardan 20 tasi alarm dvigateli va kuzatuvchilarning unit testlari, 11 tasi to'liq zanjirda nosozlik stsenariylari:
  - fotoelement;
  - gerkon ziddiyati va yurish vaqti tugashi;
  - "ochiq qoldi";
  - CT bilan tasdiq;
  - IR yetmasligi va "ta'sir yo'q";
  - suv yo'q;
  - proshivka limiti bulutdagi sozlamadan ustun;
  - oqish va favqulodda tugma;
  - signalizatsiya: kirish kechikishi → sirena → o'chirish;
  - ochiq derazada yoqishdan bosh tortish;
  - internetsiz signal.
- Web: `npx vitest run` → 42 passed. Playwright → 10 passed (telefon + iPad), shu jumladan signalizatsiyani UI'dan sozlash, PIN bilan yoqish/o'chirish va voqealar tasmasi `[SIM]`.
- Deploy skripti: 5 passed.
- Proshivka: `esphome config` → 5 ta yangi YAML valid. `esphome compile` lokal **bajarilmadi**: tarmoq proksisi PlatformIO registry'ni bloklaydi (403). Kompilyatsiyani CI'dagi `firmware` job bajaradi; natijasi CI'da ko'rinadi.

Hal qilinmagan xavflar:
- Proshivkalar apparatda sinalmagan. Pinlar, IR protokoli (`coolix` — vaqtinchalik) va oqim datchigi koeffitsienti taxminiy.
- Sirena va signalizatsiya hozircha faqat ilovada va voqealar tasmasida ko'rinadi. Telegram/Push xabarnomalari Faza 13 da qo'shiladi; ungacha signal haqida telefonga **xabar kelmaydi**.
- Signalizatsiyada zona chetlab o'tish (bypass) yo'q: ochiq zona bilan yoqib bo'lmaydi.

Tasdiqlanmagan taxminlar:
- Darvoza blokida alohida OPEN/CLOSE/STOP kirishlari bor (H-05).
- Konditsioner IR bilan boshqariladi (H-06).
- Klapan 24 V AC, oqim datchigi YF-S201 (H-11).

Keyingi faza: 12 — Avtomatika (Hub'da).

---

## Faza 12 — Avtomatika (Hub'da) — 2026-10-08
Holat: tugadi `[SIM]`. Haqiqiy uyda va qurilmalarda sinalmagan.

Qilingan ishlar:
- **ADR 0013 va shartnoma:**
  - `automation.schema.json`:
    - triggerlar: qurilma holati (`for_s` bilan), vaqt va kunlar, quyosh chiqishi/botishi ± daqiqa;
    - shartlar: holat, vaqt oralig'i, kun yoki tun, signalizatsiya rejimi;
    - harakatlar: buyruq (`auto_off_after_s` bilan), kutish, xabar;
    - sozlamalar: `cooldown_s`, `max_runs_per_hour`, `manual_override_s`.
  - `hub-automation-runs.schema.json` — bajarilish tarixi formati.
  - ARCHITECTURE 11-bo'lim yakuniy formatga moslashtirildi.
- **Backend:**
  - Jadvallar: `automations` (versiya bilan) va `automation_runs` (90 kun saqlanadi). Migratsiya 0007, expand-only.
  - API: CRUD, `:validate`, run tarixi. Hub qoidalarni `GET /hub/config` orqali oladi.
  - `POST /hub/automation-runs` — id bo'yicha idempotent.
  - Validatsiya qoidalari:
    - qurilma, capability, atribut va qiymat shartnoma sxemasi bo'yicha tekshiriladi;
    - harakat parametrlari tekshiriladi; klapan `duration_s` uchun `max_runtime_s` dan oshib bo'lmaydi;
    - **`risk: high` harakatlar taqiqlangan**: darvoza, qulf, kontaktor, signalizatsiya;
    - **sikllar rad etiladi** (A → B → A va o'ziga ham). O'chirilgan qoidani qayta yoqishda ham tekshiriladi;
    - `sun` uchun uy koordinatalari majburiy.
- **Hub dvigateli** (`gateway/automations.py`, `gateway/sun.py`):
  - Trigger faqat qurilmadan kelgan (`reported`) qiymat **o'zgarganda** ishlaydi.
  - Qiymat noma'lum yoki qurilma oflayn bo'lsa, shart bajarilmagan hisoblanadi.
  - Quyosh vaqti NOAA formulasi bilan internetsiz hisoblanadi; London jadvali bilan ±1 daqiqa farq. Hub o'chiq turgan paytdagi eski quyosh botishi qayta bajarilmaydi.
  - `cooldown`, `max_runs_per_hour` ishlaydi (limit bir marta yoziladi). Qoida tahrirlanganda tarix va limit saqlanadi.
  - **Qo'lda boshqaruv ustun:** odam ilovadan buyruq bersa, avtomatika shu qurilmaga `manual_override_s` davomida tegmaydi. `auto_off` ham, agar odam qurilmani olib qo'ygan bo'lsa, o'chirmaydi.
  - Buyruqlar lokal yuboriladi va bulut buyrug'i kabi ack hamda tasdiq kutadi. Bulutga ack yuborilmaydi, bulutdagi buyruqlar tarixida ko'rinmaydi.
  - Har bir ishga tushish outbox orqali yuboriladi: internet yo'q paytda kutadi, keyin yetkaziladi.
- **PWA:**
  - "Avtomatika" sahifasi: qoidalar ro'yxati, qoidani so'z bilan tushuntirish, yoqish/o'chirish kaliti, oxirgi natija, tarix.
  - **Vizual muharrir:** "Qachon? / Agar / Nima qilsin?". Qiymatlar shartnoma sxemasidan tanlanadi (erkin matn emas). Yuqori xavfli qurilmalar harakatlar ro'yxatida umuman ko'rinmaydi. Backend xatolari to'liq ko'rsatiladi.
  - Sozlamalar → "Uy joylashuvi": koordinatalar, "Hozirgi joylashuvdan olish" tugmasi.
- Hub `requirements.txt` ga `tzdata` qo'shildi: Docker slim image'da vaqt zonalari bazasi yo'q.

Topilgan va tuzatilgan xato: `auto_off` odam qurilmani qo'lga olgandan keyin ham o'chirib qo'yardi. Unit test buni topdi.

CI (oldingi commit 040b030): web E2E, proshivka kompilyatsiyasi (sug'orish, sirena va datchik ham), backend, migratsiyalar va hub 3.10 — hammasi yashil. `hub 3.12` job'i GitHub runner'ida "Install mosquitto" qadamida qotib qoldi. Bu kod xatosi emas; keyingi push'da qayta ishlaydi.

Testlar:
- Contracts: 70 passed.
- Backend: 179 passed. Avtomatika testlari 15 ta: validatsiya, high-risk taqiqi, sikllar, versiya, ruxsatlar, idempotent tarix.
- Hub: 83 passed `[SIM]`. Shundan 13 tasi dvigatel unit testlari, 3 tasi to'liq zanjir (haqiqiy Mosquitto):
  - harakat → chiroq **internetsiz** yoqiladi, tarix keyin yetadi;
  - odam buyrug'i avtomatikadan ustun;
  - o'chirilgan qoida Hub'da to'xtaydi.
- Web: vitest 46 passed. Playwright 12 passed: telefon va iPad'da qoidani muharrirda yaratish, yoqish/o'chirish va o'chirib tashlash.
- PostgreSQL migratsiya testi bu safar lokal ishga tushirilmadi (konteyner qayta yongandan keyin PostgreSQL ishlamayapti); CI'dagi `migrations` job'i uni tekshiradi.

Hal qilinmagan xavflar:
- `notify` hozircha faqat tarixga yoziladi. Telegram/Push — Faza 13; ungacha avtomatika xabari **telefonga kelmaydi**.
- Ishlash vaqtidagi sikl himoyasi faqat `max_runs_per_hour` ga tayanadi (asosiy himoya — saqlashdagi tekshiruv).
- Bitta qurilmada bir nechta capability bo'lsa, harakat va trigger capability darajasida solishtiriladi (masalan, dimmer ↔ switch alohida hisoblanadi).

Tasdiqlanmagan taxminlar:
- Uy koordinatalari kiritilmagan (H-14). Ularsiz quyosh qoidalari saqlanmaydi.

Keyingi faza: 13 — Bildirishnomalar.

## Faza 13 — Bildirishnomalar — 2026-10-08
Holat: tugadi `[SIM]`. Telegram va Push servislari testlarda soxta HTTP transport bilan almashtirilgan. Haqiqiy bot va telefonda **sinalmagan**.

Qilingan ishlar:
- **ADR 0014:** manbalar, qabul qiluvchilar, kanallar, yetkazish, tasdiqlash, eslatma. ARCHITECTURE 7, 8, 12-bo'limlar yangilandi.
- **Backend:**
  - Migratsiya 0008 (expand-only):
    - yangi jadvallar: `notifications`, `notification_deliveries`, `telegram_links`, `telegram_link_codes`, `push_subscriptions`;
    - yangi ustunlar: `home_members.notify_min_severity` (`server_default` `warning`), `hubs`/`devices.offline_notified_at`.
  - **Manbalar:**
    - Hub'dan kelgan har bir yangi voqea (`event:<id>`, takrorlanmaydi);
    - avtomatikaning `notify` harakati (`run:<id>:<n>`) — Faza 12 dagi "telefonga kelmaydi" cheklovi yopildi;
    - nazoratchi cron: Hub 150 s jim bo'lsa → **kritik** (cron har daqiqada ishlaydi, ya'ni 3 daqiqa ichida), Hub qaytsa → xabar;
    - qurilma 5 daqiqa `offline` bo'lsa → ogohlantirish. Hub o'zi aloqasiz bo'lsa, qurilmalar haqida alohida xabar berilmaydi.
  - **Kimga:** egasi, admin va oila a'zolari, har kim o'zi tanlagan darajadan (standart `warning`) yuqori xabarlarni oladi; kritik xabar har doim yuboriladi. Mehmon va kuzatuvchi olmaydi.
  - **Telegram:**
    - webhook `X-Telegram-Bot-Api-Secret-Token` sarlavhasi bilan tekshiriladi, sir noto'g'ri bo'lsa 404 qaytadi;
    - bog'lash 8 belgili bir martalik kod bilan (10 daqiqa, bazada faqat SHA-256), faqat shaxsiy chat orqali; `/stop` bog'lanishni uzadi;
    - xabarda "✅ Ko'rdim" tugmasi bor; bosilganda xabar "Ko'rildi — Ism" ga o'zgaradi;
    - bot bloklansa, bog'lanish o'chiriladi.
  - **Web Push:**
    - RFC 8291 (aes128gcm) va RFC 8292 (VAPID) `cryptography` bilan yozildi. **RFC 8291 test vektori bilan bayt-ma-bayt mos keladi**, testda brauzer kabi qayta shifrdan ochiladi;
    - endpoint faqat haqiqiy push servislariga ruxsat etiladi (SSRF himoyasi);
    - 404/410 javobi kelsa, obuna o'chiriladi;
    - "Ko'rdim" tugmasi bildirishnoma × foydalanuvchi uchun HMAC-token bilan ishlaydi.
  - **Yetkazish:**
    - `warning` va `critical` darhol, Hub so'rovi ichida yuboriladi (≤ 5 s); qolganlari `app.jobs.notify` cron'ida (har daqiqa);
    - qayta urinishlar 1/2/4/8 daqiqada, 5-urinishdan keyin `failed`;
    - `pending → sending` holatiga shartli o'tkazish ikki marta yuborilishga yo'l qo'ymaydi; osilib qolgan yozuv 5 daqiqadan keyin qayta urinadi.
  - **Tasdiqlash:** ilova, Telegram yoki Push orqali; birinchi tasdiqlagan odam yoziladi. Kritik xabar 10 daqiqada tasdiqlanmasa, **bir marta** "🔁 Eslatma" yuboriladi.
  - Sinov xabari endpoint'i har bir kanal bo'yicha haqiqiy natijani qaytaradi. Sozlanmagan kanal uchun `503 NOT_CONFIGURED`. Saqlash muddati: 180 kun.
- **Deploy:**
  - `TELEGRAM_BOT_TOKEN` (mavjud Secret) va `PUBLIC_URL` serverdagi `.env` ga yoziladi;
  - webhook siri va VAPID kaliti **serverning o'zida** yaratiladi va qayta deploy'da almashtirilmaydi; `.env` ruxsati 600;
  - sog'liq tekshiruvidan keyin `app.jobs.telegram_setup` webhook'ni o'rnatadi; bu qadam yiqilsa ham deploy yiqilmaydi;
  - yangi cron qatori: `app.jobs.notify`.
  - **Yangi GitHub Secret kerak emas.**
- **PWA:**
  - Yuqori panelda qo'ng'iroqcha: tasdiqlanmaganlar soni; kritik xabar bo'lsa, qizil pulsatsiya.
  - "Bildirishnomalar" sahifasi: matn voqealar tasmasi va Telegram bilan bir xil, zona nomi qurilma nomi bilan ko'rsatiladi; "Ko'rdim" tugmasi; kim va qachon ko'rgani.
  - Sozlamalar → Bildirishnomalar:
    - Telegram'ni bog'lash: kod, `t.me` havolasi, bog'lanish avtomatik aniqlanadi;
    - shu qurilmada Push'ni yoqish;
    - **iPhone/iPad'da Push faqat o'rnatilgan PWA'da ishlashi ochiq aytiladi**;
    - daraja tanlash, sinov tugmasi.
  - Service worker'da push qabul qilish va "Ko'rdim" amali (`push-sw.js`).

Testlar:
- Backend: 208 passed (SQLite). Bildirishnoma, migratsiya, voqea va avtomatika testlari **PostgreSQL 16 da ham** o'tdi: 97 passed.
  - 29 ta yangi test: RFC vektori, VAPID imzosi, bog'lash, webhook siri, kritik xabar darhol yetishi va tugma bilan tasdiqlanishi, boshqa uy yoki bog'lanmagan chat tasdiqlay olmasligi, daraja filtri, kuzatuvchi rolida xabar kelmasligi, backoff va `failed`, bloklangan bot, ikki marta yuborilmaslik, push shifrini ochish va token bilan tasdiqlash, 410, SSRF, Hub o'chishi va qaytishi, qurilma oflayn bo'lishi, eslatma (tasdiqlangan bo'lsa yuborilmaydi), avtomatika xabari, saqlash muddati, production konfiguratsiya tekshiruvi.
- Deploy skripti: 6 passed (haqiqiy PostgreSQL). Sirlar `.env` da yaratiladi, logga chiqmaydi va qayta deploy'da o'zgarmaydi.
- Web: vitest 51 passed. Playwright 16 passed: telefon va iPad'da qo'ng'iroqcha → sahifa → "Ko'rdim" → sozlamalar ("serverda sozlanmagan" ochiq aytiladi). Sahifa gorizontal siljimaydi.
- Hub kodi o'zgarmadi (faqat izoh); hub testlarini CI ishga tushiradi.

Hal qilinmagan xavflar:
- Uyda internet o'chsa, voqea xabari internet qaytgandan keyin keladi. Matnda voqeaning asl vaqti ko'rsatiladi.
- Telegram yoki push servisi uzoq vaqt ishlamasa, 5 urinishdan keyin `failed` bo'ladi; ilovadagi ro'yxat baribir to'liq qoladi.
- Hub qaytgandan keyin qurilmalar holatini qayta yuborguncha eski `offline` holati bitta ortiqcha xabar berishi mumkin.

Tasdiqlanishi kerak `[REAL]`:
- Haqiqiy bot: deploy'dan keyin webhook o'rnatilganini, bog'lashni, kritik xabarni va "Ko'rdim" tugmasini tekshirish.
- iPhone'da o'rnatilgan PWA'ga Push (iOS 16.4+), Android Chrome'ga Push.
- Hub tokini uzib, 3 daqiqa ichida Telegram'ga "Hub aloqasiz" xabari kelishini tekshirish.

Keyingi faza: 14 — Mustahkamlash.

## Faza 14 — Mustahkamlash — 2026-10-08
Holat: tugadi. Skanlar va tiklash mashqi haqiqatan bajarildi: lokal, haqiqiy PostgreSQL 16 da va CI'da. Tashqi port skani va production serverdagi tiklash mashqi `[REAL]` — uy va server tayyor bo'lganda bajariladi (`docs/runbooks/security-audit.md` 3-bo'lim, `backup-restore.md`).

**Xavfsizlik tekshiruvi** (`docs/runbooks/security-audit.md`):
- `pip-audit` (backend + hub, tranzitiv paketlar bilan): **zaiflik yo'q**. `npm audit`: **0**. `gitleaks` (22 commit + ishchi papka): **haqiqiy sir yo'q**. 2 ta soxta topilma `.gitleaksignore` ga sababi bilan yozildi.
- Yangi CI job'i `security`: pip-audit, `npm audit --audit-level=high`, gitleaks. Gitleaks binari sha256 bilan tekshiriladi. Yiqilsa, deploy bo'lmaydi.

**Topilgan va tuzatilgan muammolar:**
1. **Port ochiqligi (jiddiy):**
   - Muammo: `docker-compose.yml` dagi `"1883:1883"`, `8971`, `8555` portlari barcha manzillarda (IPv6 ham) ochilardi, Docker esa ufw'ni chetlab o'tadi.
   - Tuzatish: endi har bir port `HUB_LAN_IP` / `HUB_TAILNET_IP` ga bog'langan; `HUB_LAN_IP` siz stack ishga tushmaydi.
   - Tekshiruv: `tests/test_exposure.py` testi (eski konfiguratsiyada yiqilishi ko'rildi) va `docker compose config` (7/7 portda `host_ip` bor).
2. **`backup.sh` yolg'on "backup ok":**
   - Muammo: POSIX `sh` da `pg_dump | gzip` ishlatilardi va `pipefail` yo'q. Yarim dump "ok" deb hisoblanardi.
   - Tuzatish: endi `pg_dump` chiqish kodi va "dump complete" oxirgi qatori tekshiriladi.
   - Tekshiruv: regressiya testi bor.
3. **Hub sog'lig'i yo'qolardi:**
   - Muammo: Hub heartbeat'da broker va disk holatini yuborardi, bulut esa uni tashlab yuborardi.
   - Tuzatish (migratsiya 0009, expand-only):
     - `hubs.health` (faqat ma'lum kalitlar va turlar) va `hubs.health_alerts` saqlanadi;
     - watchdog **broker ishlamasa** va **disk to'lsa** (Hub tizim diski ≥ 90%, kamera HDD'si ≥ 85%) ⚠️ bildirishnoma beradi, tiklanganda xabar beradi;
     - 2 daqiqalik kutish bor (broker qisqa qayta yuklansa, xabar yuborilmaydi);
     - **noma'lum holat** na alert yaratadi, na "tiklandi" deydi (test shu xatoni topdi va tuzatildi).
   - Hub sahifasida broker, disklar va outbox ko'rinadi. Hub o'z tizim diskini o'lchaydi (`data_disk_pct`).
4. **Docker log'lari cheklanmagan edi:** endi har servisga 3 × 10 MB.
5. **Yo'qolgan telefon:** "Barcha qurilmalardan chiqish" endi Push obunalarini ham o'chiradi.
6. **Runbook'dagi xato maslahat:** `gunzip | psql` usuli mavjud bazada ishlamaydi. U `restore.sh` bilan almashtirildi.
7. **Rate limit chegarasi (CI'dagi tasodifiy yiqilish orqali topildi):**
   - Muammo: cheklov soatga bog'langan qat'iy 5 daqiqalik oynada sanardi. Oyna chegarasida (masalan, 12:04:59 va 12:05:00) 20 + 20 = **40 ta** noto'g'ri parol bir necha soniyada qabul qilinardi. `test_ip_rate_limit` testi ham shu sababli ba'zan yiqilardi.
   - Tuzatish: endi sirpanuvchi oyna bahosi ishlatiladi: oldingi oyna hisobi qolgan ulushiga ko'paytiriladi va joriy oyna hisobiga qo'shiladi. Login, PIN, buyruqlar va realtime cheklovlarining hammasiga tegishli.
   - Tekshiruv: yangi testlar aniq vaqt bilan; eski kodda 4 tadan 3 tasi yiqildi.

**Zaxiradan tiklash — haqiqatan bajarildi** (`infra/cpanel/restore.sh`, `docs/runbooks/backup-restore.md`):
- `restore.sh` qadamlari:
  1. dump tekshiriladi;
  2. hozirgi baza xavfsizlik dumpiga saqlanadi;
  3. o'chirish va yuklash **bitta tranzaksiyada** bajariladi (xato bo'lsa, baza o'zgarmaydi);
  4. `alembic upgrade head`;
  5. ilova qayta ishga tushiriladi.
- Mashq haqiqiy PostgreSQL'da, deploy qilingan ilova bilan bajarildi:
  - "falokat": ma'lumot va jadval o'chirildi;
  - kesilgan dump rad etildi, o'rtasida xato bor dump orqaga qaytarildi;
  - tiklashdan keyin ma'lumot, jadval va alembic versiyasi joyida, ilova sog';
  - xavfsizlik dumpi bilan orqaga qaytarish ishladi.
- `restore.sh` relizga qo'shildi.

**Runbook'lar** (`docs/runbooks/`): `hub-down`, `broker-down`, `disk-full`, `token-stolen` (telefon, Hub, bulut sirlari, deploy kaliti — har biri qanday bekor qilinadi va almashtiriladi), `power-outage`, `backup-restore`, `security-audit`. Hammasi iPad'dan bajariladi. Tugma nomlari ilovadagi haqiqiy matnlar bilan solishtirildi. Runbook uchun gateway'ga `local mqtt connected` log qatori qo'shildi.

Testlar:
- Backend: 212 passed (SQLite). Notifications, migrations va hub testlari PostgreSQL 16 da ham o'tdi (85).
- Hub: 88 passed `[SIM]`, shu jumladan 5 ta yangi exposure testi.
- Deploy va tiklash skriptlari: 9 passed (haqiqiy PostgreSQL).
- Web: vitest 52 passed.

Hal qilinmagan xavflar:
- **Audit log uchun ilovada sahifa yo'q**: ma'lumot faqat API orqali olinadi. Kelajakdagi ish sifatida qayd etildi.
- Imzo kalitini almashtirish uchun bitta `SIGNING_MASTER_KEY` almashtiriladi. Bitta uy uchun bu yetarli; bir nechta uy bo'lsa, har uy uchun alohida rotatsiya kerak bo'ladi.
- Yangi CVE chiqsa, `security` job'i deploy'ni to'xtatadi. Bu ataylab qilingan: runbook'da nima qilish kerakligi yozilgan.

`[REAL]` qoldi:
- tashqi port skani (mobil internetdan, IPv4 va IPv6);
- production serverda bir marta tiklash mashqi;
- UPS va elektr uzilishi sinovi.

Keyingi faza: 15 — Uyni ishga tushirish (apparat kerak).

## Qo'shimcha: Elektr shiti — masofadan boshqariladigan avtomatlar (ADR 0015) — 2026-10-08
Egasining so'rovi bo'yicha. Holat: tugadi `[SIM]`. Haqiqiy avtomatlarda **sinalmagan**: modeli inventarda hali ochiq, sinov jadvali `docs/hardware/tests/breaker.md` da.

Qilingan ishlar:
- **Shartnoma:** yangi `breaker` capability.
  - `closed` — avtomatning o'z kontaktidan keladi va faqat shu buyruqni tasdiqlaydi.
  - `tripped` — himoya ishlagan.
  - Sozlamalari: shit nomi, yorliqdagi raqami, nominali (`C16`), qutblar soni.
  - Xavf darajasi `high`: har bir yoqish va o'chirish PIN bilan bo'ladi, faqat egasi va admin bajaradi, avtomatika bu harakatni qila olmaydi.
  - Voqealar: `breaker.tripped` (critical, Telegram/Push'ga keladi) va `breaker.close_refused`.
- **Proshivka** `devices/esphome/circuit-breaker.yaml`: motor operatori, OF (holat) va SD (himoya) kontaktlari.
  - Himoya ishlagan avtomat masofadan **yoqilmaydi** (`safety_rule`).
  - Himoya holati noma'lum bo'lsa ham yoqilmaydi.
  - Konfiguratsiya lokal `esphome config` bilan tekshirildi, kompilyatsiyani CI qiladi.
- **Hub:** tasdiq faqat `closed` orqali. Simulyatorda `BreakerSim` bor: himoya ishlashi, joyida tiklash, OF kontakt nosozligi.
- **Ilova:**
  - Elektr bo'limida haqiqiy shitga o'xshash ko'rinish. Avtomatlar yorliqdagi raqam bo'yicha chapdan o'ngga teriladi, 2P avtomat ikki modul egallaydi.
  - Har bir modulda raqam, `C16`, richag, qizil/yashil indikator, nom va holat bor.
  - Noma'lum holatda richag **o'rtada** turadi va bosib bo'lmaydi.
  - Himoya ishlaganda modul qizil "TRIP" holatida bo'ladi va yoqib bo'lmaydi.
  - Takrorlangan raqam belgilanadi.
  - Oxirgi "+" bo'sh joy keyingi bo'sh raqam bilan avtomat qo'shadi.
  - Avtomat qo'shish formasi: liniya nomi (masalan, "Oshxona"), shit, raqam, qutb, xarakteristika, nominal tok va "quvvatni ham o'lchaydi" belgisi.
  - Bosh sahifada avtomatlar alohida kartochka bo'lib chiqmaydi, ularning o'rniga shit xulosasi ko'rsatiladi. Himoya ishlasa, banner qizil bo'ladi va avtomat nomini aytadi.
  - Qurilma tarixida va PIN oynasida avtomat uchun "Yoqish/O'chirish" yoziladi ("Yopish/Ochish" emas).

Testlar:
- Contracts: 70 passed.
- Backend: 225 passed. Shu jumladan avtomat konfiguratsiyasi tekshiruvi (7 ta noto'g'ri holat rad etildi) va voqea darajalari.
- Hub: 90 passed `[SIM]`. To'liq zanjir:
  - PIN'siz buyruq rad etiladi;
  - o'chirish va yoqish tasdiqlanadi;
  - himoya ishlaydi → voqea → masofadan yoqish rad etiladi → joyida tiklangach yoqiladi;
  - OF kontakt uzilsa, "bajarildi" deb ko'rsatilmaydi.
- Web: vitest 58 passed. Playwright 18 passed: telefon va iPad'da 12 ta avtomatli shit, PIN bilan o'chirish va yoqish (tasdiqlandi), himoya ishlagan nasos bloklangan.
- gitleaks: toza.

## Qo'shimcha (egasining so'rovi, 2026-10-09): yangi dizayn, Tuya, IR pult, Alisa — ADR 0016

Holat: kod tayyor, **[SIM]** testlardan o'tgan. Haqiqiy qurilmalar bilan sinov **[REAL]** hali qilinmagan (`docs/hardware/tests/tuya.md`).

- **Dizayn.** Qurilmalar endi ixcham plitkalarda: dumaloq belgi qurilmani yoqib-o'chiradi, plitkaning o'zi qurilma sahifasini ochadi. Ranglar yangilandi, ko'rsatkichlar suriladigan qatorga o'tdi, pastki menyu "suzib" turadi. Holat qoidalari o'zgarmadi.
- **Tuya / Smart Life** (Hub, uy tarmog'i, bulutsiz):
  - Wi-Fi rele, quvvat o'lchaydigan rozetka, Wi-Fi avtomat (TO-Q-SY2-JWT kabi), chiroq va IR pult qo'llab-quvvatlanadi.
  - Local Key bulutda shifrlangan holda saqlanadi, ilovada hech qachon ko'rsatilmaydi va faqat Hub'ga beriladi.
  - Tasdiq faqat qurilmaning o'z javobidan keladi. Himoya ishlagan avtomat masofadan yoqilmaydi.
- **IR pult** (oddiy televizor va konditsioner):
  - Tugmalar asl pultdan o'rgatiladi va kod haqiqatan olingandagina tasdiqlanadi.
  - Tugmani bosish faqat "yuborildi" bo'ladi, chunki IR'da qaytar aloqa yo'q.
- **Yandex Alisa** (bulut orqali):
  - Token bir marta kiritiladi va shifrlangan holda saqlanadi.
  - Alisa chiroqlari, rozetkalari, televizorlari va konditsionerlari qurilma sifatida paydo bo'ladi.
  - Holat har daqiqada yangilanadi. Buyruq Yandex holatini qayta o'qib tasdiqlanadi.
  - Alisa ssenariylarini ilovadan ishga tushirish mumkin.
- Migratsiyalar: `0010` (qurilma ulanishi va shifrlangan kalit), `0011` (integratsiyalar). Ikkalasi ham expand-only.
- Yo'riqnomalar: `TUYA.md` va `ALISA.md` zip ichida (Local Key va token olish telefondan qilinadi).

Testlar:
- Contracts: 70 passed.
- Backend: 247 passed. Shu jumladan Tuya kalitining shifrlanishi va qaytarilmasligi hamda soxta Yandex API bilan sinxronlash, tasdiqlash va xatolar.
- Hub: 99 passed `[SIM]` (9 tasi Tuya ko'prigi uchun):
  - e'tiborsiz qoldirilgan buyruq tasdiqlanmaydi;
  - avtomat himoyasi;
  - IR o'rgatish.
- Web: vitest 61 passed. Playwright 28 passed (telefon + iPad):
  - Tuya rele;
  - Hovli shitidagi Wi-Fi avtomat;
  - TV pultini o'rgatish va bosish;
  - Tuya qurilma qo'shish (kalit ko'rinmaydi);
  - Alisa'ni ulash, chiroq (tasdiqlandi), TV ovozi.
- gitleaks: toza.

Hali yo'q (keyingi bosqich):
- bizning qurilmalarni Alisa'ga **ovozli** boshqaruv uchun berish (Yandex "aqlli uy" ko'nikmasi);
- LG va Samsung televizorlarining o'z protokollari.
