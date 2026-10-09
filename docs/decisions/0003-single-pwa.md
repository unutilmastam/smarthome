# 0003 — Bitta React PWA (React Native emas)

- Holat: qabul qilingan
- Sana: 2026-10-07

## Kontekst
- Asl rejada mobil (React Native) va veb (React) — ikki alohida ilova.
- Bitta dasturchi (va AI agent), kompyutersiz: Xcode, Android Studio, App Store hisobi yo'q.
- Ilova ikki joydan xizmat qilishi kerak: cloud (`https://home.<domen>.uz`) va uy ichida Hub (`http://hub.local`, internetsiz).
- iOS 16.4+ da o'rnatilgan PWA uchun Web Push ishlaydi.

## Qaror
- **Bitta React 18 + TypeScript + Vite PWA** (`apps/web`), `vite-plugin-pwa`. Telefon, iPad va kompyuterda bir xil kod.
- Bir xil build ham cPanel `public_html` ga, ham Hub `local-api` ga joylanadi. Ilova avval lokal Hub'ni tekshiradi, bo'lmasa cloud'ga ulanadi.
- Bildirishnoma: Web Push + Telegram bot (zaxira kanal, iOS push kechikishi tufayli).
- Expo/React Native — keyinroq, ixtiyoriy, alohida ADR bilan (agar native imkoniyat — masalan, geofencing, NFC — haqiqatan kerak bo'lsa).

## Ko'rib chiqilgan muqobillar
- **React Native + React** — 2x ish, native build uchun Mac/EAS kerak.
- **Faqat Telegram bot** — boshqaruv paneli, kamera, grafiklar uchun yetarli emas.
- **Home Assistant ilovasi** — o'z rollarimiz, imzo va contracts bilan mos emas.

## Oqibatlar
### Ijobiy
- Bitta kod bazasi, GitHub Actions'da build, App Store tekshiruvisiz yangilanish.
### Salbiy / xavflar
- iOS PWA cheklovlari: push faqat "Home Screen"ga o'rnatilganda; fon jarayon yo'q; saqlash iOS tomonidan tozalanishi mumkin.
- `http://hub.local` — HTTPS emas: brauzer ba'zi API'larni (Service Worker, Web Push, kamera) "secure context"siz bermaydi. Lokal rejimda HTTPS (masalan, Tailscale sertifikati yoki lokal CA) Faza 6/10 da alohida hal qilinadi. **Ochiq savol.**
- mDNS (`.local`) Android'ning ba'zi versiyalarida ishonchsiz — zaxira: Hub'ning statik IP manzili sozlamalarda.
- Refresh token saqlash usuli Faza 6 da alohida ADR.
