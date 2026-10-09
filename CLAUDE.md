# CLAUDE.md — AI agent uchun ish qoidalari

Loyiha: **SmartHome Control Center** — real uy uchun boshqaruv tizimi (o'yinchoq emas).

## Avval o'qi
1. `ARCHITECTURE.md` — tizim qanday tuzilgan (manba haqiqati).
2. `docs/PHASES.md` — bosqichlar tartibi va har birining tugash mezoni.
3. `docs/PROGRESS.md` — qaysi faza tugagan (bo'lmasa, Faza 0 dan boshla).
4. `packages/contracts/` — qurilma imkoniyatlari (`capabilities.json`) va JSON Schema shartnomalar (yagona manba).

## Ish tartibi
- So'ralgan **bitta fazani** bajar. Tugagach hisobot yoz (`docs/PHASES.md` dagi shablon) va to'xta.
- Faza ichida kichik qadamlar bilan ishla, har qadamdan keyin testlarni ishga tushir.
- Hujjat va kod zid kelsa: avval hujjatni yangila (ADR bilan), keyin kod.

## Qat'iy qoidalar
1. **Qiymat o'ylab topma.** Ma'lumot yo'q → `unknown`, o'lchanmaydi → `not_supported`, eski → `stale`, offline → `offline`.
2. **Tasdiqlangan va so'ralgan holatni aralashtirma.** `confirmed` faqat qurilmadan haqiqiy qaytar aloqa bilan.
3. **Video cloud'ga hech qachon yozilmaydi** (DB, fayl, zaxira — hech qayerga).
4. **Sir kodga yozilmaydi.** Faqat `.env`; repo'da `.env.example`.
5. **Imzosiz yoki muddati o'tgan buyruq bajarilmaydi.**
6. **Xavfsizlik chegaralari proshivkada** (nasos `max_runtime`, `fail_safe_state`). Dastur — qo'shimcha himoya, yagona emas.
7. **Port ochilmaydi.** Hub faqat tashqariga ulanadi; masofaviy kirish — Tailscale.
8. Simulyatsiyada o'tgan testni "real apparatda ishladi" deb yozma: `[SIM]` / `[REAL]`.
9. Mock yoki bo'sh ekranni "tayyor" deb belgilama.
10. Mavjud ishni sababsiz o'chirma.

## Avtomatik rejim (egasining qarori, ADR 0011)
- **Deploy va migratsiya uchun egasidan ruxsat so'ralmaydi.** `main` ga har bir merge `deploy-cloud.yml` orqali avtomatik production'ga chiqadi.
- Deploy tartibi (o'zgartirilmaydi):
  1. CI: barcha testlar, expand-only tekshiruvi, toza PostgreSQL'da `alembic upgrade head`. Yiqilsa — deploy **yo'q**, Telegram'ga xabar.
  2. Serverda migratsiyadan **oldin** `pg_dump` zaxira (oxirgi 10 tasi saqlanadi).
  3. Kod yuklash → `alembic upgrade head` → Passenger restart.
  4. `/api/v1/health` tekshiruvi (aynan yangi `build`). Javob bermasa — **avtomatik qaytish** (kod + DB zaxiradan) va Telegram'ga xabar.
- **Migratsiyalar faqat "expand" usulida** yoziladi: faqat qo'shish (jadval, nullable ustun yoki `server_default` bilan ustun, indeks). Ustun yoki jadval o'chirish, nomini o'zgartirish, NOT NULL qilish — **alohida "contract" migratsiyada** (`CONTRACT = True`), kod u narsadan foydalanishni to'xtatgan relizdan **keyingi** relizda. `scripts/check_migrations.py` buni CI'da majburlaydi.
- Agent to'xtashi mumkin bo'lgan **yagona** holat: GitHub Secrets kerak bo'lganda — ro'yxatni egasiga **bir marta** beradi (`docs/runbooks/deploy.md`). Secrets qo'yilgach, deploy va migratsiyani o'zi bajaraveradi.
- Deploy yiqilsa ham "tayyor" deb yozilmaydi: natija (`deployed` / `rolled_back` / `rollback_failed`) hisobotga haqiqiy holicha yoziladi.

## Muhit cheklovlari
- Cloud: **hostmaster.uz cPanel shared hosting** — Docker yo'q, doimiy fon jarayon yo'q, WebSocket server yo'q. Bor: Setup Python App (Passenger), PostgreSQL, SSH, Terminal, Cron, Git Version Control.
- FastAPI → `passenger_wsgi.py` orqali (a2wsgi). Fon ishlar → cron.
- Python **3.10** bilan mos kod (hosting versiyasi tasdiqlanguncha).
- Egasi kompyutersiz ishlaydi (telefon/iPad). Build va deploy — faqat GitHub Actions orqali. Qo'lda bajariladigan qadamlar iPad'dan bajarsa bo'ladigan qilib yoziladi.

## Til
- Kod, identifikator, commit: ingliz tili.
- UI matnlari: o'zbek (lotin), i18n kalitlari orqali; ru/en keyin.
- Hujjat, hisobot, ADR: o'zbek tili.

## Buyruqlar (fazalar bilan to'ldiriladi)
- Backend testlari: `cd services/backend && pytest`
- Migratsiya: `cd services/backend && alembic upgrade head`
- Expand-only tekshiruvi: `cd services/backend && python scripts/check_migrations.py`
- Deploy skripti testlari: `TEST_POSTGRES_ADMIN_URL=postgresql://... pytest infra/cpanel/tests`
- Hub testlari: `cd services/hub && pytest` (lokal `mosquitto` kerak)
- Web: `cd apps/web && npx tsc -b && npx vitest run && npx playwright test`
