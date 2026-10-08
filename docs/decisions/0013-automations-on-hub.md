# 0013 — Avtomatika Hub'da: format, xavfsizlik chegaralari, sikllar

- Holat: qabul qilingan
- Sana: 2026-10-07
- Faza 12. ARCHITECTURE 11-bo'limni aniqlashtiradi.

## Kontekst
Avtomatika internet bo'lmasa ham ishlashi kerak, shuning uchun u Hub'da bajariladi. Lekin avtomatika — odamsiz ishlaydigan buyruq. Unga cheklovlar zarur:
- noto'g'ri qoida darvozani ochmasligi kerak;
- ikkita qoida bir-birini cheksiz yoqib-o'chirmasligi kerak;
- odam qo'lda boshqarayotgan qurilmaga avtomatika aralashmasligi kerak.

## Qaror
1. **Format:** `packages/contracts/schemas/automation.schema.json`.
   - **Triggerlar:** qurilma holati (faqat qurilmadan kelgan, ya'ni `reported` qiymat; `for_s` bilan), vaqt (HH:MM, kunlar), quyosh (chiqishi yoki botishi ± daqiqa).
   - **Shartlar:** qurilma holati, vaqt oralig'i, kun yoki tun, signalizatsiya rejimi. Qiymat noma'lum yoki qurilma oflayn bo'lsa, shart **bajarilmagan** hisoblanadi — taxmin qilinmaydi.
   - **Harakatlar:** buyruq (`auto_off_after_s` — faqat `switch.turn_on` uchun), kutish, xabar (`notify`).
   - Sozlamalar: `cooldown_s` (standart 60), `max_runs_per_hour` (20), `manual_override_s` (1800).
2. **Xavf chegarasi:** `risk: high` capability'lar (darvoza, qulf, kontaktor, signalizatsiya) avtomatikada **taqiqlangan**. Bularni faqat odam PIN bilan bajaradi. `medium` (klapan) ruxsat etiladi, lekin shartnomadagi parametrlar majburiy: masalan, klapanni `duration_s` siz ochib bo'lmaydi. `max_runtime` esa baribir proshivkada.
3. **Sikllar:** backend saqlashdan oldin graf tuzadi. Agar A qoidaning harakati X qurilmaning capability'sini o'zgartirsa va B qoida shu capability holatiga qarab ishga tushsa, A → B qirra hosil bo'ladi. Sikl (o'zini o'zi ham) bo'lsa — saqlash rad etiladi (`VALIDATION_ERROR`). Ishlash vaqtida `max_runs_per_hour` ikkinchi himoya bo'lib qoladi.
4. **Bajarish:**
   - Hub qoidalarni `GET /hub/config` orqali oladi va oxirgi nusxasini saqlaydi (oflayn start).
   - Buyruqlar lokal MQTT bilan, xuddi bulut buyrug'i kabi tasdiq kutib yuboriladi: ack, so'ng holat. Bu imzosiz, chunki Hub'ning o'z qarori — xuddi sirena kabi (ADR 0012).
   - Har bir ishga tushish `automation_runs` ga yoziladi (outbox orqali, idempotent).
   - Quyosh vaqti uy koordinatalaridan Hub'da hisoblanadi (NOAA formulasi, internet kerak emas). Koordinata bo'lmasa, `sun` trigger va shartlarini backend rad etadi (H-14).
5. **Qo'lda boshqaruv:** odam ilovadan biror qurilmaga buyruq bersa, shu qurilmaga ta'sir qiluvchi avtomatika harakatlari `manual_override_s` davomida o'tkazib yuboriladi (`skipped: manual_override`).
6. **`notify`** harakati hozircha bajarilish tarixiga yoziladi. Telegram va Push'ga yetkazish Faza 13 da qo'shiladi.

## Oqibatlar
- Avtomatika darvozani ochmaydi va signalizatsiyani o'chirmaydi — bu ataylab qilingan cheklov.
- Rejadagi "notify" hozircha telefonga yetib bormaydi: bu hisobotda va UI'da ochiq aytiladi.
