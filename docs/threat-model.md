# Tahdid modeli (Threat model)

- Versiya: 1 (Faza 0) — 2026-10-07
- Qamrov: cloud (cPanel), managed MQTT broker, Home Hub, ESP32 qurilmalar, PWA, kameralar, ishlab chiqish/deploy zanjiri.
- Qayta ko'rib chiqish: har bir yangi qurilma turi yoki tashqi xizmat qo'shilganda, va Faza 14 da to'liq.

Holat ustuni: `rejalashtirilgan (Faza N)` — himoya hali kodda yo'q. Faza 0 da hech qanday himoya amalda **sinalmagan**.

---

## 1. Aktivlar

| ID | Aktiv | Nima uchun qimmat | Ta'sir (buzilsa) |
|---|---|---|---|
| A1 | Darvoza | Uyga jismoniy kirish | Kritik |
| A2 | Qulf(lar) | Uyga jismoniy kirish | Kritik |
| A3 | Kamera video va arxiv | Oila maxfiyligi, uy rejasi, kun tartibi | Kritik |
| A4 | Elektr liniyalari (kontaktorlar) | Svetni o'chirish: muzlatgich, isitish, kamera, xavfsizlik tizimi | Yuqori |
| A5 | Sug'orish klapani / nasos | Suv toshqini, nasos kuyishi | O'rta |
| A6 | Xavfsizlik rejimi (armed/disarmed), datchiklar | O'chirilsa — signalizatsiya ishlamaydi | Yuqori |
| A7 | Hisob ma'lumotlari: parol, PIN, refresh token, `hub_token` | Barcha boshqa aktivlarga yo'l | Kritik |
| A8 | `SIGNING_MASTER_KEY`, `signing_key_hex` | Buyruq soxtalashtirish | Kritik |
| A9 | Cloud DB (foydalanuvchilar, audit, holat tarixi) | Kun tartibi (kim qachon uyda), audit dalili | Yuqori |
| A10 | Home Hub (apparat + disk) | Lokal "miya", video, sirlar | Kritik |
| A11 | GitHub repo, Actions Secrets, cPanel hisobi | Kodga/deployga zararli o'zgarish | Kritik |
| A12 | Lokal tarmoq (Wi-Fi, router) | Barcha lokal qurilmalarga yo'l | Yuqori |

## 2. Hujumchilar

| Kim | Imkoniyat |
|---|---|
| Internetdagi tasodifiy hujumchi | Skanerlash, parol taxmin qilish, ma'lum zaifliklar |
| Maqsadli hujumchi (o'g'ri) | Uyga jismoniy kirish maqsadi; Wi-Fi yaqinida bo'lishi mumkin |
| Shared hostingdagi "qo'shni" yoki buzilgan hosting | Fayl/DB'ga ruxsatsiz kirish ehtimoli |
| Uchinchi tomon xizmat (broker, Tailscale, Telegram) buzilishi | Trafikni ko'rish/o'zgartirish |
| Ruxsati cheklangan ichki foydalanuvchi (mehmon, ko'ruvchi, sobiq uy xodimi) | O'z ruxsatidan oshib ketishga urinish |
| Begona/buzilgan IoT qurilma LAN'da | Lokal broker, kameralar, Hub'ga hujum |

## 3. Tahdidlar va himoyalar

### T1. Foydalanuvchi tokenini o'g'irlash (access/refresh)
- **Stsenariy:** XSS, telefon o'g'irlanishi, ochiq Wi-Fi'da ushlab qolish.
- **Himoya:**
  - HTTPS hamma joyda (AutoSSL), HSTS.
  - Access JWT 15 daq, faqat xotirada. Refresh 30 kun, DB'da faqat SHA-256, **rotatsiya**; eski refresh qayta ishlatilsa — foydalanuvchining barcha sessiyalari bekor (Faza 2).
  - `logout-all`, parol o'zgarsa boshqa sessiyalar bekor.
  - `risk: high` harakatlar (darvoza, qulf, kontaktor) uchun alohida **PIN** (`confirm_pin`) — token yetarli emas.
  - Qat'iy CSP, `dangerouslySetInnerHTML` yo'q (Faza 6).
- **Holat:** rejalashtirilgan (Faza 2, 3, 6). Refresh token saqlash joyi — Faza 6 ADR.

### T2. Parol taxmin qilish / credential stuffing
- **Himoya:** Argon2id; IP bo'yicha rate limit + akkaunt bloki (5 xato → 5 daq); mavjud bo'lmagan email uchun ham bir xil vaqt (dummy hash); ommaviy ro'yxatdan o'tish yo'q (owner CLI orqali yaratiladi).
- **Holat:** rejalashtirilgan (Faza 2).

### T3. Broker paroli o'g'irlanishi
- **Stsenariy:** `app-{user}` yoki `hub-{home}` hisobi sizib chiqadi va hujumchi `cmd` topikiga yozadi.
- **Himoya:**
  - Buyruqlar **HMAC imzoli** (ADR 0004); Hub imzosiz buyruqni rad etadi — broker'ga yozish imkoniyati buyruq bajarishga yetmaydi.
  - ACL: `app-{user}` faqat o'qiydi; `backend` faqat `cmd` ga yozadi; `hub-{home}` faqat o'z uyi topiklari.
  - Foydalanuvchiga qisqa muddatli broker hisobi (`/realtime/credentials`).
  - Broker hisobi bo'yicha qolgan xavf: `state` topikiga soxta holat yozish (UI'ni aldash) → `hub-{home}` paroli faqat Hub `.env` da; Backend holatni broker'dan emas, `POST /hub/report` dan (hub token bilan) saqlaydi.
