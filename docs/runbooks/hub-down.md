# Hub o'chdi / aloqa yo'q

**Qanday bilasiz:**
- Telegram/Push'ga 🚨 **"Hub aloqasiz: N daqiqadan beri javob yo'q"** keladi. Bulut cron'i har daqiqa tekshiradi va 150 s javob bo'lmasa xabar beradi, ya'ni 3 daqiqa ichida.
- Ilovada sariq "Hub bilan aloqa yo'q" banneri chiqadi.

**Bu paytda nima ishlaydi va nima ishlamaydi:**
- Bulutdan buyruq berib bo'lmaydi: `503 HUB_UNREACHABLE`. Ilova buni ochiq aytadi.
- Holatlar eskirgan (`stale`) deb ko'rsatiladi. Ular taxmin qilinmaydi.
- Hub tirik, faqat internet uzilgan bo'lsa: avtomatika, signalizatsiya va kamera yozuvi uyda ishlashda davom etadi. Uyda `http://hub.local` orqali boshqarish mumkin.
- Hub butunlay o'chgan bo'lsa: rele proshivkadagi xavfsiz holatda qoladi (nasos va klapan `max_runtime` bilan o'zi yopiladi). ESP32 broker'siz 15 daqiqa kutadi, keyin qayta yuklanadi va **OFF** holatda turadi.

## Qadamlar (iPad / telefon)
1. **Uyda internet bormi?** Telefon uy Wi-Fi'ida internetga chiqyaptimi? Yo'q bo'lsa — router yoki provayder muammosi. Internet qaytganda Hub o'zi ulanadi va to'plangan ma'lumotlarni yuboradi.
2. **Hub yoniqmi?** Tailscale ilovasida `hub` mashinasi "Connected" holatidami?
   - Ha → 3-qadam.
   - Yo'q → Hub'ni jismonan tekshiring: chirog'i, UPS. Svet o'chgan bo'lsa → [power-outage.md](power-outage.md). Hub "qotib" qolgan bo'lsa → quvvat tugmasini 5 s bosib turing va qayta yoqing. BIOS'da "Restore on AC power loss: Power On" o'rnatilgan.
3. **Konteynerlar** (Termius → `hubadmin@hub`):
   ```
   cd ~/smarthome/services/hub
   docker compose ps                      # hammasi "running"?
   docker compose logs --tail 50 gateway  # "heartbeat failed" / "401" bormi?
   ```
   - `401 Invalid or revoked hub token` → Hub ilovada bekor qilingan yoki `.env` dagi `HUB_TOKEN` noto'g'ri. Ilova → Hub → yangi Hub qo'shing va `.env` ni yangilang.
   - Konteyner to'xtagan → `docker compose up -d`.
   - Disk to'lgan → [disk-full.md](disk-full.md).
4. **Bulut ishlayaptimi?** Brauzerda `https://<sayt>/api/v1/health` → `"status":"ok"`. Ishlamasa → [deploy.md](deploy.md), "Muammo bo'lsa" bo'limi.

**Tugadi:** Hub qayta ulanganda ℹ️ "Hub qayta ulandi" xabari keladi, ilovadagi banner yo'qoladi. Hub o'chiq paytda qurilmalar haqida alohida xabar berilmagan bo'ladi: sabab bitta edi. Agar biror qurilma hali ham aloqasiz bo'lsa, u haqida xabar alohida keladi.
