# Runbook: hostmaster.uz cPanel'ga avtomatik deploy (iPad'dan)

Deploy **to'liq avtomatik** (ADR 0011). `main` ga har bir merge'dan keyin:
testlar → zaxira → yangi kod → migratsiya → restart → tekshiruv → (xato bo'lsa) avtomatik qaytish → Telegram.
Quyidagi narsalar **faqat bir marta** qilinadi.

## A. cPanel'da bir martalik sozlash (brauzerda, ~10 daqiqa)
1. **2FA**: Security → Two-Factor Authentication.
2. **Subdomen**: Domains → Create A New Domain → `home.example.uz`. Keyin SSL/TLS Status → **Run AutoSSL**.
3. **PostgreSQL**: PostgreSQL Databases → baza `USER_smarthome` va foydalanuvchi `USER_shapp` yarating (uzun tasodifiy parol bilan), foydalanuvchini bazaga qo'shing (ALL PRIVILEGES).
4. **Python ilova**: Setup Python App → Create Application:
   - Python: eng yuqori versiya (≥ 3.10);
   - Application root: `smarthome-api`;
   - Application URL: `home.example.uz` / `api`;
   - Startup file: `passenger_wsgi.py`;
   - Entry point: `application`.
   
   Sahifa tepasida ko'rsatilgan `source …/bin/activate` yo'lini nusxalab oling.
5. **SSH kalit**: SSH Access → Manage SSH Keys → Generate a New Key (nomi `gh-deploy`, parolsiz) → **Authorize** → Private Key → nusxalang.
6. **Telegram bot**:
   - Telegram'da @BotFather → `/newbot` → token oling;
   - botga istalgan xabar yozing;
   - brauzerda `https://api.telegram.org/bot<TOKEN>/getUpdates` ni oching va `chat.id` ni oling.
   - Shu bot uy bildirishnomalarini ham yuboradi (ADR 0014). Deploy tokenni serverdagi `.env` ga yozadi va webhook'ni o'zi o'rnatadi. Shundan keyin `getUpdates` ishlamaydi — bu normal holat. Chat id'ni webhook yoqilishidan **oldin** oling.
   - Har bir oila a'zosi botni ilovada ulaydi: Sozlamalar → Bildirishnomalar → "Telegram'ni bog'lash".

`.env` faylini qo'lda yaratish **shart emas**: birinchi deploy uni o'zi yaratadi. JWT va signing kalitlari serverning o'zida generatsiya qilinadi va GitHub'ga chiqmaydi. Telegram webhook siri va Web Push (VAPID) kaliti ham serverda generatsiya qilinadi. Yangi Secret kerak emas: `TELEGRAM_BOT_TOKEN` va `PUBLIC_URL` deploy paytida `.env` ga yoziladi.

## B. GitHub Secrets (yagona ro'yxat)
GitHub → repo → Settings → Secrets and variables → Actions → **New repository secret**:

| Secret | Nima | Misol |
|---|---|---|
| `CPANEL_SSH_HOST` | SSH server nomi | `server12.hostmaster.uz` |
| `CPANEL_SSH_PORT` | SSH porti (hostmaster bergan) | `22` |
| `CPANEL_SSH_USER` | cPanel foydalanuvchi nomi | `myuser` |
| `CPANEL_SSH_KEY` | A.5 dagi private key (to'liq matn) | `-----BEGIN OPENSSH PRIVATE KEY-----…` |
| `CPANEL_APP_DIR` | A.4 dagi Application root | `smarthome-api` |
| `CPANEL_WEB_DIR` | A.2 dagi subdomen papkasi | `home.example.uz` |
| `CPANEL_VENV_ACTIVATE` | A.4 dagi activate yo'li | `/home/myuser/virtualenv/smarthome-api/3.11/bin/activate` |
| `CPANEL_DATABASE_URL` | A.3 dagi baza | `postgresql+psycopg://USER_shapp:PAROL@localhost:5432/USER_smarthome` |
| `PUBLIC_URL` | Sayt manzili | `https://home.example.uz` |
| `TELEGRAM_BOT_TOKEN` | A.6 dagi token | `123456:ABC…` |
| `TELEGRAM_CHAT_ID` | A.6 dagi chat id | `123456789` |
| `CPANEL_KNOWN_HOSTS` | *(tavsiya etiladi)* server kaliti: cPanel Terminal'da `ssh-keyscan -p PORT HOST` natijasi | `server12… ssh-ed25519 AAAA…` |

Secrets kiritilmaguncha deploy job'i **o'tkazib yuboriladi** (yiqilmaydi). GitHub Actions sahifasida "Deploy o'tkazib yuborildi — Secrets yo'q: …" yozuvi chiqadi.

## C. Birinchi kirish
Birinchi muvaffaqiyatli deploy'dan keyin cPanel → **Terminal**:
```
source /home/myuser/virtualenv/smarthome-api/3.11/bin/activate
cd ~/smarthome-api && python -m app.cli create-owner --email siz@example.uz --name "Ism" --home-name "Uy"
```
Keyin telefonda `https://home.example.uz` → kirish → **Sozlamalar → PIN**, so'ng **Hub → Hub qo'shish**.

## Avtomatik jarayon (ma'lumot uchun)
| Qadam | Qayerda | Yiqilsa |
|---|---|---|
| Testlar, expand-only, toza PostgreSQL'da migratsiya, deploy stsenariylari | GitHub Actions | deploy yo'q, Telegram ⛔ |
| `pg_dump` → `~/sh-deploy/backups` (oxirgi 10 ta) | server | hech narsa o'zgarmaydi, Telegram ⏸ |
| Kod → `alembic upgrade head` → restart → health (aynan yangi build) → videosiz bulut tekshiruvi | server | **avtomatik qaytish**: kod + DB zaxiradan, Telegram ⚠️ |
| Qaytish ham yiqilsa | server | Telegram 🆘. Zaxiralar `~/sh-deploy/backups` da turadi |
| Cron (`expire_due`, `energy`, `retention`, kunlik zaxira) | server | avtomatik o'rnatiladi |

Kunlik zaxiralar: `~/sh-deploy/daily` (14 kun). Deploy oldidan olingan zaxiralar: `~/sh-deploy/backups` (oxirgi 10 ta).

## Muammo bo'lsa
- 503: cPanel → Setup Python App → **Restart**. Log: `~/smarthome-api/stderr.log`.
- Deploy log'i: GitHub → Actions → `deploy-cloud` → oxirgi run.
- Qo'lda tiklash (faqat 🆘 holatda): `gunzip -c ~/sh-deploy/backups/<fayl>.sql.gz | psql "$DATABASE_URL"`. `DATABASE_URL` dagi `+psycopg` qismini olib tashlang.
