# services/hub — Home Hub

| Papka | Vazifa |
|---|---|
| `gateway/` | Cloud ↔ lokal ko'prik: heartbeat, buyruq polling, imzo/muddat/replay tekshiruvi, lokal MQTT, tasdiq, offline bufer |
| `simulator/` | Virtual qurilmalar (lokal MQTT shartnomasi bo'yicha) va nosozlik rejimlari |
| `mosquitto/` | Lokal broker: anonim o'chiq, har qurilmaga alohida login + ACL |

Ishga tushirish (Hub'da): `.env.example` → `.env`, `sh mosquitto/make-passwd.sh <qurilma kalitlari>`, `docker compose up -d`.
Simulyator bilan: `docker compose --profile sim up -d`.

Testlar: `pip install -r requirements-dev.txt -r ../backend/requirements.txt && python -m pytest`
(lokal `mosquitto` binari kerak; integratsion test backend'ni shu jarayonda ishga tushiradi).
