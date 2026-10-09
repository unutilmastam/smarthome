# 0016 — Tashqi ekotizimlar: Tuya (lokal), IR pult, Yandex Alisa

- Holat: qabul qilingan
- Sana: 2026-10-09
- Egasining so'rovi: "Yuborgan qurilmalarimni (Tuya Wi-Fi rele 7–32V, Wi-Fi avtomat TO-Q-SY2-JWT) va shu tizimda ishlaydigan shunga o'xshash qurilmalarni ulaydigan funksiya qo'sh. Alisa hub'ini, Alisa chiroqlari va boshqa Alisa qurilmalarini boshqarsin. Smart televizorlarni ulasin. Konditsioner va oddiy televizorlarni smart pult orqali ilovadan boshqarsin. Xullas, har qanday qurilma ulanishi kerak."

## Kontekst
Hozirgacha qurilma faqat bitta yo'l bilan ulanardi: bizning ESPHome proshivkasi va uydagi lokal MQTT (ARCHITECTURE 5). Egasi esa do'kondagi tayyor qurilmalarni ishlatadi:
- **Tuya / Smart Life** — rele, avtomat, rozetka, chiroq, IR pult. Ichida Tuya proshivkasi bor.
- **Yandex Alisa** ekotizimi — Yandex Stansiya, Alisa chiroqlari va rozetkalari, Alisa'ga ulangan televizorlar.

Ularni qayta proshivka qilish lehim va kompyuter talab qiladi, egasida esa faqat telefon va iPad bor. Demak, tayyor proshivka bilan ishlash kerak. Bunda tizim qoidalari buzilmasligi shart:
- holat faqat haqiqiy qaytar aloqadan "tasdiqlangan" bo'ladi;
- port ochilmaydi;
- sir kodga yozilmaydi.

## Qaror

### 1. Tuya qurilmalari — Hub orqali, uy tarmog'ida (lokal)
- Yangi adapter: `adapter = "tuya"`, `protocol = "tuya-local"`.
- **Hub** qurilma bilan Tuya'ning lokal protokoli (3.1–3.5) orqali **uy Wi-Fi tarmog'ida to'g'ridan-to'g'ri** gaplashadi (`services/hub/gateway/tuya.py`, `tinytuya` kutubxonasi). Tuya buluti ishlatilmaydi va internet uzilsa ham ishlaydi.
- Hub ichida bu "virtual qurilma" yo'li (ADR 0012, signalizatsiya bilan bir xil):
  - buyruq `_run` dan ko'prikka o'tadi;
  - ko'prik javobi `ack` bo'ladi;
  - qurilma holati (DPS) oddiy `state` xabariga aylantirilib, `_handle_state` ga beriladi.
  - Shuning uchun **tasdiqlash, PIN, avtomatika va bildirishnomalar o'zgarishsiz ishlaydi**.
