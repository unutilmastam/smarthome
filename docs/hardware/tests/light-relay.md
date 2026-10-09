# [REAL] sinov: ESP32 rele + chiroq (Faza 8)

Natijalar shu jadvalga yoziladi: sana, kim sinadi, natija (✓ yoki ✗), izoh. Simulyatsiyadagi natija bu yerga **yozilmaydi**.
Elektr montajini faqat malakali elektrik bajaradi (H-08). Sinov paytida yorug'lik zanjiri avtomat orqali himoyalangan bo'lishi shart.

Tayyorgarlik:
- [ ] Hub `infra/hub/install.md` bo'yicha o'rnatilgan, ilovada "Onlayn".
- [ ] `devices/esphome/light-relay.yaml` → `device_key`, `relay_pin` sozlangan; ESPHome Dashboard'da kompilyatsiya va o'rnatish OK.
- [ ] `sh mosquitto/make-passwd.sh garden_lights` (`DEVICE_PASSWORD_GARDEN_LIGHTS` `.env` da).
- [ ] Ilovada qurilma qo'shilgan: kalit `garden_lights`, imkoniyat "Yoqish/o'chirish".

| # | Sinov | Kutilgan natija | Sana | Kim | Natija | Izoh |
|---|---|---|---|---|---|---|
| 1 | Ilovadan **Yoqish** | Chiroq yonadi; ilovada ⏳ → ✓ "Tasdiqlandi"; holat "Yoqilgan ✓" | | | | |
| 2 | Ilovadan **O'chirish** | Chiroq o'chadi; ✓ | | | | |
| 3 | Devordagi tugma | Chiroq almashadi; ilovada holat ≤ 3 s da o'zgaradi (buyruqsiz) | | | | |
| 4 | Wi-Fi router'ni 2 daqiqaga o'chirish | Ilovada qurilma "Oflayn", qiymat ⚠ "Eskirgan"; buyruq tugmalari o'chiq; Wi-Fi qaytgach ≤ 1 daq da "Onlayn" | | | | |
| 5 | Chiroq yoniq turganda ESP32'ning tokini uzib, qayta ulash | Qayta yoqilgach chiroq **O'CHIQ** (`restore_mode: ALWAYS_OFF`), ilovada "O'chirilgan ✓" | | | | |
| 6 | Uydagi svetni o'chirib, qayta yoqish (UPS bilan) | Hub ishlashda davom etadi (UPS); ESP32 qaytgach holat to'g'ri | | | | |
| 7 | Router'da internetni uzish (LAN ishlaydi) | Devordagi tugma ishlaydi. Ilovadan masofaviy boshqaruv ishlamaydi (kutilgan). `hub.local` orqali boshqaruv **hali yo'q** — local-api keyingi faza | | | | |
| 8 | Internet qaytgach | Hub buferni yuboradi; ilovada oxirgi haqiqiy holat ko'rinadi; uzilish paytida yuborilgan buyruqlar **bajarilmaydi** | | | | |
| 9 | Hub'ni o'chirish (ESP32 ishlayapti) | Ilovada "Hub bilan aloqa yo'q"; buyruq → "Hub bilan aloqa yo'q" xatosi; devordagi tugma ishlaydi | | | | |
| 10 | Boshqa qurilma nomidan MQTT'ga yozish (`mosquitto_pub -u garden_lights ... -t home/front_gate/cmd`) | Broker rad etadi (ACL) | | | | |
| 11 | OTA yangilash (ESPHome Dashboard, Wi-Fi orqali) | Parol bilan muvaffaqiyatli; noto'g'ri parol bilan rad | | | | |
| 12 | 24 soat davomida ishlash | Uzilishlar soni (ilovadagi availability tarixi / Hub log) yozib olinadi | | | | |

Natija: hamma qator ✓ bo'lsa, `docs/PROGRESS.md` ga `[REAL]` deb yoziladi. ✗ bo'lsa — sabab va tuzatish yoziladi.
