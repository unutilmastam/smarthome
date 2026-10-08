# Lokal MQTT broker ishlamayapti

**Qanday bilasiz:**
- ⚠️ **"Uydagi MQTT broker ishlamayapti — qurilmalarga buyruq yetmaydi"** xabari keladi. Hub buni har heartbeat'da (30 s) xabar qiladi. Xabar muammo 2 daqiqadan uzoq davom etsa yuboriladi: broker'ning qisqa qayta yuklanishi xabar emas.
- Ilova → Hub sahifasi: "Lokal MQTT broker: **Ishlamayapti**".

**Bu paytda:**
- Hub bulut bilan bog'langan, lekin qurilmalar bilan emas. Buyruqlar `failed: device_offline` bilan tugaydi. Hech narsa "bajarildi" deb ko'rsatilmaydi.
- ESP32 lar o'z xavfsiz holatida qoladi. Broker 15 daqiqa qaytmasa, ular qayta yuklanadi (rele OFF).
- Signalizatsiya zonalari haqida yangi ma'lumot kelmaydi.

## Qadamlar (Termius → `hubadmin@hub`)
```
cd ~/smarthome/services/hub
docker compose ps mosquitto
docker compose logs --tail 50 mosquitto
```
| Log'da | Sabab | Nima qilish kerak |
|---|---|---|
| `Error: Unable to open pwfile` | `mosquitto/passwd` yo'q yoki buzilgan | `sh mosquitto/make-passwd.sh <qurilma kalitlari>`, keyin `docker compose restart mosquitto` |
| `Address not available` / `Cannot assign requested address` | `HUB_LAN_IP` noto'g'ri: router Hub'ga boshqa IP bergan | Router'da DHCP reservation'ni tekshiring, `.env` dagi `HUB_LAN_IP` ni to'g'rilang, `docker compose up -d` |
| `No space left on device` | Disk to'lgan | [disk-full.md](disk-full.md) |
| Konteyner yo'q yoki "Exited" | — | `docker compose up -d mosquitto` |

Tekshirish: `docker compose logs --tail 20 gateway` da `local mqtt connected` chiqishi kerak. Bir daqiqadan keyin ℹ️ "MQTT broker tiklandi" xabari keladi.

Qurilma ulanmayotgan bo'lsa (broker ishlayapti, lekin bitta ESP32 `offline`): `docker compose logs mosquitto | grep <qurilma_kaliti>` ni tekshiring. `not authorised` chiqsa, parol mos emas: `secrets.yaml` va `passwd` bir xil bo'lishi kerak.
