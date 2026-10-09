# [REAL] sinov: Xavfsizlik tizimi (Faza 11)

Signalizatsiya Hub'da ishlaydi (ADR 0012). Simulyatsiya natijalari (`[SIM]`, `test_alarm.py`, `test_phase11.py`, e2e `security.spec.ts`) bu yerga yozilmaydi.

Tayyorgarlik:
- [ ] Inventar H-13: mavjud datchiklar, sirena.
- [ ] `security-sensor.yaml` (har bir eshik/deraza/harakat uchun), `siren.yaml` (`max_on_s`).
- [ ] Ilovada: **Xavfsizlik → Signalizatsiyani sozlash**: zonalar, sirena, kechikishlar.

| # | Sinov | Kutilgan natija | Sana | Kim | Natija | Izoh |
|---|---|---|---|---|---|---|
| 1 | Deraza ochiq turganda **Uydan chiqyapman** | Rad etiladi: "ochiq zona"; voqea | | | | |
| 2 | Hammasi yopiq — **Uydan chiqyapman** (PIN) | "Yoqilmoqda" → chiqish vaqtidan keyin "Qo'riqlanmoqda ✓" | | | | |
| 3 | Kirish eshigini ochish | "Kirish vaqti — PIN kiriting!"; vaqt ichida o'chirilsa sirena **yo'q** | | | | |
| 4 | Kirish eshigini ochib, o'chirmaslik | Kechikishdan keyin sirena; voqea "SIGNAL: Kirish eshigi" (muhim) | | | | |
| 5 | Sirena ishlayotganda Hub tokini uzish | Sirena `max_on_s` da **o'zi** to'xtaydi (proshivka) | | | | |
| 6 | **Internetni uzib**, harakat datchigini ishga tushirish (qo'riqlash yoqiq) | Sirena yoqiladi (Hub lokal); internet qaytgach voqea ilovada | | | | |
| 7 | Qo'riqlash yoqiq paytida Hub'ni qayta ishga tushirish | Qayta yongach holat "Qo'riqlanmoqda" saqlangan | | | | |
| 8 | Zona datchigining tokini uzish (qo'riqlash yoqiq) | Voqea "Zona datchigi aloqasiz" | | | | |
| 9 | Oila a'zosi PIN'siz o'chirishga urinish | PIN so'raladi; noto'g'ri PIN → rad | | | | |
