# Yandex Alisa'ni ulash (telefondan, bir marta)

Alisa'ga ulangan chiroqlar, rozetkalar, televizorlar va konditsionerlar ilovada boshqariladi (ADR 0016).

Ulanish bulut orqali ishlaydi: **bizning server → Yandex**, Hub kerak emas. Buning uchun Yandex'dan bir marta **OAuth token** olinadi.

## 1. Yandex'da ilova yaratish (5 daqiqa)
1. Yandex hisobingiz bilan (Alisa qurilmalari shu hisobda) **oauth.yandex.ru/client/new** sahifasini oching.
2. **Название:** `SmartHome`.
3. **Платформа:** «Веб-сервисы». **Redirect URI:** `https://oauth.yandex.ru/verification_code`.
4. **Доступы** bo'limida **«Умный дом»** guruhidan ikkitasini belgilang:
   - `iot:view` (просмотр);
   - `iot:control` (управление).
5. **Создать приложение** ni bosing. Sahifada **ClientID** chiqadi, uni nusxalang.

## 2. Token olish
Brauzerda quyidagini oching (`CLIENT_ID` o'rniga 1-qadamdagi ClientID):
```
https://oauth.yandex.ru/authorize?response_type=token&client_id=CLIENT_ID
```
**Разрешить** ni bosing. Sahifada token chiqadi (`y0_...` bilan boshlanadi). Uni nusxalang.

⚠️ **Token — sir.** Uni hech kimga yubormang va chatga yozmang.

## 3. Ilovaga kiritish
**Sozlamalar → Alisa (Yandex) → Yandex OAuth token** maydoniga tokenni qo'ying va **Alisa'ni ulash** ni bosing.

Natijada:
- Alisa qurilmalari **Qurilmalar** ro'yxatida paydo bo'ladi. Yandex'dagi xona nomi ilovadagi bo'lim nomiga mos kelsa, qurilma o'sha bo'limga tushadi.
- Holat har daqiqada Yandex'dan olinadi. Buyruqdan keyin holat darhol qayta o'qiladi va **faqat Yandex yangi holatni ko'rsatsa** "Tasdiqlandi" chiqadi.
- **Alisa ssenariylari** (Yandex ilovasida tuzilganlar) shu bo'limdan ishga tushiriladi.
- Boshqaruvi bo'lmagan qurilmalar (masalan, Stansiyaning o'zi) ko'rsatilmaydi va ro'yxatda alohida yoziladi.

Token muddati tugasa yoki Yandex'da bekor qilinsa, holat "Xato" bo'ladi. Shunda 2-qadamni takrorlang.
