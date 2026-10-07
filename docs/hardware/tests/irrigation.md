# [REAL] sinov: Sug'orish klapani (Faza 11)

Simulyatsiya natijalari bu yerga yozilmaydi. **ARCHITECTURE 17: "Nasos/klapan internet uzilsa ham `max_runtime` da o'chadi (sinaldi)" — shu sinov bilan belgilanadi.**

Tayyorgarlik:
- [ ] Inventar H-11: zonalar soni, klapan (24 V AC?), nasos, oqim datchigi.
- [ ] `irrigation-valve.yaml`: `max_runtime_s` = bulutdagi `max_runtime_s` (yoki kichikroq), `no_flow_s`, oqim datchigi koeffitsienti.

| # | Sinov | Kutilgan natija | Sana | Kim | Natija | Izoh |
|---|---|---|---|---|---|---|
| 1 | Ilovadan 2 daqiqaga **Ochish** | Suv oqadi; "Ochiq ✓", oqim > 0; buyruq "Tasdiqlandi"; 2 daq dan keyin o'zi yopiladi | | | | |
| 2 | **Internetni uzib**, `max_runtime_s` dan uzoqroq ochish (oldindan yuborilgan buyruq) | Klapan `max_runtime_s` da **o'zi** yopiladi; voqea internet qaytgach keladi | | | | |
| 3 | Hub'ni o'chirib qo'yish (klapan ochiq) | Klapan baribir vaqtida yopiladi | | | | |
| 4 | Suv kranini yopib **Ochish** | Buyruq "Muvaffaqiyatsiz (no_feedback)"; 30 s da klapan yopiladi; voqea "Suv kelmayapti" | | | | |
| 5 | Favqulodda tugmani bosish (klapan ochiq) | Darhol yopiladi; voqea "Favqulodda tugma bosildi" | | | | |
| 6 | Ilovada **Hammasini to'xtatish** | Ochiq barcha klapanlar yopiladi | | | | |
| 7 | ESP32 tokini uzib qayta ulash (klapan ochiq edi) | Qayta yoqilganda klapan **YOPIQ** | | | | |
| 8 | Yopiq klapan oldidan suv oqizish (sinov uchun) | Voqea "Yopiq klapandan suv oqyapti!" (muhim) | | | | |
