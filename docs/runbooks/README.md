# Runbook'lar

Nosozlik va texnik xizmat ko'rsatmalari. Hammasi iPad'dan bajariladi: cPanel → Terminal yoki File Manager, Hub'ga esa Termius + Tailscale orqali.

| Hodisa | Runbook | Qanday bilasiz |
|---|---|---|
| Deploy, Secrets, birinchi o'rnatish | [deploy.md](deploy.md) | — |
| Hub o'chdi yoki aloqa yo'q | [hub-down.md](hub-down.md) | 🚨 "Hub aloqasiz" (3 daqiqa ichida) |
| Lokal MQTT broker ishlamayapti | [broker-down.md](broker-down.md) | ⚠️ "MQTT broker ishlamayapti" |
| Disk to'ldi (Hub, kamera HDD, bulut) | [disk-full.md](disk-full.md) | ⚠️ "Hub diski to'lmoqda" / "Kamera yozuvlari diski" |
| Token yoki kalit o'g'irlandi | [token-stolen.md](token-stolen.md) | — |
| Elektr uzildi | [power-outage.md](power-outage.md) | 🚨 "Hub aloqasiz" (router UPS'siz bo'lsa) |
| Zaxira va tiklash | [backup-restore.md](backup-restore.md) | — |
| Xavfsizlik tekshiruvi (skanlar, tashqi port) | [security-audit.md](security-audit.md) | CI'dagi `security` job'i |
