# apps/web — PWA (telefon, iPad, veb)

React 18 + TypeScript + Vite, TanStack Query, i18next (uz/ru/en), vite-plugin-pwa.
Qurilma imkoniyatlari va rollar `packages/contracts` dan o'qiladi (yagona manba).

| Buyruq | Vazifa |
|---|---|
| `npm ci` | o'rnatish |
| `npm run dev` | ishlab chiqish (`/api` → `BACKEND_URL`, standart `http://127.0.0.1:8000`) |
| `npx tsc -b && npx vitest run` | typecheck + unit testlar |
| `npx vite build` | `dist/` (cPanel `public_html` ga, Faza 7) |
| `PYTHON=python3 npx playwright test` | E2E: backend + Hub + mosquitto + simulyator + PWA, telefon va iPad emulyatsiyasi `[SIM]` |

Tokenlar: ADR 0009 (access — faqat xotirada, refresh — `HttpOnly` cookie).
Holat belgilari: ✓ tasdiqlangan, ⏳ kutilmoqda, ≈ taxminiy, ⚠ eskirgan, ? noma'lum, — qo'llab-quvvatlanmaydi.
