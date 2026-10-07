# Apparat va muhit inventari (savollar)

- Manba: ARCHITECTURE.md, 18-bo'lim.
- Yangilangan: 2026-10-07 (Faza 0)
- Qoida: javob yo'q → **noma'lum**. Taxmin javob sifatida yozilmaydi. Javob kelganda: shu jadval yangilanadi, sana va manba (kim/qanday tasdiqladi) yoziladi.

Javob bo'lmaguncha ishlar **xavfsiz standart qiymatlar + simulyator** bilan davom etadi (ustun "Standart").

| ID | Savol | Javob | Manba / sana | Standart (javobgacha) | Qaysi faza bloklanadi |
|---|---|---|---|---|---|
| H-01a | hostmaster.uz cPanel'da qaysi xizmatlar bor? | Setup Python App, Setup Node.js App, SSH Access, Terminal, PostgreSQL, Git Version Control, Cron Jobs | ARCHITECTURE.md 18.1 (egasi tasdiqlagan) | — | — |
| H-01b | Setup Python App'dagi eng yuqori Python versiyasi (≥ 3.10 kerak) | noma'lum | — | Kod Python 3.10 bilan mos yoziladi; CI 3.10 va 3.12 da | Faza 7 (Faza 1 da emas) |
| H-01c | PostgreSQL versiyasi (≥ 12 kutilmoqda) | noma'lum | — | Versiyaga xos imkoniyatlar ishlatilmaydi (ADR 0002) | Faza 7 |
| H-01d | Domen va subdomen (`home.<domen>.uz`) | noma'lum | — | Konfiguratsiyada `PUBLIC_BASE_URL` | Faza 7 |
| H-01e | cPanel 2FA yoqilganmi; cron minimal oralig'i; DB hajmi/ulanishlar limiti | noma'lum | — | Cron ≥ 1 daq deb hisoblanadi | Faza 7 |
| H-02 | Hub: Intel N100 mini PC yoki Raspberry Pi 5? Byudjet? | noma'lum | — | Hub dasturi `amd64` va `arm64` uchun build qilinadi; simulyator | Faza 8 |
| H-03a | Kameralar soni va modeli | noma'lum | — | Frigate konfiguratsiyasi simulyatsiyasiz; kamera fazasi kutadi | Faza 10 |
| H-03b | Kameralar ONVIF/RTSP qo'llaydimi? | noma'lum | — | RTSP talab qilinadi deb hisoblanadi | Faza 10 |
| H-03c | PoE switch bormi? | noma'lum | — | — | Faza 10 |
| H-04a | Elektr: 1 faza yoki 3 faza? | noma'lum | — | Simulyatorda 1 faza PZEM | Faza 9 |
| H-04b | Nechta liniyani kuzatish kerak? | noma'lum | — | — | Faza 9 |
| H-04c | Qaysi liniyalarni masofadan o'chirish kerak (kontaktor)? | noma'lum | — | Hech qaysi liniya o'chirilmaydi | Faza 9, 11 |
| H-05 | Darvoza blokining modeli; qaysi kirishlar bor (open / close / step)? Gerkon o'rnatish mumkinmi? Fotoelement bormi? | noma'lum | — | Simulyatorda alohida open/close + gerkon; `confirmed` faqat gerkon bilan | Faza 11 |
| H-06 | Konditsionerlar modeli; IR yoki Wi-Fi moduli? Soni? | noma'lum | — | IR, holat `assumed` | Faza 11 |
| H-07 | Router modeli (OpenWrt / MikroTik — VLAN mumkinmi?) | noma'lum | — | Tekis tarmoq deb hisoblanadi (threat model T6 qolgan xavf) | Faza 8, 10 |
| H-08 | Elektr montajini kim bajaradi (malakali elektrik)? | noma'lum | — | Malakali elektrik bo'lmaguncha 220V bilan ishlaydigan `[REAL]` qadam bajarilmaydi | Faza 8, 9, 11 |

## Qo'shimcha savollar (Faza 0 ko'rib chiqishida aniqlandi)

| ID | Savol | Javob | Standart (javobgacha) | Qaysi faza |
|---|---|---|---|---|
| H-09 | UPS bormi / qaysi quvvat (≥ 600 VA tavsiya)? USB orqali NUT bilan ishlaydimi? | noma'lum | UPS holati `unknown` ko'rsatiladi | Faza 8 |
| H-10 | Internet provayderi va ulanish turi; zaxira internet (mobil modem) bormi? | noma'lum | Bitta kanal deb hisoblanadi | Faza 8 |
| H-11 | Sug'orish: nechta zona, klapan turi (24V AC?), nasos bormi, oqim datchigi o'rnatish mumkinmi? | noma'lum | Simulyatorda 1 klapan, `max_runtime` majburiy | Faza 11 |
| H-12 | Qulf(lar) bormi — model va boshqaruv turi? | noma'lum | Lock capability faqat simulyatorda | Faza 11 |
| H-13 | Mavjud xavfsizlik datchiklari / sirena bormi? | noma'lum | — | Faza 11 |
| H-14 | Uy koordinatalari va vaqt zonasi (quyosh chiqishi/botishi uchun) | Vaqt zonasi: `Asia/Tashkent` (ARCHITECTURE 0.13); koordinatalar noma'lum | Koordinatasiz `sun` sharti ishlamaydi va validatsiyada rad etiladi | Faza 12 |
| H-15 | Managed MQTT broker: EMQX Serverless / HiveMQ bepul limitlari, ACL, HTTP publish API | tekshirilmagan | Polling (ADR 0005) | Faza 5 |
| H-16 | Foydalanuvchilar: nechta oila a'zosi, mehmon kerakmi, telefon turlari (iOS versiyasi ≥ 16.4?) | noma'lum | — | Faza 6, 13 |
