# [REAL] sinov: Smart Life / Tuya qurilmalari (ADR 0016)

Har bir yangi **model** uchun bir marta o'tkaziladi. Natija `docs/hardware/installed.md` ga yoziladi. Simulyatorda o'tgan sinov **[SIM]**, bu ro'yxat esa **[REAL]**.

## Wi-Fi rele (7–32V, CB2S/BK7231)
- [ ] Hub jurnalida `tuya <key> dps {...}` chiqadi, 1-DPS `true`/`false`.
- [ ] Ilovadan yoqish → rele chiqillaydi → "Tasdiqlandi".
- [ ] Rele ta'minotini uzish → ~10 s ichida "Oflayn". Buyruq yuborilsa, "failed" bo'ladi.
- [ ] 433 MHz pult bilan qo'lda yoqish → ilovada holat o'zgaradi (tasdiq qurilmadan).

## Wi-Fi avtomat (TO-Q-SY2-JWT)
- [ ] DPS xaritasi: yoqilgan = ?, A faza = ?, kWh = ?, nosozlik = ?. Standartdan farq qilsa, `connection.dps` ga yoziladi.
- [ ] Kuchlanish, tok va quvvat multimetr yoki klesh bilan solishtiriladi (±3%).
- [ ] Ilovadan o'chirish/yoqish PIN bilan, avtomatning o'z javobi bilan "Tasdiqlandi".
- [ ] Himoya (chegara pastga qo'yib, yuklama bilan) ishlaganda ilova "Himoya ishladi" deb ko'rsatadi, masofadan yoqish rad etiladi.
- [ ] Shit qopqog'i yopiq holda Wi-Fi signali yetadi.

## IR pult
- [ ] Televizor ⏻ tugmasi o'rgatiladi va ilovadan bosilganda televizor yonadi.
- [ ] Konditsioner "Sovutish 24°" tugmasi o'rgatiladi va ishlaydi.
- [ ] Hub qayta ishga tushgandan keyin o'rgatilgan tugmalar saqlanib qoladi.
