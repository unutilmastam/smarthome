# Zaxira va tiklash

## Nima, qayerda zaxiralanadi
| Ma'lumot | Zaxira | Qayerda | Muddat |
|---|---|---|---|
| Bulut bazasi (PostgreSQL): foydalanuvchilar, qurilmalar, tarix, avtomatika, bildirishnomalar | `backup.sh`, har kuni 03:41 | `~/sh-deploy/daily` | 14 kun |
| Shu baza, har deploy oldidan | `deploy.sh` | `~/sh-deploy/backups/pre-deploy-*` | oxirgi 10 ta |
| Tiklashdan oldingi holat | `restore.sh` | `~/sh-deploy/backups/pre-restore-*` | qo'lda o'chiriladi |
| Server sirlari (`.env`) | **zaxiralanmaydi** (ataylab) | faqat serverda | — |
| Hub `.env` (HUB_TOKEN, SIGNING_KEY_HEX, parollar) | egasining parol menejerida (qo'lda) | — | — |
| Hub SQLite (outbox, bajarilgan buyruqlar) | kerak emas: yo'qolsa, Hub bulutdan qayta sinxronlanadi | — | — |
| Kamera yozuvlari | **hech qachon bulutga chiqmaydi** (ADR 0006) | Hub HDD | Frigate sozlamasi |

Barcha dump fayllarining ruxsati `600`, ular `public_html` dan tashqarida turadi.

**Tuzatilgan xato (Faza 14):** `backup.sh` POSIX `sh` da `pg_dump | gzip` qilardi. `pipefail` yo'qligi sababli, `pg_dump` yarim yo'lda yiqilsa ham skript "backup ok" deb yozardi. Endi dump faylga yoziladi va avval `pg_dump` chiqish kodi, keyin "dump complete" oxirgi qatori tekshiriladi. Shundan keyingina siqiladi.

## Tiklash (cPanel → Terminal, iPad'dan)
```
cd ~/smarthome-api
bash restore.sh                                   # mavjud dumplar ro'yxati
bash restore.sh ~/sh-deploy/daily/smarthome-…sql.gz        # faqat tekshiruv: dump butunmi?
bash restore.sh ~/sh-deploy/daily/smarthome-…sql.gz --yes  # tiklash
```
`--yes` bilan nima bo'ladi:
1. Dump tekshiriladi: gzip butun va "dump complete" bor. Aks holda **hech narsa o'zgarmaydi**.
2. Hozirgi baza `pre-restore-*.sql.gz` ga saqlanadi.
3. Eski jadvallarni o'chirish va dumpni yuklash **bitta tranzaksiyada** bajariladi. Xato bo'lsa, baza avvalgi holicha qoladi.
4. `alembic upgrade head`: eski dump joriy kod sxemasiga ko'tariladi (migratsiyalar expand-only).
5. Ilova qayta ishga tushiriladi.

Natija yoqmasa, oldingi holatga qaytarish: `bash restore.sh ~/sh-deploy/backups/pre-restore-….sql.gz --yes`.

Deploy yiqilganda tiklash **avtomatik** bo'ladi (`deploy.sh`). Bu runbook — qo'lda tiklash uchun: ma'lumot xato o'chirilganda, buzilganda yoki 🆘 holatda.

## Mashq — haqiqatan bajarildi
`infra/cpanel/tests/test_restore.py`. Haqiqiy PostgreSQL 16 da, deploy qilingan ilova, alembic va health check bilan bajarildi. Har push'da CI'da qaytariladi.

| Qadam | Natija |
|---|---|
| Ma'lumot yozildi → `backup.sh` | ✅ dump yaratildi, ruxsati `600` |
| "Falokat": ma'lumot o'chirildi, `audit_log` jadvali o'chirildi, noto'g'ri yozuv qo'shildi | — |
| Dump tekshiruvi (`--yes` siz) | ✅ hech narsa o'zgarmadi |
| Yarmi kesilgan dump | ✅ rad etildi, baza o'zgarmadi |
| O'rtasida xato bor dump | ✅ yuklash orqaga qaytarildi, jadvallar o'chirilmadi |
| Tiklash `--yes` | ✅ ma'lumot va `audit_log` qaytdi, alembic versiyasi joyida, ilova sog' (health ok) |
| `pre-restore` dumpi bilan qaytarish | ✅ falokatdan oldingi holat qaytdi |
| Ishlamayotgan baza bilan `backup.sh` | ✅ "backup ok" **yozilmadi**, fayl qolmadi |

`[REAL]` qoldi: production serverda bir marta mashq qilish. Ma'lumot kam paytda, kunlik dump bilan quyidagi ketma-ketlik bajariladi:
1. dumpni tekshirish (`--yes` siz);
2. `--yes` bilan tiklash;
3. ilovada ma'lumotlar joyida ekanini ko'rish.

Natijani shu jadvalga sana bilan qo'shing.

## Hub'ni noldan tiklash (disk buzildi, Hub almashtirildi)
1. `infra/hub/install.md` bo'yicha yangi Hub o'rnatiladi.
2. `.env` parol menejeridan tiklanadi. Agar eski Hub o'g'irlangan bo'lsa — [token-stolen.md](token-stolen.md): yangi token va kalit oling.
3. `sh mosquitto/make-passwd.sh <qurilma kalitlari>`: ESP32 lar o'z `secrets.yaml` dagi parollari bilan ulanadi.
4. `docker compose up -d`. Qurilmalar, avtomatika va signalizatsiya sozlamalari `GET /hub/config` orqali bulutdan qaytadi.
5. Signalizatsiya **qo'riqlanmagan** holatda boshlanadi (yangi diskda saqlangan holat yo'q). Kerak bo'lsa, ilovadan qayta yoqing.
