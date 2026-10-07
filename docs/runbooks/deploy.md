# Runbook: hostmaster.uz cPanel'ga deploy (iPad'dan)

Hammasi brauzerda bajariladi: cPanel, GitHub. Kompyuter kerak emas.
Qavs ichidagi nomlar — sizning qiymatlaringiz. Misol: `home.example.uz`.

## 0. Oldindan
- cPanel'da **2FA** yoqilgan bo'lsin (Security → Two-Factor Authentication). Threat model T10.
- GitHub hisobida 2FA yoqilgan bo'lsin. `main` branch himoyalangan bo'lsin: PR va yashil CI talab qilinsin.

## 1. Subdomen va SSL
1. cPanel → **Domains** → Create A New Domain: `home.example.uz`. Document root: `home.example.uz`.
2. cPanel → **SSL/TLS Status** → `home.example.uz` uchun **Run AutoSSL**. Sertifikat chiqmaguncha keyingi qadamga o'tmang (cookie `Secure`, HSTS).

## 2. PostgreSQL
1. cPanel → **PostgreSQL Databases**: baza `USER_smarthome`, foydalanuvchi `USER_shapp` yarating. Parol uzun va tasodifiy bo'lsin; uni faqat `.env` ga yozing.
2. Foydalanuvchini bazaga qo'shing (ALL PRIVILEGES).
3. PostgreSQL versiyasini yozib oling → `docs/hardware/inventory.md` H-01c.

## 3. Python ilova
1. cPanel → **Setup Python App** → Create Application:
   - Python version: **3.10 yoki undan yuqori** (eng yuqorisini tanlang; versiyani H-01b ga yozing);
   - Application root: `smarthome-api`;
   - Application URL: `home.example.uz` / **`api`**;
   - Application startup file: `passenger_wsgi.py`;
   - Application Entry point: `application`.
2. Sahifa tepasida ko'rsatilgan virtualenv buyrug'ini yozib oling. Masalan: `source /home/USER/virtualenv/smarthome-api/3.10/bin/activate`. Bu `CPANEL_VENV_ACTIVATE`.
3. cPanel → **File Manager** → `smarthome-api/.env` faylini yarating (ruxsat 600):
   ```
   ENV=production
   DATABASE_URL=postgresql+psycopg://USER_shapp:PAROL@localhost:5432/USER_smarthome
   JWT_SECRET=<64 ta hex belgi>
   SIGNING_MASTER_KEY=<boshqa 64 ta hex belgi>
   COOKIE_SECURE=true
   REALTIME_PROVIDER=none
   ```
   Tasodifiy qiymat olish uchun cPanel → **Terminal**: `python3 -c "import secrets; print(secrets.token_hex(32))"` (ikki marta, ikki xil qiymat).
   Ilova xavfsiz bo'lmagan sozlama bilan ishga **tushmaydi**: SQLite, qisqa sir, `COOKIE_SECURE=false` va hokazo.

## 4. GitHub Actions uchun SSH kalit
1. cPanel → **SSH Access** → Manage SSH Keys → **Generate a New Key** (`gh-deploy`, parolsiz) → Authorize.
2. Private key'ni ko'ring va nusxalang → GitHub → repo → Settings → Secrets and variables → Actions → **Secrets**:
   - `CPANEL_SSH_KEY` — private key;
   - `CPANEL_SSH_HOST`, `CPANEL_SSH_PORT` (hostmaster bergan port), `CPANEL_SSH_USER`;
   - `CPANEL_KNOWN_HOSTS` — cPanel **Terminal**'da `ssh-keyscan -p PORT HOST` buyrug'i chiqargan qatorlar.
3. Shu sahifadagi **Variables**:
   - `DEPLOY_ENABLED=true`;
   - `CPANEL_APP_DIR=smarthome-api`;
   - `CPANEL_WEB_DIR=home.example.uz`;
   - `CPANEL_VENV_ACTIVATE=...`;
   - `PUBLIC_URL=https://home.example.uz`.
4. GitHub → Settings → Environments → `production` muhitini yarating (ixtiyoriy: "Required reviewers" — deploy'dan oldin tasdiqlash).

## 5. Birinchi deploy
- `main` ga merge bo'lgach, `test` workflow yashil bo'lsa `deploy-cloud` avtomatik ishga tushadi. Qo'lda ishga tushirish: Actions → deploy-cloud → **Run workflow**.
- Muvaffaqiyat belgisi: workflow oxiridagi health check `{"status":"ok"}` qaytaradi. Brauzerda `https://home.example.uz/api/v1/health` ni ham ochib tekshiring.

## 6. Birinchi owner
cPanel → **Terminal**:
```
source /home/USER/virtualenv/smarthome-api/3.10/bin/activate
cd ~/smarthome-api
python -m app.cli create-owner --email siz@example.uz --name "Ismingiz" --home-name "Uy"
```
Parol ikki marta so'raladi (kamida 10 belgi). Keyin telefonda `https://home.example.uz` ni oching, kiring va **Sozlamalar → PIN** o'rnating.

## 7. Cron
cPanel → **Cron Jobs**: `infra/cpanel/cron.txt` dagi uchta qatorni qo'shing (`APP` va `VENV` o'rniga o'z yo'llaringizni yozing).
- Zaxira uchun `~/.pgpass` kerak: bitta qator `localhost:5432:USER_smarthome:USER_shapp:PAROL`, ruxsat `chmod 600 ~/.pgpass`.
- Cron qatorining boshiga `PGDATABASE=USER_smarthome` qo'shing.
- Hosting har daqiqalik cron'ga ruxsat bermasa `*/5` qo'ying (H-01e).

## 8. Hub'ni ulash
1. Ilovada: **Hub** sahifasi → **Hub qo'shish** (owner yoki admin). `hub_token` va `signing_key_hex` **faqat bir marta** ko'rsatiladi: "Nusxalash" bilan oling.
2. Hub `.env`: `BACKEND_URL=https://home.example.uz`, `HUB_TOKEN=...`, `SIGNING_KEY_HEX=...` (`services/hub/.env.example`).
3. Ilovada Hub "Onlayn" bo'lishi kerak. Hali haqiqiy Hub bo'lmasa, simulyator ishlatiladi: `docker compose --profile sim up -d`.

## Muammo bo'lsa
- 503 yoki "Incomplete response": cPanel → Setup Python App → **Restart**. Log: `smarthome-api/stderr.log`.
- Ilova ishga tushmasa, ko'pincha sababi `.env` dagi xato. `ConfigError` xabari aynan qaysi qiymat noto'g'riligini aytadi.
- Deploy'ni orqaga qaytarish: GitHub → Actions → avvalgi muvaffaqiyatli `deploy-cloud` run → **Re-run**. Migratsiya orqaga qaytarilmaydi, shuning uchun migratsiyalar faqat oldinga mos qilib yoziladi.