- **Holat:** rejalashtirilgan (Faza 3, 5).

### T4. Cloud DB sizishi (shared hosting)
- **Himoya:**
  - DB'da sirlar ochiq holda yo'q: parol/PIN — Argon2id, refresh va `hub_token` — SHA-256, uy imzo kaliti **saqlanmaydi** (master kalitdan hosil qilinadi).
  - Video DB'da yo'q (ADR 0006).
  - Telemetriya agregatlangan; xom ma'lumot faqat Hub'da.
  - DB foydalanuvchisi minimal huquqli; DB tashqi ulanishga yopiq (faqat localhost).
- **Qolgan xavf:** kun tartibi (holat tarixi, audit) oshkor bo'ladi. `SIGNING_MASTER_KEY` ham fayl tizimidagi `.env` da — hosting to'liq buzilsa ikkalasi birga sizadi (T10).
- **Holat:** rejalashtirilgan (Faza 2, 3).

### T5. Replay (eski buyruqni qayta yuborish)
- **Himoya:** har buyruqda `command_id` (UUID) + `expires_at` (10 s, `high` uchun 5 s); Hub bajarilgan `command_id` larni SQLite'da saqlaydi; muddati o'tgan yoki takroriy → `rejected`. Internet qaytganda eskirgan buyruqlar **bajarilmaydi**. NTP majburiy.
- **Holat:** rejalashtirilgan (Faza 3, 4).

### T6. LAN'dagi begona yoki buzilgan qurilma
- **Stsenariy:** mehmon telefoni, arzon IoT qurilma yoki buzilgan kamera lokal broker/ESP32'ga hujum qiladi.
- **Himoya:**
  - Lokal Mosquitto: anonim ulanish o'chiq, har ESP32'ga alohida login + ACL (faqat o'z `home/{device_id}/*`); `cmd` ga faqat gateway yozadi.
  - ESPHome: API shifrlash kaliti va OTA paroli har qurilmada alohida.
  - Kameralar alohida VLAN, internetga chiqish yopiq; IoT VLAN (router imkon bersa — H-07).
  - Mehmon Wi-Fi alohida (router imkon bersa).
  - Hub `local-api` lokal sessiya bilan autentifikatsiya talab qiladi (LAN'da bo'lish — ruxsat emas).
- **Qolgan xavf:** router VLAN qo'llamasa — tarmoq tekis. ESP32 ↔ lokal Mosquitto TLS'siz bo'lishi mumkin (ESP32 resurslari) — LAN'da tinglash ehtimoli.
- **Holat:** rejalashtirilgan (Faza 4, 8, 10). Router modeli noma'lum (H-07).

### T7. Ichki foydalanuvchi ruxsatidan oshib ketishi (mehmon, ko'ruvchi)
- **Himoya:** server tomonida rol tekshiruvi (`app/core/permissions.py`, ARCHITECTURE 9); a'zo bo'lmagan resursga **404** (ID taxmin qilinmasin); faqat owner a'zo qo'shadi; Hub payload'dagi rolni ham tekshiradi; mehmon grants tayyor bo'lmaguncha faqat ko'radi; audit log (faqat qo'shiladi).
- **Holat:** rejalashtirilgan (Faza 2, 3).

### T8. Kiruvchi port orqali hujum (router port forwarding, UPnP)
- **Himoya:** port forwarding yo'q, UPnP o'chiq; Hub faqat tashqariga ulanadi; masofaviy kirish faqat Tailscale (ACL bilan, faqat egasi qurilmalari). Faza 14 da tashqi port skan.
- **Holat:** rejalashtirilgan (Faza 8, 14).

