/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon.svg", "apple-touch-icon.png"],
      manifest: {
        name: "SmartHome",
        short_name: "SmartHome",
        description: "Uy boshqaruv markazi",
        lang: "uz",
        start_url: "/",
        display: "standalone",
        background_color: "#0f1419",
        theme_color: "#0f1419",
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        // API responses are never cached: stale device state must not look current.
        navigateFallback: "/index.html",
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [],
        // Web Push: show notifications, "Ko'rdim" action (ADR 0014).
        importScripts: ["push-sw.js"],
      },
    }),
  ],
  // packages/contracts is shared with backend and hub (single source of truth).
  server: { proxy: { "/api": backend }, fs: { allow: ["..", "../../packages/contracts"] } },
  preview: { proxy: { "/api": backend } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