- **Tasdiq faqat qurilmaning o'z javobidan** (DPS), `source = "reported"`. Buyruqdan keyin ko'prik holatni darhol qayta o'qiydi. Kutilgan qiymat kelsa — `confirmed`, kelmasa — `no_feedback`.
- **Profillar** (qaysi DPS nima ekanini bildiradi):

  | Profil | Qurilmalar | Capability | Standart DPS |
  |---|---|---|---|
  | `switch` | rele, oddiy rozetka/kalit | `switch` | 1 = on |
  | `plug_meter` | quvvat o'lchaydigan rozetka | `switch` + `power_meter` | 1 = on, 18 = mA, 19 = W×10, 20 = V×10, 17 = kWh×1000 |
  | `breaker` | Wi-Fi avtomat (dlq, masalan TO-Q-SY2-JWT) | `breaker` + `power_meter` | 16 = yoqilgan, 6 = A faza (base64: V/A/W), 1 = kWh×100, 9 = nosozlik |
  | `light` | Tuya chiroq | `switch` + `dimmer` | 20 = on, 22 = yorqinlik (10–1000) |
  | `ir` | IR pult (smart pult) | `remote` | — (o'rgatilgan kodlar) |

  DPS raqamlari modelga qarab farq qiladi. Shuning uchun har birini qurilma sozlamasida o'zgartirish mumkin (`connection.dps`). Ko'prik o'qigan **barcha** DPS'lar hub jurnaliga yoziladi, shunda mosligini tekshirish oson.
- **Qiymat o'ylab topilmaydi:**
  - DPS kelmasa, qiymat `unknown` bo'ladi;
  - profilda umuman bo'lmasa — `not_supported`;
  - qurilma javob bermasa — `offline`.
- **Avtomat (breaker):** himoya chegaralarini (ortiqcha tok yoki kuchlanish) avtomatning o'zi saqlaydi va o'zi ishlatadi (CLAUDE.md 6-qoida: xavfsizlik qurilmada).
  - Nosozlik DPS'i nolga teng bo'lmasa va avtomat o'chiq bo'lsa, `tripped = true` bo'ladi. Ko'prik bunday avtomatni masofadan **yoqmaydi**: `rejected` / `safety_rule`, xuddi ADR 0015 dagi kabi.
  - Profilda nosozlik DPS'i bo'lmasa, `tripped` — `not_supported`. Bunda himoyani faqat avtomatning o'zi hal qiladi.
- **Kalit (`local_key`)** — qurilma siri:
  - Bulutda **shifrlangan** holda saqlanadi (AES-GCM, `SIGNING_MASTER_KEY` dan HKDF orqali olingan alohida kalit bilan).
  - Qurilma API'si uni **hech qachon qaytarmaydi**, faqat yozish mumkin.
  - U faqat Hub'ga, Hub tokeni bilan himoyalangan `/hub/config` orqali beriladi.
  - Kalitni bilish ham yetarli emas: qurilmaga faqat uy tarmog'idan ulanish mumkin, chunki port ochilmaydi.
- Kalitni olish (bir marta, telefondan): qurilma Smart Life ilovasiga ulanadi → iot.tuya.com da loyiha ochiladi → Smart Life hisobi bog'lanadi → har bir qurilmaning `Device ID` va `Local Key` qiymatlari ko'chiriladi. Yo'riqnoma: `docs/runbooks/tuya.md`.

### 2. IR pult (konditsioner, oddiy televizor) — yangi capability `remote`
- Tuya IR pult (smart pult) Hub orqali boshqariladi, `ir` profili bilan.
- **Tugmalar asl pultdan o'rgatiladi:**
  1. ilovada "O'rgatish" bosiladi;
  2. Hub IR pultni o'rganish rejimiga qo'yadi;
  3. asl pultning tugmasi bosiladi;
  4. olingan kod Hub'da saqlanadi.
- Kodlar faqat Hub'da turadi va zaxira nusxasi Hub bazasida bo'ladi. Ular sir emas, lekin bulutga ham kerak emas.
- `remote` capability'si:
  - `buttons` atributi — o'rgatilgan tugmalar ro'yxati, Hub xabar beradi;
  - harakatlar: `press` (bosish), `learn` (o'rgatish), `forget` (unutish).
- **IR'da qaytar aloqa yo'q.** Shuning uchun `press` faqat `acked` (yuborildi) bo'ladi va hech qachon `confirmed` bo'lmaydi (CLAUDE.md 2-qoida).
  - `learn` esa haqiqiy tasdiq oladi: kod qabul qilinsa, `buttons` ro'yxatida paydo bo'ladi.
- Ilovada pult ko'rinishi `config.layout` bo'yicha tanlanadi: `tv` (raqamlar, kanal, ovoz, OK, strelkalar) yoki `ac` (yoqish/o'chirish, harorat va rejim tugmalari). Har qanday tugmaga o'z nomini berib o'rgatish ham mumkin.

### 3. Yandex Alisa — bulut orqali (Yandex Smart Home API)
- Alisa qurilmalari (Stansiya, chiroq, rozetka, Alisa'ga ulangan televizor, konditsioner) Yandex bulutida turadi, uy tarmog'ida emas. Shuning uchun ular **bizning bulutimiz orqali** boshqariladi:
  - `api.iot.yandex.net` (`iot:view`, `iot:control`);
  - `adapter = "yandex"`.
  - Bu yerda Hub ishtirok etmaydi.
- **Token:**
  - egasi o'z Yandex hisobi bilan bir marta OAuth token oladi;
  - token bulutda shifrlangan holda saqlanadi (1-banddagi kabi);
  - API uni qaytarmaydi.
- **Holat** cron orqali har daqiqada sinxronlanadi (`app.jobs.yandex_sync`). Yandex bergan qiymat `reported` bo'ladi, vaqti esa Yandex'dagi `last_updated` dan olinadi.
- **Buyruq:**
  - bulut `devices/actions` ni chaqiradi;
  - Yandex `DONE` qaytarsa — `acked`;
  - shundan keyin qurilma holati qayta o'qiladi va yangi qiymat kelsa — `confirmed`.
  - Yandex xatosi `failed` ga aylanadi va sababi saqlanadi.
- **Imzo (CLAUDE.md 5-qoida):** bu buyruqlar Hub'ga bormaydi, shuning uchun HMAC imzosi ishlatilmaydi. Buning o'rniga bulut buyruqni o'zi bajaradi va oddiy qoidalar amal qiladi: foydalanuvchi huquqi, PIN, muddat va audit.
- **Moslik:**

  | Yandex | Bizda |
  |---|---|
  | `on_off` | `switch` |
  | `range/brightness` | `dimmer` |
  | `range/temperature` (konditsioner) | `climate.target_temp` |
  | `mode/thermostat` | `climate.mode` |
  | televizor (`media_device.tv`): `on_off`, `range/volume`, `range/channel`, `toggle/mute` | yangi `media` capability |
  | `float` (harorat, namlik, quvvat) | `environment` / `power_meter` |

  Mos kelmaydigan imkoniyatlar ko'rsatilmaydi. O'ylab topilgan boshqaruv yo'q.
- **Alisa ssenariylari** (Yandex ilovasida tuzilgan) ilovadan ishga tushirilishi mumkin.
- **Keyingi bosqich (bu ADR'da emas):** bizning qurilmalarni Alisa'ga ovozli boshqaruv uchun berish ("Alisa, bog' chirog'ini yoq"). Buning uchun Yandex Dialogs'da "aqlli uy" ko'nikmasi va bizda OAuth server kerak.

### 4. Smart televizorlar
- Alisa'ga ulangan televizor (Yandex TV, ko'pchilik Android TV) **3-band orqali** `media` sifatida boshqariladi.
- Oddiy televizor **2-band orqali** IR pult bilan boshqariladi.
- LG webOS va Samsung Tizen'ning o'z lokal protokollari keyingi bosqichda Hub ko'prigi sifatida qo'shiladi.

## Ko'rib chiqilgan muqobillar
- **Tuya'ni bulut API orqali boshqarish:** internet va Xitoy bulutiga bog'liq bo'lib qoladi, kechikish katta, uydagi avtomat uchun ishonchsiz — rad etildi. Bulut faqat bir marta kalit olish uchun ishlatiladi.
- **Qurilmalarni ESPHome yoki OpenBeken'ga qayta proshivka qilish:** eng toza yo'l, lekin lehim yoki kompyuter kerak. Egasining sharoitiga to'g'ri kelmaydi. Keyinchalik mumkin, shartnomalar o'zgarmaydi.
- **Alisa'ni Hub orqali boshqarish:** Alisa qurilmalari LAN'da lokal API bermaydi — rad etildi.
- **Home Assistant'ni Hub ichiga qo'yish:** juda ko'p qurilmani "bepul" beradi, lekin bizning tasdiq, imzo va PIN qoidalarimizni chetlab o'tadi va yana bitta katta tizimni qo'llab-quvvatlashni talab qiladi. Hozircha rad etildi.

## Oqibatlar
### Ijobiy
- Egasi Smart Life va Alisa qurilmalarini ilova ichida ishlatadi. Qoidalar hamma qurilma uchun bir xil.
- Yangi Tuya qurilmasi uchun ko'pincha kod emas, profil yoki DPS sozlamasi kifoya qiladi.

### Salbiy / xavflar
- Tuya DPS raqamlari modelga qarab farq qiladi: noto'g'ri raqam qiymatni noto'g'ri ko'rsatishi mumkin. Shuning uchun har bir yangi model **[REAL]** sinovdan o'tkaziladi (`docs/hardware/tests/tuya.md`). Profil standartlari faqat simulyatorda sinalgan **[SIM]**.
- Yandex holati daqiqada bir yangilanadi. Bu Hub'dagi qurilmalardan sekinroq.
- Shifrlangan sirlar `SIGNING_MASTER_KEY` ga bog'liq: u o'zgarsa, kalitlarni qayta kiritish kerak bo'ladi.

## Tasdiqlanishi kerak
- [REAL] TO-Q-SY2-JWT avtomatning haqiqiy DPS xaritasi.
- [REAL] 7–32V rele (CB2S/BK7231 modul): DPS 1.
- [REAL] Tuya IR pult: o'rgatish va yuborish.
- [REAL] Yandex token va qurilmalar ro'yxati.
