# 0015 — Elektr shiti: masofadan boshqariladigan avtomatlar

- Holat: qabul qilingan
- Sana: 2026-10-08
- Egasining so'rovi: "Elektr bo'limida avtomatlarni yoqib-o'chiradigan joy bo'lsin. Shitda 10–20 ta Wi-Fi avtomat bor, har biriga nom beriladi (1 — Oshxona) va ular haqiqiy shitga o'xshab yonma-yon terilib boradi."

## Kontekst
Mavjud `contactor` capability'si liniya kontaktori uchun, avtomat uchun emas. Avtomatda kontaktorda bo'lmagan holat bor — **himoya ishlashi (trip)**. Bunda avtomat qisqa tutashuv, ortiqcha yuklama yoki tok sizishi sababli o'zi o'chadi. Bu "o'chirilgan" holatdan boshqa narsa: liniyada nosozlik bor bo'lishi mumkin.

## Qaror
1. **Yangi capability `breaker`** (`packages/contracts/capabilities.json`):
   - `closed` — kontaktlar holati, avtomatning o'z kontaktidan (OF). **Faqat shu buyruqni tasdiqlaydi** (`confirm_attribute`).
   - `tripped` — himoya ishlagan (SD kontakt).
   - Harakatlar: `close` (yoqish) va `open` (o'chirish).
   - Voqealar: `breaker.tripped` (critical) va `breaker.close_refused` (warning).
   - Sozlamalar (`config`): `panel` (shit nomi), `position` (yorliqdagi raqam, 1–99), `rating_a` (6–63 A), `curve` (B/C/D), `poles` (1–4, shitdagi modul kengligi).
2. **Xavf darajasi: `high`, ruxsat: `control_power`.**
   - Liniyani o'chirish muzlatgich, qozon yoki signalizatsiyani tokdan uzadi.
   - Liniyani yoqish — liniyada odam ishlayotgan bo'lsa — hayot uchun xavfli.
   - Shuning uchun har bir yoqish va o'chirish **PIN** bilan bo'ladi. Avtomatika bu harakatlarni bajara olmaydi (ADR 0013, high-risk taqiqi).
3. **Proshivka himoyasi** (`devices/esphome/circuit-breaker.yaml`, CLAUDE.md 6-qoida):
   - Himoya ishlagan avtomat masofadan **yoqilmaydi**: `rejected` / `safety_rule` va voqea `close_refused` yuboriladi. Nosozlik avval joyida topiladi va avtomat qo'lda tiklanadi.
   - `tripped` holati noma'lum bo'lsa ham avtomat yoqilmaydi: "ko'r-ko'rona" yoqish yo'q.
   - Elektr qaytganda ESP32 hech qanday impuls bermaydi, avtomat o'z holatida qoladi.
4. **Ilova ko'rinishi** (Elektr bo'limi):
   - Shit — DIN reykali quti. Avtomatlar `position` bo'yicha chapdan o'ngga teriladi. Kengligi `poles` ga teng, qator to'lsa keyingi reykaga o'tadi.
   - Har bir modulda: yorliq raqami, richag (yuqori — yoqilgan, pastki — o'chirilgan), indikator, `C16` belgisi va nom.
   - Avtomatda hisoblagich ham bo'lsa (`power_meter` capability), modulda quvvat ko'rsatiladi.
   - Holat noma'lum bo'lsa, richag **o'rtada** va "?" belgisi bilan turadi. Holat taxmin qilinmaydi.
   - `tripped` bo'lsa, modul qizil rangda "Himoya ishladi" deb ko'rsatiladi va richagni yoqib bo'lmaydi.
   - Bir nechta shit (`panel` nomi) bo'lsa, har biri alohida chiziladi. Oxirida "+" bo'sh joy bor: yangi avtomat keyingi bo'sh raqam bilan qo'shiladi.
   - Bir xil raqam takrorlansa, ilova buni ko'rsatadi, lekin taqiqlamaydi.

## Ko'rib chiqilgan muqobillar
- **`switch` capability'si bilan avtomat:** trip holatini ifodalab bo'lmaydi va xavf darajasi past bo'lib qoladi — rad etildi.
- **Avtomat holatini alohida jadvalda saqlash (DB ustunlari):** `config` allaqachon har bir capability uchun shartnoma bilan tekshiriladi. Yangi migratsiya kerak emas.

## Oqibatlar
- Har bir avtomat — alohida qurilma: o'z kaliti, tarixi, bildirishnomasi bor. Himoya ishlaganda 🚨 xabar Telegram/Push'ga keladi (ADR 0014).
- Har bir bosish PIN talab qiladi. Bu ataylab: shitni bitta xato teginish bilan o'chirib bo'lmaydi.

## Tasdiqlanishi kerak `[REAL]`
- Avtomat modeli (inventar): motor operatori, OF va SD kontaktlari bo'lishi kerak. Tuya Wi-Fi avtomatlarining ko'pchiligida SD kontakt yo'q. Bunday avtomatda `breaker.tripped` qurilmaning `unsupported` ro'yxatiga yoziladi va ilova "qo'llab-quvvatlanmaydi" deb ko'rsatadi. **Proshivka esa trip holatini bilmay turib avtomatni yoqmaydi**.
- `docs/hardware/tests/breaker.md` jadvali.
