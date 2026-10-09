# 0012 — Voqealar oqimi, Hub'dagi xavfsizlik tizimi va qaytar aloqa atributlari

- Holat: qabul qilingan
- Sana: 2026-10-07
- Faza 11 (darvoza, konditsioner, xavfsizlik, sug'orish).

## Kontekst
Faza 11 to'rt turdagi qurilma talab qiladi. Ularning har biri "holat"dan tashqari **voqea** ham yaratadi:
- darvoza ochiq qoldi;
- fotoelement to'sildi;
- konditsioner ta'sir qilmayapti;
- signalizatsiya ishga tushdi;
- klapan `max_runtime` da yopildi;
- suv yo'q yoki yopiq klapandan suv oqyapti.

Bularni hozirgi `state` orqali ifodalab bo'lmaydi: state oxirgi qiymatni saqlaydi, voqea esa bir martalik va tarixga ega. Xavfsizlik tizimi (armed/disarmed, kechikishlar) internet bo'lmasa ham ishlashi shart.

## Qaror
1. **Voqealar.**
   - Yangi lokal topik: `home/{key}/event` (proshivka, simulyator va Hub'ning o'zi yozadi).
   - Format: `local-mqtt.schema.json#/$defs/event`.
   - Gateway voqeani tekshiradi, unga `id` (UUID, idempotentlik uchun) qo'shadi, outbox'ga yozadi va `POST /api/v1/hub/events` ga yuboradi (`hub-events.schema.json`). Internet yo'q paytda voqealar outbox'da kutadi.
   - Backend ularni `events` jadvalida saqlaydi (180 kun) va `GET /homes/{id}/events` orqali beradi.
   - Telegram va Push'ga yetkazish — Faza 13. U shu jadvaldan foydalanadi.
2. **Xavfsizlik tizimi Hub'da.**
   - Yangi capability: `alarm`. U `adapter: "hub"` bo'lgan virtual qurilma sifatida qo'shiladi.
   - Gateway bu qurilmaning buyruqlarini MQTT'ga emas, ichki dvigatelga (`gateway/alarm.py`) beradi. Imzo, muddat, rol va PIN tekshiruvi oddiy qurilmalardagi kabi.
   - Dvigatel zonalar (gerkon/harakat datchiklari) holatini gateway'ning o'zidan oladi. Sirenani esa oddiy lokal `cmd` bilan yoqadi.
   - Holat Hub'ning SQLite'ida saqlanadi: Hub qayta yonsa ham "armed" holati saqlanib qoladi.
   - Sirenaning maksimal ishlash vaqti **siren proshivkasida** ham cheklanadi.
3. **Qaytar aloqa atributlari** (faqat qo'shiladi — expand):
   - `cover.obstructed`: fotoelement holati. Faqat ko'rsatiladi; to'xtatish darvoza blokining o'zida (apparatda) qoladi. Proshivka to'siq paytida "yopish" buyrug'ini qo'shimcha rad etadi.
   - `climate.running`: tok datchigi (CT) bo'yicha "konditsioner haqiqatan ishlayapti". Bu IR konditsioner uchun yagona haqiqiy tasdiq. `set_power` faqat shu atribut mos kelsa `confirmed` bo'ladi. Datchik bo'lmasa (`not_supported`) buyruq `acked` da qoladi, holat esa `assumed` bo'ladi.
   - `valve.open` buyrug'i qurilmada oqim datchigi bo'lsa, `open = true` **va** `flow > 0` bilan tasdiqlanadi.
4. **Capability sozlamalari shartnomada.** `capabilities.json` da har bir capability uchun ixtiyoriy `config` (JSON Schema) bo'ladi. Masalan:
   - `cover.left_open_after_s`;
   - `alarm.zones`, `alarm.sirens`, `alarm.exit_delay_s`.

   Backend qurilma sozlamalarini shu sxema bilan tekshiradi.

## Oqibatlar
- Shartnomaga yangi atributlar qo'shildi: eski qurilmalarda ular `unknown` bo'ladi. O'rnatilmagan datchiklar `unsupported` ga yoziladi va `not_supported` ko'rinadi.
- Hub'da avtomatika dvigateli (Faza 12) hali yo'q. Signalizatsiya Faza 12 ga bog'liq emas — u alohida, oddiy holatlar mashinasi.
- `[REAL]` sinovlar apparat ma'lum bo'lgach (inventar H-05, H-06, H-11, H-13) o'tkaziladi.
