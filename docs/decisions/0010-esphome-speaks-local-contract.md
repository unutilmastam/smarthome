# 0010 — ESPHome qurilmalari lokal shartnomani to'g'ridan-to'g'ri gapiradi

- Holat: qabul qilingan
- Sana: 2026-10-07
- PHASES Faza 8 dagi "`services/hub/adapters/esphome`: ESPHome MQTT ↔ contracts" bandini almashtiradi.

## Kontekst
Faza 8 rejasida Hub'da ESPHome'ning standart MQTT topiklarini (`<prefix>/switch/<id>/state`, `.../command`) bizning shartnomaga tarjima qiluvchi adapter bor edi. Lekin:
- Standart ESPHome'da **ack** yo'q. Adapter ack'ni o'zi "yasashi" kerak bo'lardi, ya'ni ack qurilmadan emas, adapterdan kelardi. Bu "qiymat o'ylab topma" qoidasiga zid (CLAUDE.md, 1–2-qoidalar).
- Tarjimon — yana bitta harakatlanuvchi qism va yana bitta nosozlik nuqtasi.
- ESPHome'da `mqtt.on_json_message` va `mqtt.publish_json` bor. Ular bilan proshivka bizning JSON shartnomamizni o'zi gapira oladi.

## Qaror
- ESPHome konfiguratsiyalari (`devices/esphome/*.yaml`) `home/<key>/cmd` dagi buyruqni o'zi o'qiydi, **o'zi** ack yuboradi va retained `state` ga to'liq holatni yozadi. Availability — `birth/will/shutdown` xabarlari orqali.
- ESPHome'ning standart topiklari o'chirilgan (`topic_prefix: null`, `state_topic: null`, `command_topic: null`, `discovery: false`). Mosquitto ACL baribir ularga yozishni taqiqlaydi.
- Hub tomonida alohida adapter **yo'q**: gateway har qanday qurilma bilan bir xil shartnoma orqali ishlaydi.
- Xavfsizlik chegaralari (masalan, klapanning `max_runtime`) proshivkada, YAML ichida yoziladi.
- Shartnomani gapira olmaydigan tayyor qurilmalar (zavod proshivkali Wi-Fi qurilmalar, Zigbee) uchun adapter keyin, kerak bo'lganda va alohida ADR bilan qo'shiladi.

## Oqibatlar
- Ack haqiqatan proshivkadan keladi. `confirmed` esa proshivka yuborgan rele holatidan keladi.
- Har bir yangi ESPHome qurilmasi uchun YAML'da kichik lambda yoziladi; namuna — `light-relay.yaml`.
- `esphome config` faqat YAML'ni tekshiradi. Lambda (C++) xatolarini faqat `esphome compile` topadi, shuning uchun har bir qurilma YAML'i kompilyatsiya qilinishi shart.
