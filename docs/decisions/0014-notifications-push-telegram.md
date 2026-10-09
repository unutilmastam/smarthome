# 0014 — Bildirishnomalar: Web Push + Telegram, tasdiqlash, Hub nazoratchisi

- Holat: qabul qilingan
- Sana: 2026-10-08
- Faza 13. ARCHITECTURE 5 (Bildirishnoma), 7 (jadvallar), 8 (API), 12 (offline stsenariylar) ni aniqlashtiradi.

## Kontekst
Uyda nimadir bo'lsa (signal, suv oqishi, darvoza ochiq qoldi, Hub o'chdi), egasi telefonida darhol bilishi kerak. Cheklovlar:
- Cloud — cPanel shared hosting: doimiy fon jarayon va WebSocket yo'q, faqat Passenger so'rovlari va har daqiqalik cron.
- iOS'da Web Push faqat Bosh ekranga o'rnatilgan PWA'da ishlaydi va ba'zan kechikadi. Shuning uchun Telegram — zaxira, eng ishonchli kanal (ARCHITECTURE 1, 12-qator).
- Sir kodga yozilmaydi. Uyda port ochilmaydi.

## Qaror
1. **Bildirishnoma manbalari** (`notifications` jadvali, 180 kun):
   - Hub'dan kelgan **voqealar** (ADR 0012). Har bir yangi voqea bildirishnomaga aylanadi, jiddiylik shartnomadan olinadi. `dedupe_key = event:<id>` — qayta yuborilgan paket ikki marta xabar bermaydi.
   - Avtomatikadagi **`notify` harakati** (ADR 0013). Bajarilish tarixi kelganda yaratiladi: `run:<id>:<n>`.
   - **Nazoratchi (watchdog) cron**, har daqiqa:
     - Hub `last_seen` 150 s dan eski bo'lsa → **kritik** "Hub aloqasiz". Cron har daqiqada ishlaydi, shuning uchun Hub o'chganidan keyin ko'pi bilan 3 daqiqada aniqlanadi.
     - Hub qaytsa → "Hub qaytdi". Bu xabar "aloqasiz" xabarini olgan odamlarga yuboriladi.
     - Qurilma 5 daqiqadan beri `offline` bo'lsa → ogohlantirish, qaytganda — xabar. Hub o'zi aloqasiz bo'lsa, qurilmalar haqida alohida xabar berilmaydi: sabab bitta, xabar ham bitta.
     - Bu holatlar `hubs.offline_notified_at` va `devices.offline_notified_at` bilan belgilanadi, shuning uchun xabar takrorlanmaydi.
   - **Sinov xabari** — faqat so'ragan odamning o'ziga.
2. **Kimga:** uyning `owner`, `admin` va `family` a'zolariga, agar xabar jiddiyligi a'zoning `notify_min_severity` qiymatidan (standart `warning`) past bo'lmasa. Kritik xabar har doim yuboriladi. `guest` va `viewer` olmaydi.
3. **Kanallar** (`notification_deliveries`: har bir odam × kanal uchun bitta yozuv):
   - **Telegram Bot API.** Bot GitHub Secrets'dagi `TELEGRAM_BOT_TOKEN` bilan ishlaydi (deploy xabarlari ham shu botdan). Deploy bu tokenni faqat serverdagi `.env` ga yozadi.
     - Webhook: `POST /api/v1/telegram/webhook`. U `X-Telegram-Bot-Api-Secret-Token` sarlavhasi bilan tekshiriladi; bu sir deploy paytida serverda yaratiladi. Kiruvchi so'rov uyga emas, cloud'ga keladi, shuning uchun uyda port ochilmaydi.
     - Bog'lash: ilova 8 belgili kod beradi (10 daqiqa, bir martalik, bazada faqat SHA-256 xeshi). Foydalanuvchi `t.me/<bot>?start=KOD` ni ochadi va chat foydalanuvchiga bog'lanadi. Faqat shaxsiy chat qabul qilinadi. `/stop` bog'lanishni uzadi.
     - Har bir xabarda "✅ Ko'rdim" tugmasi bor. U ilovadagi tasdiqlash bilan bir xil ishlaydi.
   - **Web Push (VAPID, RFC 8291 aes128gcm + RFC 8292).** Shifrlash `cryptography` bilan o'zimizda yozilgan (RFC 8291 test vektori bilan tekshirilgan); qo'shimcha kutubxona yo'q. VAPID kaliti deploy paytida serverda yaratiladi va `.env` da turadi.
     - Service worker xabarni ko'rsatadi. "Ko'rdim" tugmasi bildirishnoma × foydalanuvchi uchun HMAC-token bilan tasdiqlaydi, chunki SW'da access token yo'q (ADR 0009).
     - 404/410 javobi kelsa, obuna o'chiriladi.
