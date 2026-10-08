# Elektr uzildi

## Svet o'chganda nima bo'ladi (avtomatik)
| Qism | Xatti-harakati |
|---|---|
| Hub | UPS'dan ishlaydi. UPS batareyasi kamaysa, NUT Hub'ni **to'g'ri** o'chiradi (SQLite buzilmaydi) |
| Router | UPS'ga ulangan bo'lsa ishlaydi. Bo'lmasa — Hub internetsiz qoladi. Bulut 3 daqiqada 🚨 "Hub aloqasiz" xabarini yuboradi |
| ESP32 releleri | Quvvat yo'q — hammasi o'chadi |
| Nasos, klapan | Quvvatsiz yopiladi |
| Signalizatsiya | Hub UPS'da bo'lsa ishlaydi. Zona datchiklari batareyada bo'lsa — signal beradi |

## Svet qaytganda (avtomatik)
1. Hub BIOS'dagi **"Restore on AC power loss: Power On"** tufayli o'zi yonadi. Docker konteynerlari `restart: always` bilan ko'tariladi.
2. ESP32 lar yonadi va har rele o'z `restore_mode` holatiga o'tadi:
   - standart OFF;
   - **nasos, klapan, darvoza, sirena — har doim OFF**;
   - chiroqlar sozlamaga qarab.
3. **Muddati o'tgan buyruqlar bajarilmaydi.** Svet o'chishidan oldin yuborilgan buyruq svet qaytgach o'z-o'zidan ishlab ketmaydi.
4. Signalizatsiya holati Hub'da saqlanadi. Qo'riqlash yoqilgan bo'lgan bo'lsa, **yoqilgan holicha qaytadi**: Hub qayta yonishi uyni jimgina qo'riqsiz qoldirmaydi.
5. Hub internetga ulanadi va o'chiq paytda to'plangan telemetriya va voqealarni yuboradi. Bulut ℹ️ "Hub qayta ulandi" xabarini yuboradi.

## Qo'lda tekshirish (svet qaytgandan 5 daqiqa keyin)
1. Ilovada Hub "Onlayn"mi, sariq banner yo'qmi?
2. Qurilmalar sahifasi: hammasi `online`mi? 5 daqiqadan keyin ham `offline` bo'lgan qurilma haqida ⚠️ xabar o'zi keladi.
3. Chiroqlar kerakli holatdami? Kerak bo'lsa, ilovadan yoqing.
4. Signalizatsiya holati to'g'rimi (Xavfsizlik sahifasi)?
5. UPS: `upsc ups@localhost` (Termius) → `ups.status: OL` (tarmoqdan), `battery.charge` o'syapti.

## Uzoq uzilishdan keyin
- Hub UPS tugab o'chgan bo'lsa: u svet qaytganda o'zi yonadi (BIOS). Yonmasa — quvvat tugmasini bosing va BIOS sozlamasini tekshiring.
- Bulut xabarlari tartibi: 🚨 "Hub aloqasiz" → (svet qaytganda) ℹ️ "Hub qayta ulandi". Voqealar internet qaytgandan keyin keladi, matnda **asl vaqti** ko'rsatiladi.

`[REAL]` sinov (Faza 15): UPS'ni rozetkadan uzib, NUT o'chirishini tekshirish. Hub'ni quvvatdan uzib-ulab, o'zi yonishini, relelar OFF holatda qolishini va signalizatsiya holati saqlanishini tekshirish.
