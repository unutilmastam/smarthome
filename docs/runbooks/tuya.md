# Smart Life / Tuya qurilmalarini ulash (telefondan)

Bu yo'riqnoma Wi-Fi rele, Wi-Fi avtomat, rozetka, chiroq va IR pult (smart pult) uchun (ADR 0016).

Hub bu qurilmalarga **uy Wi-Fi tarmog'ida to'g'ridan-to'g'ri** ulanadi. Buning uchun har bir qurilmaning uchta ma'lumoti kerak:
- **Device ID**;
- **Local Key**;
- **IP manzil**.

Device ID va Local Key bir marta Tuya'ning dasturchilar saytidan olinadi. Keyin Tuya buluti ishlatilmaydi.

## 1. Qurilmani Smart Life'ga ulash
1. Telefonga **Smart Life** ilovasini o'rnating va ro'yxatdan o'ting.
2. Telefon **2.4 GHz** Wi-Fi tarmog'ida bo'lsin (5 GHz emas).
3. Qurilmadagi tugmani **5–10 soniya** bosib turing, chiroq tez miltillasin.
4. **"+" → Add Device**, keyin Wi-Fi parolini kiriting.
5. Qurilma Smart Life'da ishlashini tekshiring.

## 2. Doimiy IP manzil
Router sozlamalarida (odatda `192.168.1.1`): **DHCP → Address Reservation** bo'limida qurilmaga doimiy IP bering, masalan `192.168.1.50`.

Qurilma Smart Life'da **Device → ✏️ → Device Information** sahifasida ko'rinadi. U yerda **Virtual ID** (bu Device ID) va **IP** yozilgan.

## 3. Local Key olish (bir marta, ~15 daqiqa, telefon brauzerida)
1. **iot.tuya.com** saytida ro'yxatdan o'ting. Bepul, "Individual developer" turini tanlang.
2. **Cloud → Development → Create Cloud Project**:
   - Industry: Smart Home;
   - Development Method: Smart Home;
   - Data Center: **Central Europe** (O'zbekiston uchun odatda shu; Smart Life hisobingiz qaysi markazda bo'lsa, o'shani tanlang).
3. Loyihada **Devices → Link Tuya App Account → Add App Account** ni bosing. QR kod chiqadi.
4. Smart Life ilovasida: **Me → ⊞ (skaner)** bilan QR kodni skanerlang va tasdiqlang. Endi barcha qurilmalaringiz loyihada ko'rinadi.
5. **Cloud → API Explorer → Device Management → Query Device Details** ni oching. `device_id` maydoniga qurilmaning Device ID'sini yozing va **Submit** bosing. Javobdagi **`local_key`** qiymati kerakli kalit bo'ladi.

⚠️ **Local Key — sir.** Uni hech kimga yubormang va chatga yozmang. Uni faqat ilovaga, qurilma qo'shish oynasiga kiritasiz.

Qurilmani Smart Life'dan o'chirib qayta ulasangiz, Local Key **o'zgaradi**. Bunday holda ilovada yangisini kiriting: **Qurilma → ✏️ → Yangi Local Key**.

## 4. Ilovaga qo'shish
**+ → Qurilma qo'shish → Smart Life / Tuya** bo'limidan turini tanlang:

| Qurilma | Tur |
|---|---|
| Wi-Fi avtomat (shitda) | **Wi-Fi avtomat (shit)**. Shit nomi va raqami ham so'raladi |
| 7–32V rele | **Wi-Fi rele** |
| Rozetka (quvvat ko'rsatadi) | **Wi-Fi rozetka** |
| Chiroq | **Wi-Fi chiroq** |
| IR pult (televizor uchun) | **Televizor (IR pult)** |
| IR pult (konditsioner uchun) | **Konditsioner (IR pult)** |

Keyin quyidagilarni kiriting:
- **Device ID**;
- **Local Key**;
- **IP**;
- **Protokol**: odatda **3.3**. Yangi qurilmalar ko'pincha **3.4** yoki **3.5** bo'ladi. Holat kelmasa, boshqasini sinab ko'ring.

Bir necha soniyadan keyin holat Hub'dan keladi. Plitkadagi yashil nuqta qurilmaning **o'zi** javob berganini bildiradi.

## 5. IR pultni o'rgatish
1. Qurilma sahifasida **O'rgatish** ni bosing.
2. Ilovadagi tugmani bosing (masalan ⏻).
3. 25 soniya ichida asl pultni IR pultga qaratib, o'sha tugmani bosing.
4. Tugma oq rangga kirsa, kod olindi.

Konditsioner pultida tugma holatni birga yuboradi. Shuning uchun, masalan, **«Sovutish 24°»** tugmasini o'rgatishdan oldin asl pultda "sovutish, 24°" ni sozlang va yoqish tugmasini bosing.

Ilova IR buyruqni faqat **yuboradi**. Televizor yoki konditsioner haqiqatan javob berganini IR orqali bilib bo'lmaydi, shuning uchun bunday buyruq "Tasdiqlandi" bo'lmaydi.

## Muammo bo'lsa
| Belgi | Sabab | Yechim |
|---|---|---|
| Qurilma "Oflayn" | IP o'zgargan yoki qurilma o'chiq | Router'da doimiy IP bering, IP'ni ilovada yangilang |
| Holat "Noma'lum" bo'lib qoladi | Protokol versiyasi mos emas | 3.3 / 3.4 / 3.5 ni sinab ko'ring |
| Holat noto'g'ri | Modelda DPS raqamlari boshqacha | Hub jurnalidagi `tuya … dps` qatorini menga yuboring, DPS raqamini sozlab beraman |
| Kalit ishlamay qoldi | Qurilma Smart Life'da qayta ulangan | Yangi Local Key oling (3-qadam) |
