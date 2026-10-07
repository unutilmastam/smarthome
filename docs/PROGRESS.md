# Progress

Har bir faza tugagach shu yerga hisobot qo'shiladi (shablon: `docs/PHASES.md`).
Belgilar: `[SIM]` — simulyatsiyada, `[REAL]` — haqiqiy apparatda sinalgan.

| Faza | Nomi | Holat |
|---|---|---|
| 0 | Tayyorgarlik (hujjatlar) | tugadi |
| 1 | Poydevor (monorepo, contracts, CI) | tugadi (CI natijasi pastda) |
| 2 | Backend asosi | boshlanmagan |

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
- GitHub Actions natijasi: push'dan keyin tekshiriladi (pastda).

Hal qilinmagan xavflar:
- PostgreSQL service CI'da ko'tariladi, lekin Faza 1 da DB'dan foydalanilmaydi (Faza 2 dan).
- cPanel'ga deploy paytida `packages/contracts` ilova yoniga (`contracts/`) nusxalanishi kerak — `CONTRACTS_DIR` bunga tayyor (Faza 7).
- Starlette testclient `httpx` uchun deprecation ogohlantirishi beradi (funksional ta'siri yo'q).

Tasdiqlanmagan taxminlar:
- Hosting Python versiyasi ≥ 3.10 (H-01b).

Keyingi faza: 2 — Backend asosi (auth, uy, xona, qurilma reyestri).
