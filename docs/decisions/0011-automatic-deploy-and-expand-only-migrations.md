# 0011 — Avtomatik deploy, avtomatik qaytish va "expand-only" migratsiyalar

- Holat: qabul qilingan
- Sana: 2026-10-07
- Faza 7 dagi deploy'ni almashtiradi (`DEPLOY_ENABLED` endi kerak emas).

## Kontekst
Egasi qaror qildi: deploy va migratsiya uchun undan ruxsat so'ralmaydi. `main` ga har bir merge avtomatik ravishda production'ga chiqishi kerak. Lekin xato bo'lsa uy boshqaruvsiz qolmasligi, ya'ni avvalgi ishlaydigan versiyaga avtomatik qaytish shart.

## Qaror
1. **CI darvozasi** (`deploy-cloud.yml` → `test.yml`):
   - barcha testlar (backend SQLite + PostgreSQL, hub, web + E2E, firmware);
   - "expand-only" tekshiruvi;
   - toza PostgreSQL'da `alembic upgrade head`;
   - `deploy.sh` stsenariylari.
   
   Biror narsa yiqilsa deploy **bo'lmaydi** va Telegram'ga xabar ketadi.
2. **Serverda** (`infra/cpanel/deploy.sh`, SSH orqali):
   1. qulf (bir vaqtda faqat bitta deploy);
   2. migratsiyadan **oldin** `pg_dump` → `~/sh-deploy/backups`, oxirgi **10 tasi** saqlanadi; zaxira bo'lmasa hech narsa o'zgarmaydi;
   3. ishlab turgan kodning nusxasi → `~/sh-deploy/previous`;
   4. yangi kod → `alembic upgrade head` → Passenger restart;
   5. `/api/v1/health` tekshiruvi: javobda **aynan shu commit** (`build`) bo'lishi kerak, shunda eski jarayon "muvaffaqiyat" deb hisoblanmaydi;
   6. "videosiz bulut" tekshiruvi (ADR 0006);
   7. cron vazifalari avtomatik o'rnatiladi.
3. **Avtomatik qaytish**: 4–6-qadamlardan biri yiqilsa avvalgi kod tiklanadi, DB pre-deploy zaxiradan tiklanadi (yangi migratsiya yaratgan jadvallar ham o'chiriladi), restart qilinadi va avvalgi build'ning health'i tekshiriladi. Natija Telegram'ga yuboriladi.
   - Chiqish kodlari: `0` deploy qilindi, `10` qaytarildi, `11` boshlanmadi, `12` qaytarish ham yiqildi.
4. **Birinchi deploy**: `.env` serverda yaratiladi. JWT va signing kalitlari **serverning o'zida** generatsiya qilinadi va GitHub'ga hech qachon chiqmaydi. GitHub'dan faqat `DATABASE_URL` keladi.
5. **Expand-only migratsiyalar** (`scripts/check_migrations.py`, CI'da majburiy):
   - oddiy migratsiya faqat **qo'shadi**: jadval, nullable ustun (yoki `server_default` bilan NOT NULL), indeks;
   - o'chirish, nomini o'zgartirish, NOT NULL qilish, turini o'zgartirish, constraint/indeks o'chirish va xom `DROP/ALTER` SQL faqat alohida **contract** migratsiyada (`CONTRACT = True`) bo'ladi. U kod o'sha ustun/jadvaldan foydalanishni to'xtatgan relizdan **keyingi** relizda chiqariladi va ichida qo'shish amallari bo'lmaydi.
   - Natijada avvalgi kod yangi sxema bilan ham ishlaydi, qaytish xavfsiz bo'ladi.

## Oqibatlar
- Egasi faqat bir marta GitHub Secrets'ni kiritadi (`docs/runbooks/deploy.md`); keyin hammasi avtomatik.
- Qaytishda DB zaxiradan tiklanadi, shuning uchun zaxira va qaytish orasida yozilgan ma'lumotlar yo'qoladi (odatda 1–2 daqiqa). Expand-only qoidasi tufayli bu ko'pincha kerak ham emas, lekin xavfsizlik uchun egasi so'raganidek bajariladi.
- cPanel'da "Setup Python App"ni yaratish bir martalik qo'lda qadam bo'lib qoladi: ilova ildizi va virtualenv yo'lini hosting panelining o'zi beradi.
