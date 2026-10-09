# SmartHome'ni hostingga o'rnatish (zip orqali, telefondan)

Bu yo'l GitHub Actions'siz ishlaydi. Zip ichida quyidagilar bor:
- tayyor ilova (`api/`);
- sayt (`web/`);
- o'rnatish skripti (`install.sh`).

Skript **avval hamma narsani tekshiradi**:
- subdomen;
- https sertifikati;
- Python ilova;
- bazaga kirish.

Shundan keyingina serverga tegadi. Biror narsa yetishmasa, nimani qilish kerakligini o'zbekcha aytadi va hech narsani o'zgartirmaydi. Keyin avtomatik deploy bilan **bir xil** ishni bajaradi:
1. zaxira oladi;
2. kodni o'rnatadi;
3. migratsiya qiladi;
4. ilovani qayta ishga tushiradi;
5. tekshiradi.

Xato bo'lsa, o'zi avvalgi holatga qaytaradi.

Zip ichida **hech qanday sir yo'q**. Parollar va kalitlar serverning o'zida yaratiladi va faqat `smarthome-api/.env` faylida turadi.

Quyida misol uchun subdomen `smy.itcode.uz`, cPanel foydalanuvchisi esa `itcode`. O'zingiznikiga moslang.

---

## 1-qadam. cPanel'da tayyorgarlik (faqat birinchi marta)

1. **Subdomen.** *Domains → Create A New Domain*:
   - Domain: `smy.itcode.uz`;
   - "Share document root" belgisini **olib tashlang**;
   - **Submit** ni bosing.
2. **SSL.** *SSL/TLS Status* → `smy.itcode.uz` ni belgilang → **Run AutoSSL**. 5–10 daqiqa kuting.
3. **Python ilova.** *Setup Python App → Create Application*:

   | Maydon | Qiymat |
   |---|---|
   | Python version | 3.10 yoki yuqori |
   | Application root | `smarthome-api` |
   | Application URL | `smy.itcode.uz`, yo'l: `api` |
   | Application startup file | `passenger_wsgi.py` |
   | Application Entry point | `application` |

   So'ng **Create** ni bosing.

**Baza yaratish shart emas.** Skript `itcode_smy` bazasi va foydalanuvchisini cPanel orqali o'zi yaratadi va ulaydi. O'zingiz yaratgan bo'lsangiz ham ishlaydi, faqat parolini bilishingiz kerak.

## 2-qadam. Zip'ni yuklash

1. *File Manager* → **Home** (`/home/itcode`) papkasini oching.
2. **Upload** → `smarthome-….zip` faylini tanlang. Yuklanish 100% bo'lishini kuting.
3. Zip faylni belgilang → **Extract** → **Extract Files**. Natijada `smarthome-release` papkasi paydo bo'ladi.

## 3-qadam. O'rnatish (Terminal)

*cPanel → Terminal* oching va yozing:

```
bash ~/smarthome-release/install.sh
```

Skript faqat 4 narsani so'raydi:

| Savol | Nima yozasiz |
|---|---|
| Subdomen | `smy.itcode.uz` |
| Baza nomi / foydalanuvchisi | **Enter** (o'zi `itcode_smy` ni taklif qiladi) |
| Baza paroli | Yangi parol o'ylab toping (skript bazani o'zi yaratadi). Bazani o'zingiz yaratgan bo'lsangiz, uning parolini yozing |
| Email va ilova paroli | Ilovaga shu email va parol bilan kirasiz (kamida 10 belgi, ikki marta) |

"Baza va foydalanuvchini o'zim yaratib qo'yaymi?" deb so'rasa, **Enter** bosing.

Keyin 2–5 daqiqa kuting. Telefon ekrani o'chmasin. Oxirida **✅ O'rnatildi** chiqadi.

## 4-qadam. Kirish

1. `https://smy.itcode.uz` ni oching.
2. Email va parol bilan kiring.
3. **Sozlamalar → PIN kod** o'rnating. PIN darvoza, avtomatlar va signalizatsiya uchun kerak.
4. Safari'da **Ulashish → "Bosh ekranga qo'shish"**. Shunda ilova kabi ochiladi va Push xabarlari ishlaydi.

Parolni unutsangiz, `bash ~/smarthome-release/install.sh` ni qayta ishga tushirmang. Uning o'rniga Terminal'da quyidagini bajaring:
```
cd ~/smarthome-api && . ~/virtualenv/smarthome-api/*/bin/activate && python -m app.cli create-owner --email SIZNING@EMAIL --name "Uy egasi"
```
Bu buyruq yangi parolni ikki marta so'raydi. Uy va undagi ma'lumotlar saqlanib qoladi.

## Yangilash (keyingi versiyalar)

1. Yangi zip'ni yuklang va xuddi shunday **Extract** qiling (ustiga yoziladi).
2. `bash ~/smarthome-release/install.sh` ni ishga tushiring. Subdomen so'ralganda **Enter** bosing, boshqa savol bo'lmaydi.

Bazangiz va sozlamalaringiz saqlanadi. Har yangilashdan oldin zaxira olinadi: `~/sh-deploy/backups`, oxirgi 10 tasi.

## Muammo bo'lsa

| Belgi | Ma'nosi | Nima qilish kerak |
|---|---|---|
| ⏸ | Hech narsa o'zgarmadi | Sababi va yechimi ekranda yozilgan. Tuzatib, qayta ishga tushiring |
| ⚠️ "AVTOMATIK QAYTARILDI" | Yangi versiya ishlamadi, eski versiya va baza joyida | `~/sh-deploy/last-install.log` ni yuboring |
| Kirishda "Email yoki parol noto'g'ri" | Uy egasi paroli boshqa | Yuqoridagi "parolni unutsangiz" buyrug'i |
| 🆘 | Qaytarish ham muvaffaqiyatsiz | `docs/runbooks/backup-restore.md`. Zaxiralar `~/sh-deploy/backups` da |

## Hammasini o'chirib, boshidan boshlash

Faqat SmartHome'ga tegishli narsalar o'chiriladi. Boshqa saytlaringiz (`nbx`, `usta`, `public_html`, …) qolaveradi.

1. *Setup Python App* → `smarthome-api` qatoridagi **axlat qutisi** (Destroy) → tasdiqlang.
2. *PostgreSQL Databases*:
   - SmartHome bazasini **Delete** qiling (masalan `itcode_smarthome`);
   - uning foydalanuvchisini **Delete** qiling (masalan `itcode_smy`).
   - **Boshqa bazalarga tegmang.**
3. *Domains* → eski subdomen (masalan `home.itcode.uz`) → **Manage** → **Remove Domain**.
4. *Terminal*da (papkalar va cron vazifalarini o'chiradi):
   ```
   crontab -l 2>/dev/null | grep -v smarthome-managed | crontab -; rm -rf ~/smarthome-api ~/smarthome-release ~/sh-deploy ~/home.itcode.uz ~/smarthome-*.zip; echo tozalandi
   ```

Avtomatik deploy'ga keyin o'tish mumkin: buning uchun GitHub Secrets kiritiladi (`docs/runbooks/deploy.md`). Ikkala yo'l ham bir xil skriptdan foydalanadi.
