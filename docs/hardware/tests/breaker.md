# [REAL] sinov: Elektr shitidagi avtomatlar (ADR 0015)

Natijalar shu jadvalga yoziladi: sana, kim sinadi, natija (✓ yoki ✗), izoh. Simulyatsiyadagi natija bu yerga **yozilmaydi** (u `services/hub/tests/test_breaker.py` da, `[SIM]`).
Shit ichidagi barcha ishlarni **faqat malakali elektrik**, kuchlanish o'chirilgan holda bajaradi.

Tayyorgarlik:
- [ ] Avtomat modeli tanlandi: motor operatori (masofadan yoqish/o'chirish), OF (holat) va SD (himoya) kontaktlari bor. SD yo'q bo'lsa, ilovada `unsupported: ["breaker.tripped"]`.
- [ ] `devices/esphome/circuit-breaker.yaml`: pinlar, `device_key`, `pulse_ms` (operator hujjatiga ko'ra).
- [ ] Ilovada: Qo'shish → "Avtomat (shit)"; nomi (masalan "Oshxona"), shit, raqam (yorliqdagi bilan bir xil), C16.

| # | Sinov | Kutilgan natija | Sana | Kim | Natija | Izoh |
|---|---|---|---|---|---|---|
| 1 | Ilovada avtomat richagini pastga bosish (PIN) | Avtomat o'chadi; OF kontakt → "O'chirilgan", buyruq "Tasdiqlandi"; liniyadagi rozetkada tok yo'q (tester bilan) | | | | |
| 2 | Richagni yuqoriga bosish (PIN) | Avtomat yoqiladi, "Yoqilgan ✓", liniyada tok bor | | | | |
| 3 | PIN'siz yoki noto'g'ri PIN | Buyruq yuborilmaydi | | | | |
| 4 | Himoyani tekshirish: avtomatdagi TEST tugmasi (RCBO) yoki elektrik usuli bilan trip | Ilovada qizil "Himoya ishladi"; Telegram'ga 🚨 "Avtomat himoyasi ishladi" | | | | |
| 5 | Trip holatida ilovadan yoqish | Rad etiladi: "xavfsizlik qoidasi"; voqea "masofadan yoqilmadi" | | | | |
| 6 | Joyida qo'lda tiklash, so'ng ilovadan yoqish | Yoqiladi, "Tasdiqlandi" | | | | |
| 7 | OF kontakt simini uzib, o'chirish buyrug'i | "Muvaffaqiyatsiz (no_feedback)" — "bajarildi" deb **ko'rsatilmaydi** | | | | |
| 8 | ESP32 tokini uzish va qayta ulash | Avtomat o'z holatini saqlaydi, hech qanday impuls yo'q | | | | |
| 9 | Oila a'zosi (family) roli bilan richag | Ruxsat yo'q (faqat egasi/admin: `control_power`) | | | | |
| 10 | Ilovada shit ko'rinishi | Avtomatlar yorliqdagi raqam tartibida, haqiqiy shit bilan bir xil | | | | |
