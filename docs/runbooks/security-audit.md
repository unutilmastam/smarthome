# Xavfsizlik tekshiruvi (Faza 14)

Har push'da GitHub Actions'dagi `security` job'i avtomatik ishlaydi. U `deploy-cloud` dan oldin turadi: yiqilsa, deploy **bo'lmaydi**.

| Tekshiruv | Nimani | Qachon yiqiladi |
|---|---|---|
| `pip-audit` | `services/backend` va `services/hub` dagi barcha qotirilgan Python paketlari, tranzitiv bog'liqliklari bilan | Har qanday ma'lum zaiflik |
| `npm audit --audit-level=high` | PWA paketlari | `high` yoki `critical` |
| `gitleaks` (git tarixi + ishchi papka) | Repo'ga tushgan sirlar | Har qanday topilma. Tekshirilgan soxta topilmalar `.gitleaksignore` da, har biri sababi bilan |
| `tests/test_exposure.py` (hub testlari) | Hub tashqariga nima ochadi | Port aniq LAN/Tailscale manzilsiz e'lon qilinsa; broker anonim kirishga ruxsat bersa; log aylanishi bo'lmasa |

## 1. Natijalar — 2026-10-08
- `pip-audit`: backend va hub — **zaiflik yo'q**. O'rnatilgan muhit ham, tranzitiv paketlar bilan, tekshirildi.
- `npm audit`: **0 ta** zaiflik (dev paketlar bilan birga).
- `gitleaks`: git tarixidagi 22 commit va ishchi papka tekshirildi. **Haqiqiy sir topilmadi.** 2 ta soxta topilma `.gitleaksignore` ga yozildi:
  - ochiq HMAC test vektori (ochiq test kalitidan hisoblangan);
  - testdagi ataylab noto'g'ri refresh token.
- **Port tekshiruvi — topilgan va tuzatilgan muammo:** `docker-compose.yml` portlarni `"1883:1883"` ko'rinishida e'lon qilardi. Docker bunday portlarni barcha manzillarda (IPv6 ham) ochadi va iptables qoidasini ufw'dan **oldin** qo'yadi. Ya'ni "faqat LAN" degan ufw qoidasi bu portlarga ta'sir qilmasdi. Endi har bir port `HUB_LAN_IP` / `HUB_TAILNET_IP` ga bog'langan. `docker compose config` buni tasdiqladi: 7 ta portning har birida `host_ip` bor, `HUB_LAN_IP` siz esa stack ishga tushmaydi.
- **Boshqa topilmalar (tuzatildi):**
  - Hub disk to'lishi: Docker log'lari cheklanmagan edi. Endi har servis uchun ko'pi bilan 3 × 10 MB.
  - Hub sog'lig'i: ilgari bulut uni tashlab yuborardi. Endi saqlanadi; broker o'chishi va disk to'lishi bildirishnoma bilan keladi.
  - Telefon yo'qolganda "Barcha qurilmalardan chiqish" Push obunalarini ham o'chiradi.

## 2. Topilma chiqsa
1. GitHub → Actions → `security` → qaysi paket va qaysi CVE ekanini ko'ring.
2. Paket versiyasini tuzatilgan versiyaga ko'taring (`requirements*.txt` yoki `npm update <paket>`). Testlar o'tsa, merge qiling: deploy o'zi chiqadi.
3. Tuzatilgan versiya hali yo'q bo'lsa: zaiflik bizning yo'lga ta'sir qiladimi, tahlil qiling. Ta'sir qilmasa, `pip-audit --ignore-vuln ID` ni sababi bilan qo'shing. Hech qachon tekshiruvni o'chirmang.
4. `gitleaks` haqiqiy sir topsa: sir **allaqachon oshkor bo'lgan** deb hisoblanadi. Uni almashtiring ([token-stolen.md](token-stolen.md)), keyin kodni tuzating. Tarixni qayta yozish sirni qaytarib bermaydi.

## 3. Tashqi port skani `[REAL]` (uy internet ulangandan keyin)
Maqsad: internetdan uyga **hech qanday port ochiq emasligini** isbotlash.
1. Uy Wi-Fi'ida telefonda `https://ifconfig.me` ni oching va tashqi IP'ni yozib oling. IPv6 bo'lsa, uni ham yozing.
2. **Mobil internetdan** (Wi-Fi o'chiq) port skanerini ishlating, masalan iOS'da "Fing" yoki "Network Analyzer" → Port scan → uy IP'si. Kamida shu portlarni tekshiring: `22, 80, 443, 1883, 8883, 6052, 8971, 8555, 5000, 1984`. Kutilgan natija: **hammasi yopiq** (`closed`/`filtered`).
3. IPv6 manzil uchun ham shu tekshiruvni qiling. Ko'p routerlar IPv6'da kiruvchi ulanishni sukut bo'yicha ochib qo'yadi.
4. Hub'da (Tailscale orqali SSH, Termius):
   ```
   sudo ss -tlnp | grep -E ':(1883|8971|8555|6052)'
   ```
   `1883`, `8971` va `8555` faqat `HUB_LAN_IP` va Tailscale manzilida bo'lishi kerak. `6052` (ESPHome, host tarmog'ida) ufw bilan himoyalangan: `sudo ufw status`.
5. Natijani `docs/hardware/installed.md` ga sana bilan yozing. Ochiq port topilsa — router'da port forwarding va UPnP'ni o'chiring, so'ng qayta skan qiling.

Bulut tomoni (hostmaster.uz) — shared hosting, uning portlarini provayder boshqaradi. Biz u yerda port ochmaymiz: faqat Passenger (HTTPS) va cron ishlaydi.
