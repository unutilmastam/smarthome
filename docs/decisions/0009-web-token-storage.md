# 0009 — PWA'da tokenlarni saqlash

- Holat: qabul qilingan
- Sana: 2026-10-07

## Kontekst
ARCHITECTURE 13 refresh token uchun `HttpOnly` cookie talab qiladi. Faza 2 da refresh token JSON body'da qaytariladi — bu CLI va Hub uchun qulay, lekin brauzerda JS (va XSS) uni o'qiy oladi. PWA va API bir xil domenda turadi (`/` — PWA, `/api` — Python app).

## Qaror
- **Access token** (15 daq) faqat JS xotirasida saqlanadi. `localStorage` ham, `sessionStorage` ham ishlatilmaydi. Sahifa yangilansa, access token cookie orqali qayta olinadi.
- **Refresh token** — `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth` cookie (`sh_refresh`), muddati 30 kun. JS uni ko'rmaydi.
- Brauzer mijozi har bir auth so'rovida `X-Client: web` sarlavhasini yuboradi. Shu sarlavha bo'lsa:
  - `login` va `refresh` cookie o'rnatadi va javob body'sida `refresh_token` **qaytarmaydi**;
  - `refresh` token'ni cookie'dan oladi.
- CSRF himoyasi:
  - `SameSite=Strict`;
  - `X-Client` maxsus sarlavhasi. Boshqa saytdan bunday sarlavhani yuborish uchun CORS preflight kerak, CORS esa yoqilmagan.
  - Cookie faqat `/api/v1/auth` yo'liga yuboriladi; boshqa API'lar `Authorization: Bearer` bilan ishlaydi.
- `logout` va `logout-all` cookie'ni o'chiradi.
- `Secure` bayrog'i production'da majburiy (`COOKIE_SECURE=true`); lokal ishlab chiqishda o'chirilishi mumkin.

## Oqibatlar
- XSS bo'lsa ham refresh token o'g'irlanmaydi. Access token o'g'irlanishi mumkin, lekin u ≤ 15 daqiqa yashaydi.
- Body rejimi (Hub, CLI, testlar) avvalgidek ishlaydi.
- PWA va API boshqa-boshqa domenda bo'lsa bu sxema ishlamaydi; bitta domen sharti runbook'ga yoziladi (Faza 7).
