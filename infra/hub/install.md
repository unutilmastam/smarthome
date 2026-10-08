# Home Hub o'rnatish (Ubuntu Server 24.04)

Apparat: N100 mini PC yoki Raspberry Pi 5 (H-02) + UPS (≥ 600 VA, H-09) + surveillance HDD (kameralar uchun, Faza 10).
**Hub, router, PoE switch va kameralar UPS'ga ulanadi** (ARCHITECTURE 0.6).

## 1. OS (kompyutersiz)
Ikki yo'l bor:
- **A (oson):** Ubuntu oldindan o'rnatilgan mini PC sotib olish.
- **B:** Android telefonda **EtchDroid** bilan `ubuntu-24.04-live-server-amd64.iso` ni USB flesh'ga yozish (Pi 5 uchun: Raspberry Pi Imager → Ubuntu Server 24.04). Monitor va klaviatura bir marta, o'rnatish paytida kerak bo'ladi.

O'rnatish paytida:
- hostname: `hub`;
- foydalanuvchi: `hubadmin`;
- **OpenSSH server**: yoqilsin, faqat kalit bilan kirish (parolni keyin o'chiramiz);
- disk: butun disk, LUKS **yo'q**. Sabab: svet qaytganda Hub o'zi yuklanishi kerak. Bu threat model T9 dagi ochiq savol.

## 2. Tarmoq
- Router'da Hub uchun **DHCP reservation** (doimiy IP) qiling, masalan `192.168.1.10`.
- `hub.local` nomi uchun: `sudo apt install -y avahi-daemon`.
- Router'da **port forwarding YO'Q**, UPnP o'chirilgan bo'lsin (ARCHITECTURE 13).
- Router VLAN qo'llasa (H-07): IoT va kameralar alohida VLAN'ga, kameralarning internetga chiqishi yopiladi.

## 3. Asosiy dasturlar
```
sudo apt update && sudo apt -y full-upgrade
sudo apt install -y docker.io docker-compose-v2 git mosquitto-clients nut unattended-upgrades ufw
sudo usermod -aG docker hubadmin
sudo timedatectl set-ntp true      # NTP; Hub ichida vaqt UTC
sudo timedatectl set-timezone UTC
```

## 4. Firewall (faqat LAN va Tailscale)
```
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.1.0/24 to any port 1883 proto tcp   # mosquitto (ESP32)
sudo ufw allow from 192.168.1.0/24 to any port 6052 proto tcp   # ESPHome dashboard
sudo ufw allow in on tailscale0
sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp
sudo ufw enable
```
LAN tarmog'i boshqacha bo'lsa (`192.168.1.0/24`), o'zingiznikini yozing.

> **Muhim (Faza 14):** Docker o'zi e'lon qilgan portlarga (`ports:`) ufw qoidalarini **chetlab** kirish ochadi. Shuning uchun `docker-compose.yml` dagi har bir port aniq manzilga bog'langan: `HUB_LAN_IP` (LAN) va `HUB_TAILNET_IP` (Tailscale). Bu manzillar `.env` da yoziladi (7-qadam). `0.0.0.0` va IPv6 manzilda hech narsa tinglamaydi. Buni `tests/test_exposure.py` testi tekshiradi.

## 5. Tailscale (masofaviy kirish, port ochmasdan)
```
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
```
Telefon va iPad'ga Tailscale ilovasini o'rnating. Tailscale admin → **ACL**: Hub'ga faqat sizning qurilmalaringiz kira oladi.
iPad'dan SSH: Termius → `hubadmin@hub` (Tailscale nomi).
Shundan keyin `/etc/ssh/sshd_config` da `PasswordAuthentication no` qiling va `sudo systemctl restart ssh`.

## 6. UPS (NUT)
UPS'ni USB bilan ulang:
```
sudo nut-scanner -U            # topilgan UPS'ni /etc/nut/ups.conf ga yozing
echo "MODE=standalone" | sudo tee /etc/nut/nut.conf
sudo systemctl enable --now nut-server nut-monitor
upsc ups@localhost             # battery.charge, ups.status (OL = tarmoqdan, OB = batareyadan)
```
Batareya kam bo'lganda NUT Hub'ni to'g'ri o'chiradi (`/etc/nut/upsmon.conf`: `SHUTDOWNCMD "/sbin/shutdown -h +0"`).
Svet qaytganda avtomatik yoqilishi uchun BIOS'da **"Restore on AC power loss: Power On"** qo'ying.

## 7. SmartHome stack
```
git clone https://github.com/unutilmastam/smarthome.git ~/smarthome
cd ~/smarthome/services/hub
cp .env.example .env && nano .env      # BACKEND_URL, HUB_TOKEN, SIGNING_KEY_HEX, MQTT_PASSWORD, ESPHOME_PASSWORD,
                                       # HUB_LAN_IP (DHCP reservation manzili), HUB_TAILNET_IP (`tailscale ip -4`)
sh mosquitto/make-passwd.sh garden_lights   # har bir qurilma kaliti
docker compose up -d
docker compose ps
```
`HUB_TOKEN` va `SIGNING_KEY_HEX` ilovadagi **Hub → Hub qo'shish** dan olinadi (bir marta ko'rsatiladi).
Ilovada Hub "Onlayn" bo'lishi kerak.

## 8. ESPHome (qurilma proshivkasi, kompyutersiz)
- Brauzerda (LAN yoki Tailscale orqali): `http://hub.local:6052`. Login `.env` dagi `ESPHOME_USERNAME` va `ESPHOME_PASSWORD`.
- `devices/esphome/*.yaml` va `secrets.yaml` `services/hub/esphome/` papkasida turadi.
- **Birinchi** proshivka USB kabel orqali yoziladi. Brauzerdan: ESPHome Dashboard → Install → "Plug into this computer" — Chrome kerak, iPad Safari'da ishlamaydi. Muqobil: proshivka oldindan yozilgan qurilma sotib olish yoki elektrikning kompyuteri. Keyingi yangilanishlar Wi-Fi orqali (OTA, parol bilan).

## 9. Yangilash
- OS: `unattended-upgrades` (xavfsizlik yangilanishlari avtomatik).
- Stack: `cd ~/smarthome && git pull && cd services/hub && docker compose up -d --build`.

## Tekshiruv ro'yxati
- [ ] `ufw status` → faqat LAN va Tailscale.
- [ ] Router'da port forwarding yo'q; tashqi port skan `[REAL]` — `docs/runbooks/security-audit.md` dagi 3-bo'lim.
- [ ] `sudo ss -tlnp | grep -E ':(1883|8971|8555|6052)'` — har bir port faqat LAN/Tailscale manzilida yoki ufw ostida (`*:6052` faqat ESPHome uchun).
- [ ] `upsc` UPS holatini ko'rsatadi; UPS'ni tarmoqdan uzib sinash.
- [ ] Hub qayta yoqilgandan keyin hamma konteyner o'zi ko'tariladi (`restart: always`).
