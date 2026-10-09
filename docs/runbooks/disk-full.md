# Disk to'ldi

Ikki xil disk bor, xabarlar ham ikki xil:

| Xabar | Disk | Xavf |
|---|---|---|
| ⚠️ "Hub diski to'lmoqda: N%" (≥ 90%) | Hub tizim diski: Docker, SQLite outbox | Internet yo'q paytda to'plangan ma'lumot yo'qolishi mumkin. Broker va gateway yiqilishi mumkin |
| ⚠️ "Kamera yozuvlari diski N% to'ldi" (≥ 85%) | Kamera HDD'si (`/mnt/nvr`) | Frigate eski yozuvlarni o'zi o'chiradi. Xabar — saqlash muddati diskka sig'mayotganining belgisi |

Ikkalasi ham 2 daqiqadan uzoq davom etsa yuboriladi. Joy bo'shagach, "yana joy bor" xabari keladi.

## Hub tizim diski (Termius → `hubadmin@hub`)
```
df -h /                                      # qancha band
sudo du -xh /var/lib/docker --max-depth=1 | sort -h | tail
docker system df                             # image, konteyner, volume
```
Xavfsiz tozalash (ma'lumotga tegmaydi):
```
docker image prune -af                       # ishlatilmayotgan eski image'lar (yangilanishlardan qolgan)
docker builder prune -af                     # build keshi
sudo journalctl --vacuum-size=200M           # tizim log'lari
sudo apt-get clean
```
Docker log'lari Faza 14 dan beri har servis uchun 3 × 10 MB bilan cheklangan (`docker-compose.yml` → `x-logging`). Ular endi diskni to'ldira olmaydi.

**O'chirmang:**
- `hub-data` volume'ini (outbox, bajarilgan buyruqlar ro'yxati) — uni o'chirish replay himoyasini ham o'chiradi;
- `mosquitto-data` ni.

Bular odatda bir necha MB bo'ladi. Katta bo'lsa — Hub uzoq vaqt internetsiz qolgan. Internet qaytganda outbox o'zi bo'shaydi (Hub sahifasida: "Yuborilishi kutilayotganlar").

## Kamera HDD'si
```
df -h /mnt/nvr
```
Frigate'da (`http://hub.local:8971` → Settings → Recording) saqlash kunlarini kamaytiring: `record.retain.days` (`services/hub/frigate/config.yml`). Keyin `docker compose restart frigate`. Yozuvlar **hech qachon bulutga ko'chirilmaydi** (ADR 0006). Ko'proq joy kerak bo'lsa, kattaroq HDD qo'yiladi.

## Bulut (hostmaster.uz) kvotasi
cPanel → bosh sahifa → **Disk Usage**. Odatda eng kattalari:
- `~/sh-deploy/daily` (kunlik dump, 14 kun);
- `~/sh-deploy/backups` (oxirgi 10 ta deploy dumpi va `pre-restore-*`).

Eski `pre-restore-*` fayllarini File Manager'dan qo'lda o'chirish mumkin. Kunlik dumplar 14 kundan keyin o'zi o'chadi. Baza ichida voqealar 180 kun, telemetriya 30 kun / 2 yil saqlanadi (retention cron).
