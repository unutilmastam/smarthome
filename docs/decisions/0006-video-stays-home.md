# 0006 — Video uydan chiqmaydi

- Holat: qabul qilingan
- Sana: 2026-10-07

## Kontekst
- Kamera video — eng sezgir ma'lumot (oila hayoti, uy rejasi, kirish vaqtlari).
- Shared hosting video relay/saqlash uchun yaroqsiz (trafik, disk, CPU) va uchinchi tomon serverida turadi.
- Kamera yozuvi internet uzilganda ham davom etishi kerak.

## Qaror
- Video **hech qachon** cloud'ga yozilmaydi: na DB, na hosting fayllari, na zaxira, na log. Snapshot va kesilgan klip ham video hisoblanadi.
- Yozuv va aniqlash — Hub'da **Frigate + go2rtc**, surveillance HDD'da, retention bilan.
- Masofadan ko'rish — **Tailscale** orqali to'g'ridan-to'g'ri Hub'ga (WebRTC). Cloud faqat ruxsatni tekshiradi va lokal/Tailscale URL qaytaradi (`GET /cameras/{id}/access`).
- Cloud'da faqat metadata: kamera nomi, ID, `frigate_name`, xona, holat (`stream_available`, `recording`, `disk_usage_pct`), ruxsatlar.
- Kameralar alohida VLAN'da, internetga chiqishi bloklangan; RTSP portlari tashqariga ochilmaydi.
- Bildirishnomalar (Telegram, Push) matnli: "Bog'da harakat aniqlandi" — rasm qo'shilmaydi. Rasm kerak bo'lsa havola Tailscale ichidagi Frigate'ga.

## Ko'rib chiqilgan muqobillar
- **Cloud relay / NVR-as-a-service** — maxfiylik va hosting imkoniyatlari bo'yicha rad etildi.
- **Kamera ishlab chiqaruvchi cloud'i (Hik-Connect, Ezviz)** — video uchinchi tomonga ketadi; kameralar internetdan uziladi.
- **Telegram'ga snapshot** — qulay, lekin video Telegram serverlarida qoladi. Rad etildi; egasi xohlasa kelajakda alohida ADR va aniq rozilik bilan.

## Oqibatlar
### Ijobiy
- Cloud sizishi videoni oshkor qilmaydi; internet uzilishi yozuvni to'xtatmaydi.
### Salbiy / xavflar
- Masofadan ko'rish uchun telefonda Tailscale ilovasi kerak.
- Hub/HDD o'g'irlansa yoki yonsa — yozuv yo'qoladi. Yechim (ixtiyoriy): uy ichidagi ikkinchi disk yoki shifrlangan lokal NAS; cloud emas.
- Qabul testi (Faza 10): cloud DB va hosting fayllarida video/rasm yo'qligi skript bilan tekshiriladi.
