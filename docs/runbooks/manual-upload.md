# SmartHome'ni hostingga qo'lda yuklash (zip orqali, iPad'dan)

Bu yo'l GitHub Actions'siz ishlaydi. Zip ichida tayyor ilova (`api/`), sayt (`web/`) va o'rnatish skripti (`install.sh`) bor. Skript avtomatik deploy bilan **bir xil** ishlaydi:
1. bazani zaxiralaydi;
2. kodni qo'yadi;
3. migratsiya qiladi;
4. ilovani qayta ishga tushiradi;
5. tekshiradi.

Xato bo'lsa, o'zi avvalgi holatga qaytaradi.

Zip ichida **hech qanday sir yo'q**: parollar va kalitlar serverning o'zida yaratiladi va faqat `smarthome-api/.env` faylida turadi.

---

## 1-qadam. cPanel'da tayyorgarlik (faqat birinchi marta, ~10 daqiqa)

hostmaster.uz → cPanel'ga kiring.

1. **Subdomen.** *Domains → Create A New Domain*:
   - Domain: `home.sizningdomen.uz`;
   - Document Root'ni eslab qoling (odatda `home.sizningdomen.uz`);
   - **Submit**.
   - Keyin *SSL/TLS Status* → subdomenni belgilang → **Run AutoSSL** (https uchun).
2. **Baza.** *PostgreSQL Databases*:
   - *Create New Database*: masalan `smarthome` (to'liq nomi `USER_smarthome` bo'ladi);
   - *Add New User*: masalan `shapp`, parolni **Password Generator** bilan yarating va saqlab qo'ying;
   - *Add User To Database*: foydalanuvchini bazaga qo'shing → **ALL PRIVILEGES**.
3. **Python ilova.** *Setup Python App → Create Application*:
   - Python version: eng yuqorisi (kamida 3.10);
   - Application root: `smarthome-api`;
   - Application URL: `home.sizningdomen.uz` va yo'l `api`;
   - Application startup file: `passenger_wsgi.py`;
   - Application Entry point: `application`;
   - **Create** ni bosing.

## 2-qadam. Zip'ni yuklash

1. *File Manager* → chapda **Home** (`/home/USER`) papkasini oching.
2. **Upload** → `smarthome-….zip` faylini tanlang (iPad: Fayllar ilovasidan). Yuklanish 100% bo'lishini kuting.
3. File Manager'da zip faylni belgilang → **Extract** → manzil `/home/USER` → **Extract Files**.
   Natijada `smarthome-release` papkasi paydo bo'ladi.

## 3-qadam. O'rnatish (Terminal)

*cPanel → Terminal* (Advanced bo'limida) oching va yozing:

```
bash ~/smarthome-release/install.sh
```

Skript savollar beradi. Qavs ichidagi qiymat to'g'ri bo'lsa, shunchaki **Enter** bosing:

| Savol | Nima yozasiz |
|---|---|
| Sayt manzili | `home.sizningdomen.uz` |
| Python ilova papkasi | Enter (`smarthome-api`) |
| Sayt papkasi | Enter (subdomen Document Root'i) |
| Virtualenv activate yo'li | Odatda o'zi topadi → Enter |
| Baza nomi / foydalanuvchisi / paroli | 1-qadamda yaratganlaringiz (parol ekranda ko'rinmaydi) |
| Telegram bot tokeni | Bo'lsa — kiriting; bo'lmasa Enter (keyin qo'shasiz) |

So'ng 1–3 daqiqa kuting. Oxirida **✅ O'rnatildi** chiqadi va skript uy egasini so'raydi: email, ism, uy nomi va **parol** (kamida 10 belgi, ikki marta).

## 4-qadam. Tekshirish

1. Telefonda yoki iPad'da oching: `https://home.sizningdomen.uz`.
2. Email va parol bilan kiring.
3. **Sozlamalar → PIN kod** o'rnating. PIN darvoza, avtomatlar va signalizatsiya uchun kerak.
4. Safari'da **Ulashish → "Bosh ekranga qo'shish"**. Shunda ilova kabi ochiladi va Push xabarlari ishlaydi.
5. Uydagi Hub tayyor bo'lganda: **Hub → Hub qo'shish** (`infra/hub/install.md`).

## Yangilash (keyingi versiyalar)

1. Yangi zip'ni yuklang va xuddi shunday **Extract** qiling (eski `smarthome-release` ustiga yoziladi).
2. Terminal'da `bash ~/smarthome-release/install.sh` buyrug'ini ishga tushiring va hamma savolga **Enter** bosing: javoblar eslab qolingan.

Bazangiz va sozlamalaringiz saqlanadi. Har yangilashdan oldin zaxira olinadi (`~/sh-deploy/backups`, oxirgi 10 tasi).

## Muammo bo'lsa

| Belgi | Ma'nosi | Nima qilish kerak |
|---|---|---|
| ⏸ "Hech narsa o'zgartirilmadi" | O'rnatish boshlanmadi: masalan, baza paroli noto'g'ri yoki boshqa o'rnatish ketyapti | Sababi yuqorida yozilgan. Tuzatib, qayta ishga tushiring |
| ⚠️ "AVTOMATIK QAYTARILDI" | Yangi versiya ishlamadi, eski versiya va baza joyida | `~/sh-deploy/last-install.log` faylini menga yuboring |
| Sayt ochiladi, kirish ishlamaydi | API ishga tushmagan | *Setup Python App* → **Restart**. Log: `~/smarthome-api/stderr.log` |
| 🆘 | Qaytarish ham muvaffaqiyatsiz | `docs/runbooks/backup-restore.md` ga qarang. Zaxiralar `~/sh-deploy/backups` da |

Avtomatik deploy'ga keyin o'tish mumkin: GitHub Secrets kiritilsa (`docs/runbooks/deploy.md`), har yangilanish o'zi chiqadi. Ikkala yo'l ham bir xil skriptdan foydalanadi, shuning uchun aralashtirib ishlatish xavfsiz.
