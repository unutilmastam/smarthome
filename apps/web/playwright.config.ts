import { defineConfig, devices } from "@playwright/test";

const PY = process.env.PYTHON ?? "python3";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: 0, // a flaky failure must be visible, not retried away
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:4173", trace: "retain-on-failure" },
  projects: [
    { name: "phone", use: { ...devices["Pixel 7"] } },
    { name: "ipad", use: { ...devices["iPad (gen 7) landscape"], browserName: "chromium" } },
  ],
  webServer: [
    {
      command: `${PY} e2e/stack.py`,
      url: "http://127.0.0.1:8000/api/v1/health",
      timeout: 120_000,
      reuseExistingServer: false,
      stdout: "pipe",
    },
    {
      command: "npx vite build && npx vite preview --host 127.0.0.1 --port 4173 --strictPort",
      url: "http://127.0.0.1:4173",
      timeout: 120_000,
      reuseExistingServer: false,
      env: { BACKEND_URL: "http://127.0.0.1:8000" },
    },
  ],
});
