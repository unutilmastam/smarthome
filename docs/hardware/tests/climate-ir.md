# [REAL] sinov: IR konditsioner (Faza 11)

Simulyatsiya natijalari bu yerga yozilmaydi (`[SIM]` — `test_phase11.py`). CT qisqich faqat **bitta** simni o'raydi; ulashni malakali elektrik bajaradi.

Tayyorgarlik:
- [ ] Inventar H-06: brend/model → `ir-climate.yaml` dagi `climate` platformasi (coolix o'rniga).
- [ ] CT qisqich (SCT-013) o'rnatilgan bo'lsa — `running_threshold_a` tanlanadi (bo'sh turganda va ishlaganda tok o'lchanadi). Bo'lmasa — `unsupported`: `climate.running`.

| # | Sinov | Kutilgan natija | Sana | Kim | Natija | Izoh |
|---|---|---|---|---|---|---|
| 1 | Ilovadan **Yoqish** | Konditsioner yoqiladi; "Quvvat ≈ taxminiy"; CT bilan ≤ 3 daq da "Ishlayapti ✓" va buyruq "Tasdiqlandi" | | | | |
| 2 | IR LED'ni qo'l bilan to'sib **Yoqish** | Buyruq "Bajarildi (kutilmoqda)" da qoladi, "Tasdiqlandi" **bo'lmaydi**; "Ishlamayapti" | | | | |
| 3 | 2-holatdan keyin 15 daq | Voqea "Konditsioner ta'sir qilmayapti" | | | | |
| 4 | Pultdan o'chirish | "Quvvat" taxminiy holatda qoladi (IR qaytar aloqa yo'q), lekin "Ishlamayapti" (CT) — ziddiyat ko'rinib turadi | | | | |
| 5 | Harorat 24 → 22 | Pult signali; ilovada "Ke harorat 22 ≈" | | | | |