4. **Yetkazish:**
   - Hub so'rovi ichida darhol urinib ko'riladi: faqat `warning` va `critical`, umumiy vaqt 5 s gacha. Qolgani, xato bo'lganlari va qayta urinishlar `app.jobs.notify` cron'ida (har daqiqa).
   - Yozuv yuborishdan oldin `pending → sending` holatiga shartli `UPDATE` bilan "egallanadi". Shu sababli so'rov va cron bir xabarni ikki marta yubormaydi; 5 daqiqa osilib qolgan `sending` qayta `pending` bo'ladi.
   - Qayta urinish: 1, 2, 4, 8 daqiqa; 5 urinishdan keyin `failed`.
   - Telegram 403 (bot bloklangan) → bog'lanish o'chiriladi.
5. **Tasdiqlash (ack):** ilovada (`POST /notifications/{id}/ack`), Telegram tugmasi yoki Push tugmasi orqali; `acked_by`, `acked_at` yoziladi. Kritik xabar 10 daqiqada tasdiqlanmasa, **bir marta** qayta yuboriladi ("Eslatma"). Tasdiqlangan xabar qayta yuborilmaydi.
6. **Matn** backend'da o'zbekcha yaratiladi (Telegram va Push uchun). Ilova esa `kind` + `data` bo'yicha o'z i18n kalitlarini ishlatadi. Voqea qancha kechikib kelgan bo'lsa ham, matnda **voqea vaqti** (uy vaqt zonasida) ko'rsatiladi.

## Ko'rib chiqilgan muqobillar
- **Telegram `getUpdates` (cron polling):** "Ko'rdim" tugmasiga javob 1 daqiqagacha kechikadi. Webhook — bir zumda.
- **`pywebpush`:** `requests`, `aiohttp`, `py-vapid` kabi og'ir bog'liqliklar keltiradi. Shifrlash 60 qatorga sig'adi va RFC vektori bilan tekshiriladi.
- **Faqat cron orqali yuborish:** signal 60 s gacha kechikadi. Shuning uchun kritik xabar darhol yuboriladi.

## Oqibatlar
### Ijobiy
- Internet va Hub bor ekan, signal soniyalarda Telegram'ga yetadi. Hub o'chsa ham, cloud buni 3 daqiqa ichida aytadi.
- Barcha sirlar (`TELEGRAM_BOT_TOKEN`, webhook siri, VAPID kaliti) faqat serverdagi `.env` da turadi.
### Salbiy / xavflar
- Uyda internet o'chsa, voqealar xabari internet qaytganda keladi. Matnda asl vaqt ko'rsatiladi.
- iOS Push faqat o'rnatilgan PWA'da ishlaydi (iOS 16.4+). Buni UI ochiq aytadi.
- Telegram yoki push-servis ishlamay qolsa, 5 urinishdan keyin `failed` bo'ladi. Ilovadagi ro'yxat baribir to'liq qoladi.

## Tasdiqlanishi kerak
- [REAL] Haqiqiy bot va telefon bilan: bog'lash, kritik xabar, "Ko'rdim" tugmasi, iPhone'da o'rnatilgan PWA'ga Push.