### T9. Hub o'g'irlanishi yoki jismoniy kirish
- **Himoya:** Hub yashirin/qulflangan joyda; disk shifrlash (LUKS) — tavsiya, lekin svet o'chib-yonganda avtomatik yuklanish talabi bilan to'qnashadi (ochiq savol: TPM bilan ochish). Cloud'da Hub `revoke` → `hub_token` bekor, yangi kalitlar.
- **Qolgan xavf:** HMAC kaliti Hub'da — Hub o'g'irlansa shu uy uchun buyruq imzolash mumkin (lekin o'g'ri allaqachon uyda). Ed25519 muqobili ADR 0004 da.
- **Holat:** rejalashtirilgan (Faza 8, 14).

### T10. cPanel / hosting hisobi buzilishi
- **Himoya:** cPanel 2FA; kuchli parol; SSH faqat kalit bilan (deploy uchun alohida kalit, GitHub Secrets'da); `.env` `public_html` dan **tashqarida**, ruxsatlar `600`; master kalit rotatsiya runbook'i.
- **Qolgan xavf:** hosting provayderning o'zi ishonchli tomon hisoblanadi.
- **Holat:** rejalashtirilgan (Faza 7, 14). 2FA yoqilganmi — tasdiqlanmagan.

### T11. Ta'minot zanjiri (supply chain): GitHub, bog'liqliklar, Docker image'lar
- **Himoya:** GitHub 2FA; `main` himoyalangan (PR + CI yashil); bog'liqliklar versiyasi qotirilgan; `pip-audit`, `npm audit`, gitleaks (Faza 14); Dependabot; Actions'da uchinchi tomon action'lar SHA bo'yicha qotiriladi; Hub image'lari GHCR'dan, teg emas — digest bo'yicha (Watchtower ehtiyotkorlik bilan).
- **Holat:** rejalashtirilgan (Faza 1, 7, 14).

### T12. Sirlarning repo'ga tushishi
- **Himoya:** `.gitignore` (`.env`, `*.env`), faqat `.env.example`; CI'da gitleaks; production'da dev-sir bilan ishga tushish xato beradi (Faza 1).
- **Holat:** `.gitignore` bor; qolgani rejalashtirilgan (Faza 1, 14).

### T13. Xavfli fizik harakat dasturiy xato tufayli (safety)
- **Stsenariy:** nasos internet uzilganda o'chmay qoladi; darvoza odam/mashina ustiga yopiladi; kontaktor muhim liniyani o'chiradi.
- **Himoya:** xavfsizlik chegaralari **proshivkada/apparatda**: `max_runtime`, `fail_safe_state`, darvoza fotoelementi apparatda; svet qaytganda nasos har doim OFF; `confirmed` faqat haqiqiy qaytar aloqa (gerkon, yordamchi kontakt, oqim datchigi) bilan; IR qurilmalar `assumed`. Dastur — qo'shimcha himoya, yagona emas.
- **Holat:** rejalashtirilgan (Faza 4 `[SIM]`, 8–11 `[REAL]`).

### T14. Xizmat to'xtatilishi (DoS) va infratuzilma nosozligi
- **Stsenariy:** internet/cloud/broker yo'q, svet o'chdi, Hub diski to'ldi.
- **Himoya:** uy cloud'siz ishlaydi (`hub.local`); UPS; polling zaxira (ADR 0005); buyruq rate limit (60/daq); Hub `last_seen` > 3 daq → Telegram; Frigate retention + 85% ogohlantirish.
- **Holat:** rejalashtirilgan (Faza 4, 5, 10, 13).

### T15. Uchinchi tomon xizmatlariga ma'lumot oqishi (Telegram, Push, broker, Tailscale)
- **Himoya:** bildirishnomalarda video/rasm yo'q (ADR 0006), minimal matn; broker'ga telemetriya yuborilmaydi; Telegram bog'lash bir martalik kod bilan; Tailscale ACL.
- **Holat:** rejalashtirilgan (Faza 5, 13).

## 4. Ishonch chegaralari (trust boundaries)

1. Internet ↔ Cloud API — TLS, foydalanuvchi autentifikatsiyasi.
2. Cloud ↔ Broker ↔ Hub — TLS, broker ACL, **buyruq imzosi** (broker ishonchsiz deb hisoblanadi).
3. Hub ↔ LAN qurilmalari — Mosquitto login/ACL, ESPHome shifrlash. LAN ishonchsiz deb hisoblanadi.
4. Telefon ↔ Hub (Tailscale) — WireGuard, Tailscale ACL.
5. Qurilma ↔ fizik dunyo — proshivka/apparat chegaralari (dastur ishonchsiz deb hisoblanadi).

## 5. Ochiq savollar
- Hub disk shifrlash va avtomatik yuklanish (TPM?).
- `hub.local` uchun HTTPS (secure context) — ADR 0003.
- Lokal rejimdagi autentifikatsiya (internetsiz login) — alohida ADR.
- ESP32 ↔ lokal Mosquitto TLS — resurs va qulaylik balansi.
- Hub → Backend xabarlarini imzolash kerakmi (hozir TLS + `hub_token`).
