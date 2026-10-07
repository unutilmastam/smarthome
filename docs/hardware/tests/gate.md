# [REAL] sinov: Darvoza (Faza 11)

Natijalar shu jadvalga yoziladi: sana, kim sinadi, natija (✓ yoki ✗), izoh. Simulyatsiyadagi natija bu yerga **yozilmaydi** (u `services/hub/tests/test_phase11.py` da, `[SIM]`).
Darvoza blokiga ulashni faqat malakali o'rnatuvchi bajaradi. **Fotoelement darvoza blokida (apparatda) ishlashda davom etadi** — biz uni o'chirmaymiz va chetlab o'tmaymiz.

Tayyorgarlik:
- [ ] Inventar H-05 javoblandi: blok modeli, OPEN/CLOSE/STOP kirishlari, fotoelement chiqishi.
- [ ] `devices/esphome/gate.yaml`: pinlar, `max_travel_s` (haqiqiy yurish vaqti × 1.5).
- [ ] Ilovada qurilma: kalit `front_gate`, turi "Darvoza", `unsupported`: `cover.position` (enkoder yo'q).

| # | Sinov | Kutilgan natija | Sana | Kim | Natija | Izoh |
|---|---|---|---|---|---|---|
| 1 | Ilovadan **Ochish** (PIN) | Darvoza ochiladi; "Ochilmoqda" → ochiq gerkon → "Ochiq ✓", buyruq "Tasdiqlandi" | | | | |
| 2 | Ilovadan **Yopish** (PIN) | "Yopilmoqda" → yopiq gerkon → "Yopiq ✓" | | | | |
| 3 | Yopilayotganda fotoelement nuriga qo'l qo'yish | Darvoza bloki to'xtaydi/qaytadi (apparat); ilovada "Fotoelement: To'silgan!", voqea "Fotoelement to'sildi"; buyruq "Tasdiqlandi" **bo'lmaydi** | | | | |
| 4 | Nur to'silganda **Yopish** | Rad etiladi: `safety_rule` "photocell interrupted" | | | | |
| 5 | Ochiq gerkon magnitini olib qo'yish va ochish | 60 s (max_travel) dan keyin "To'xtatilgan", voqea "Darvoza oxiriga yetmadi"; buyruq "Muvaffaqiyatsiz (no_feedback)" | | | | |
| 6 | Ikkala gerkonni bir vaqtda yopish (magnit bilan) | Holat "Noma'lum"; voqea "Gerkonlar bir-biriga zid" (muhim); har qanday buyruq rad etiladi | | | | |
| 7 | Darvozani ochiq qoldirish (10 daq) | Voqea "Darvoza 10 daqiqadan beri ochiq qoldi" | | | | |
| 8 | ESP32 tokini uzish | Darvoza o'z-o'zidan harakatlanmaydi; ilovada "Oflayn" | | | | |
| 9 | Mehmon roli bilan ochish | Rad etiladi (ruxsat yo'q) | | | | |
