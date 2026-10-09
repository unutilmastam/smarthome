# 0002 — Cloud DB — PostgreSQL (cPanel)

- Holat: qabul qilingan
- Sana: 2026-10-07

## Kontekst
- cPanel'da "PostgreSQL Databases" va MySQL mavjud. Alohida DB serveri yo'q.
- Kerak: tranzaksiyalar, buyruqni **atomik** bir marta berish (`queued → sent`), JSON maydonlar (`value_json`, `config_json`, avtomatika ta'rifi), vaqt bo'yicha indekslar (`(device_id, ts)`).
- Testlar CI'da tez ishlashi kerak.

## Qaror
- Asosiy DB: **PostgreSQL** (cPanel). ORM: **SQLAlchemy 2**, migratsiya: **Alembic**.
- Barcha vaqt UTC, `timestamptz`; ORM'da naive datetime taqiqlanadi.
- Buyruqni claim qilish: `SELECT ... FOR UPDATE SKIP LOCKED` (Postgres) — bitta buyruq bir marta beriladi.
- JSON: `JSONB` (Postgres), SQLAlchemy `JSON` turi orqali (SQLite'da testlar uchun ishlaydi).
- Testlar: tezkor unit testlar SQLite'da, integratsion testlar CI'dagi PostgreSQL service'da. `ENV=production` da SQLite bilan ishga tushish xato (Faza 1).
- Xom telemetriya cloud'ga kelmaydi (Hub'da 7 kun); cloud'da faqat `telemetry_1m` (30 kun), `telemetry_1h` (2 yil), `energy_daily`.

## Ko'rib chiqilgan muqobillar
- **MySQL/MariaDB** — mavjud, lekin `SKIP LOCKED` va JSON imkoniyatlari versiyaga bog'liq. **Zaxira variant** sifatida qoladi: hosting PostgreSQL versiyasi juda eski bo'lsa (< 12) — yangi ADR bilan MySQL'ga o'tiladi; SQLAlchemy tufayli kod deyarli o'zgarmaydi.
- **SQLite (cloud'da)** — shared hostingda bir nechta Passenger jarayoni bilan qulflash muammolari; production uchun rad etildi.
- **Tashqi managed DB (Supabase, Neon)** — tarmoq kechikishi, qo'shimcha hisob va sir; hozircha kerak emas.

## Oqibatlar
### Ijobiy
- Atomik navbat, kuchli tranzaksiyalar, JSONB indekslari.
### Salbiy / xavflar
- Shared hostingda DB hajmi va ulanishlar soni cheklangan — retention cron majburiy, ulanish pool kichik (`pool_size` 2–5).
- Versiyaga xos imkoniyatlar (masalan, `MERGE`, generated columns) ishlatilmaydi.
- Zaxira: cPanel avtomatik backup + kunlik `pg_dump` cron (Faza 7); tiklash Faza 14 da haqiqatan sinaladi.

## Tasdiqlanishi kerak
- Hostingdagi PostgreSQL versiyasi (≥ 12 kutilmoqda) — H-01.
- Ruxsat etilgan DB hajmi va maksimal ulanishlar soni.
- `pg_dump` cPanel Terminal/cron'dan ishlaydimi.
