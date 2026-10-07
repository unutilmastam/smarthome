# Progress

Har bir faza tugagach shu yerga hisobot qo'shiladi (shablon: `docs/PHASES.md`).
Belgilar: `[SIM]` — simulyatsiyada, `[REAL]` — haqiqiy apparatda sinalgan.

| Faza | Nomi | Holat |
|---|---|---|
| 0 | Tayyorgarlik (hujjatlar) | tugadi |
| 1 | Poydevor (monorepo, contracts, CI) | boshlanmagan |

---

## Faza 0 — Tayyorgarlik (hujjatlar) — 2026-10-07
Holat: tugadi

Qilingan ishlar:
- 6 ta ADR yozildi (0001–0006) va ADR indeksi/shabloni.
- Tahdid modeli: 12 aktiv, 6 turdagi hujumchi, 15 tahdid (har biriga himoya, qolgan xavf, qaysi fazada amalga oshiriladi), ishonch chegaralari, ochiq savollar.
- Apparat inventari: ARCHITECTURE 18-bo'limdagi 8 savol (kichik savollarga bo'lingan) + ko'rib chiqishda aniqlangan 8 qo'shimcha savol. Har biri uchun "javobgacha standart" va bloklanadigan faza.
- Hujjatlar o'zaro tekshirildi; aniq nomuvofiqliklar ARCHITECTURE.md da tuzatildi (pastga qarang).

Yaratilgan/o'zgartirilgan fayllar:
- `docs/decisions/README.md` (yangi)
- `docs/decisions/0001-shared-hosting-and-home-hub.md` (yangi)
- `docs/decisions/0002-postgresql.md` (yangi)
- `docs/decisions/0003-single-pwa.md` (yangi)
- `docs/decisions/0004-command-signing-hmac.md` (yangi)
- `docs/decisions/0005-polling-first-mqtt-later.md` (yangi)
- `docs/decisions/0006-video-stays-home.md` (yangi)
- `docs/threat-model.md` (yangi)
- `docs/hardware/inventory.md` (yangi)
- `docs/PROGRESS.md` (yangi)
- `ARCHITECTURE.md` (nomuvofiqliklar tuzatildi)
- `docs/PHASES.md` (Faza 0 vazifalari belgilandi)

ARCHITECTURE.md dagi tuzatishlar:
1. 3-bo'lim: "Python 3.11+" → "Python 3.10+ (3.10 bilan mos)" — CLAUDE.md va PHASES.md bilan zid edi.
2. 4.1-bo'lim: `contactor` capability ro'yxatga qo'shildi (`capabilities.json` da bor edi, ro'yxatda yo'q edi).
3. 8-bo'lim: xato kodlariga `HUB_UNREACHABLE` qo'shildi (PHASES.md Faza 3 da ishlatiladi).
4. 12-bo'lim: "Cloud broker yo'q" qatori ADR 0005 ga moslandi — broker yo'q bo'lsa polling davom etadi; ikkalasi ham ishlamasa `503 HUB_UNREACHABLE`.
5. 13-bo'lim: eskirgan `home_secret` atamasi `hub_token` + `signing_key_hex` (4.4-bo'lim) bilan almashtirildi.

Testlar: kod yo'q — testlar mavjud emas (Faza 0 tugash mezoni: "hujjatlar bor, kod yo'q"). Faqat `docs/spec/capabilities.json` JSON sifatida o'qilishi tekshirildi: `python3 -c "import json; json.load(open('docs/spec/capabilities.json'))"` → xatosiz.

Hal qilinmagan xavflar:
- Hosting cheklovlari (Python/PostgreSQL versiyasi, cron oralig'i, so'rovlar limiti) tasdiqlanmagan — 1 s polling hosting limitlariga sig'ishi noma'lum (ADR 0005).
- `http://hub.local` — secure context emas: lokal rejimda Service Worker/Push ishlamasligi mumkin (ADR 0003).
- Internetsiz lokal autentifikatsiya dizayni yo'q (ADR 0004, threat model).
- Router VLAN qo'llashi noma'lum — tarmoq tekis bo'lishi mumkin (T6).
- Hub disk shifrlash va avtomatik yuklanish ziddiyati (T9).

Tasdiqlanmagan taxminlar:
- `docs/hardware/inventory.md` dagi barcha "noma'lum" qatorlar (H-01b…H-16) — hammasi egasidan javob kutadi.
- Hosting PostgreSQL ≥ 12 va Python ≥ 3.10 deb hisoblanmoqda.
- Managed MQTT bepul limitlari uy uchun yetarli deb hisoblanmoqda (Faza 5 da tekshiriladi).

Keyingi faza: 1 — Poydevor (monorepo, contracts, CI). Faza 1 inventar javoblarisiz boshlanishi mumkin.
