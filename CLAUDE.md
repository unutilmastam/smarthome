# CLAUDE.md — AI agent uchun ish qoidalari

Loyiha: **SmartHome Control Center** — real uy uchun boshqaruv tizimi (o'yinchoq emas).

## Avval o'qi
1. `ARCHITECTURE.md` — tizim qanday tuzilgan (manba haqiqati).
2. `docs/PHASES.md` — bosqichlar tartibi va har birining tugash mezoni.
3. `docs/PROGRESS.md` — qaysi faza tugagan (bo'lmasa, Faza 0 dan boshla).
4. `docs/spec/capabilities.json` (Faza 1 dan keyin `packages/contracts/`) — qurilma imkoniyatlari.

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
