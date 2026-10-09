# Token yoki kalit o'g'irlandi (bekor qilish va almashtirish)

Qoida: shubha bo'lsa — **avval bekor qiling, keyin tekshiring**. Har bir qadam iPad'dan bajariladi.

## A. Telefon yoki planshet yo'qoldi, parol oshkor bo'ldi
1. Boshqa qurilmadan ilovaga kiring → Sozlamalar.
2. **"Barcha qurilmalardan chiqish"**:
   - barcha sessiyalar bekor bo'ladi;
   - shu foydalanuvchining barcha **Push obunalari o'chiriladi** (Faza 14), yo'qolgan telefonga uy signali boshqa kelmaydi.
3. **Parolni almashtiring.** Boshqa barcha sessiyalar ham bekor bo'ladi.
4. **PIN'ni almashtiring** (darvoza, qulf, kontaktor va signalizatsiya uchun).
5. Sozlamalar → Bildirishnomalar → Telegram → yo'qolgan telefondagi Telegram uchun **"Uzish"**. Yoki Telegram'ning o'zida: Settings → Devices → sessiyani yakunlash.
6. Boshqa a'zoning qurilmasi yo'qolgan bo'lsa: o'sha a'zo A–C qadamlarni o'zi bajaradi. Yoki egasi A'zolar sahifasida **"Chiqarish"** ni bosib, a'zoni uydan chiqaradi va keyin yangi parol bilan qayta qo'shadi.

Avtomatik himoya: o'g'irlangan refresh token **qayta ishlatilsa**, backend buni aniqlaydi va o'sha foydalanuvchining hamma sessiyasini bekor qiladi (`refresh_reuse`, audit log'da ko'rinadi).

## B. Hub tokeni yoki Hub'ning o'zi o'g'irlandi
1. Ilova → Hub → **Bekor qilish.** Shundan keyin bu token bilan bulutga hech qanday so'rov o'tmaydi (401).
2. Hub o'g'irlangan bo'lsa, unda imzo kaliti ham bor. **Imzo kalitini almashtiring:**
   - cPanel → File Manager → `smarthome-api/.env` → `SIGNING_MASTER_KEY=` qatoriga yangi qiymat yozing (64 ta hex belgi; cPanel Terminal'da: `python3 -c "import secrets;print(secrets.token_hex(32))"`);
   - cPanel → Setup Python App → **Restart**.

   Natijada eski kalit bilan imzolangan hech qanday buyruq yangi Hub'da qabul qilinmaydi. Yo'lda qolgan buyruqlar muddati o'tib bekor bo'ladi. Push xabarlaridagi eski "Ko'rdim" tugmalari ham ishlamay qoladi — bu normal holat.
3. Ilova → Hub → **Hub qo'shish** → yangi `HUB_TOKEN` va `SIGNING_KEY_HEX` → yangi Hub'ning `.env` iga yozing.
4. Tailscale admin → Machines → eski Hub → **Remove**.
5. O'g'irlangan Hub'da quyidagilar bor edi: broker parollari, ESP32 `secrets.yaml`, Wi-Fi paroli. **Wi-Fi parolini almashtiring.** ESP32'larga yangi Wi-Fi va broker parollarini OTA orqali yozing (ESPHome Dashboard), keyin `make-passwd.sh` bilan broker parollarini yangilang.

## C. Bulut sirlari oshkor bo'ldi (`.env`, server)
| Sir | Almashtirish | Natija |
|---|---|---|
| `JWT_SECRET` | `.env` da yangi qiymat → Restart | Hamma qayta login qiladi |
| `SIGNING_MASTER_KEY` | B.2 dagi kabi | Hub'ga yangi kalit kerak (B.3) |
| `TELEGRAM_BOT_TOKEN` | @BotFather → `/revoke` → yangi token → GitHub Secret `TELEGRAM_BOT_TOKEN` ni yangilang → keyingi deploy uni `.env` ga yozadi va webhook'ni qayta o'rnatadi | Bog'langan chatlar saqlanib qoladi |
| `TELEGRAM_WEBHOOK_SECRET` | `.env` dan qatorni o'chiring → keyingi deploy yangisini yaratadi va webhook'ni yangilaydi | — |
| `VAPID_PRIVATE_KEY` | `.env` dan qatorni o'chiring → keyingi deploy yangisini yaratadi | Har kim Push'ni qayta yoqishi kerak |
| `DATABASE_URL` paroli | cPanel → PostgreSQL Databases → foydalanuvchi parolini almashtirish → `.env` → Restart | — |

"Keyingi deploy" uchun yangi kod shart emas: GitHub → Actions → `deploy-cloud` → **Re-run**.

## D. GitHub yoki deploy kaliti oshkor bo'ldi
1. cPanel → SSH Access → Manage SSH Keys → `gh-deploy` → **Deauthorize / Delete.** Yangi kalit yarating → GitHub Secret `CPANEL_SSH_KEY` ni yangilang.
2. GitHub → Settings → Sessions va Personal access tokens → keraksizlarini bekor qiling. 2FA yoqilganini tekshiring.

Har bir hodisa audit log'ga yoziladi: kim, qachon, qaysi IP'dan nima qilgani. Ilovada audit sahifasi **hali yo'q**. Ma'lumot `GET /api/v1/homes/{id}/audit` orqali olinadi va bazada saqlanadi.
