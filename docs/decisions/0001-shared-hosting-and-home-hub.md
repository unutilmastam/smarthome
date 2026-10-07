# 0001 — Cloud = yengil API (cPanel shared hosting), og'ir ish = uydagi Hub

- Holat: qabul qilingan
- Sana: 2026-10-07

## Kontekst
- Mavjud hosting: **hostmaster.uz cPanel shared hosting**. Bor: Setup Python App (Passenger), Setup Node.js App, PostgreSQL, SSH Access, Terminal, Cron Jobs, Git Version Control.
- Yo'q: Docker, doimiy ishlaydigan fon jarayon, ishonchli WebSocket server. Passenger jarayonlari so'rov bo'lmasa uxlab qoladi.
- Uy internet uzilganda ham ishlashi kerak (chiroq, darvoza, sug'orish, kamera yozuvi).
- Egasi kompyutersiz ishlaydi (telefon/iPad), shuning uchun murakkab server boshqaruvi qabul qilinmaydi.

## Qaror
Tizim uch zonaga bo'linadi:

1. **Cloud (cPanel)** — faqat so'rov-javob ishlari: autentifikatsiya, rollar, reyestr (uy/xona/qurilma/Hub), buyruqni qabul qilish va imzolash, agregatlangan tarix, audit, bildirishnomalar. FastAPI (ASGI) → `a2wsgi` → `passenger_wsgi.py`. Davriy ishlar — cPanel **cron** (`python -m app.jobs.<name>`).
2. **Home Hub (uyda)** — "miya": gateway-agent, lokal Mosquitto, avtomatika, Frigate, lokal API + PWA (`hub.local`), SQLite bufer. Hub faqat **tashqariga** ulanadi (HTTPS / MQTT TLS). Uy cloud'siz to'liq ishlaydi.
3. **Qurilmalar** (ESP32/ESPHome) — faqat lokal broker bilan gaplashadi; xavfsizlik chegaralari (`max_runtime`, `fail_safe_state`) proshivkada.

Kod portativ bo'ladi: backend Docker Compose profili bilan ham ishga tushadi, kelajakda VDS'ga o'tish faqat konfiguratsiya o'zgarishi.

## Ko'rib chiqilgan muqobillar
- **VPS + Docker + broker + Redis** (asl reja) — hozirgi hostingda imkonsiz; qo'shimcha xarajat va administratsiya.
- **Faqat cloud (Hub'siz)** — internet uzilsa uy boshqarilmaydi; video uchun yaroqsiz.
- **Faqat Hub (cloud'siz), port forwarding bilan** — kiruvchi port ochish taqiqlangan (CLAUDE.md, 7-qoida).
- **Home Assistant'ni asos qilish** — tez boshlash mumkin, lekin rollar/imzo/audit talablari va o'z shartnomamiz (contracts) bilan to'liq nazorat kerak. Kelajakda adapter sifatida integratsiya qilish mumkin (ochiq savol).

## Oqibatlar
### Ijobiy
- Hosting xarajati o'zgarmaydi; internet uzilishi uy ishini to'xtatmaydi.
- Kiruvchi port yo'q — hujum yuzasi kichik.
### Salbiy / xavflar
- Cloud real-time push qila olmaydi → ADR 0005 (polling, keyin managed MQTT).
- Hub — yagona nuqta: UPS, watchdog, backup majburiy (Faza 8, 14).
- Passenger "sovuq start" — birinchi so'rov sekin bo'lishi mumkin; Hub polling'i ilovani "uyg'oq" ushlab turadi (tekshirilishi kerak).
- cPanel cron minimal oralig'i (odatda 1 daqiqa) — `expire_due` kabi ishlar shunga moslashtiriladi; aniq muddat so'rov vaqtida ham tekshiriladi.

## Tasdiqlanishi kerak
- Setup Python App'dagi eng yuqori Python versiyasi (≥ 3.10 kerak) — `docs/hardware/inventory.md`, H-01.
- Passenger jarayon boshiga so'rov vaqti limiti va bir vaqtdagi jarayonlar soni.
- cPanel cron minimal oralig'i.
