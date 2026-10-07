import { expect, test } from "@playwright/test";

// [SIM] real backend + hub gateway + mosquitto + simulated devices.

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  await expect(page.getByRole("heading", { name: "Uy" })).toBeVisible();
});

test("login → turn on the garden light → confirmed by the device", async ({ page }) => {
  const card = page.getByTestId("device-garden_lights");
  await expect(card).toBeVisible();
  // Wait for the hub to report the light's real state first.
  await expect(card.getByTestId("value-Holat")).toContainText("Tasdiqlangan", { timeout: 20_000 });
  const sw = card.getByRole("switch", { name: "Yoqish/o'chirish" });
  if (await sw.getAttribute("aria-checked") === "true") {   // left on by another run: start from off
    await sw.click();
    await expect(sw).toHaveAttribute("aria-checked", "false", { timeout: 15_000 });
  }
  await sw.click();
  await expect(card.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 15_000 });
  await expect(card.getByTestId("value-Holat")).toContainText("Yoqilgan", { timeout: 10_000 });
  // The switch knob follows the state the DEVICE reported.
  await expect(sw).toHaveAttribute("aria-checked", "true");
  // Reload: access token was only in memory, the HttpOnly refresh cookie restores the session.
  await page.reload();
  await expect(page.getByTestId("device-garden_lights").getByTestId("value-Holat")).toContainText("Yoqilgan");
  // Turn it off again so tests stay independent.
  await page.getByTestId("device-garden_lights").getByRole("switch").click();
  await expect(page.getByTestId("device-garden_lights").getByTestId("command-status"))
    .toHaveAttribute("data-status", "confirmed", { timeout: 15_000 });
});

test("gate asks for PIN and is confirmed by the reed switch", async ({ page }) => {
  page.on("response", async (r) => {
    if (r.url().includes("/api/v1/commands")) {
      try { const b = await r.json(); console.log("CMD", r.request().method(), r.status(), JSON.stringify({ id: b.data?.id, s: b.data?.status, c: b.data?.created_at, a: b.data?.action, e: b.error?.code })); } catch { /* ignore */ }
    }
  });
  const card = page.getByTestId("device-front_gate");
  await expect(card.getByTestId("value-Holat")).toContainText("Tasdiqlangan", { timeout: 20_000 });
  await card.getByRole("button", { name: "Ochish" }).click();
  await page.getByLabel("PIN", { exact: true }).fill("4821");
  await page.getByRole("button", { name: "Tasdiqlash" }).click();
  await expect(card.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 20_000 });
  await card.getByRole("button", { name: "Yopish" }).click();
  await page.getByLabel("PIN", { exact: true }).fill("4821");
  await page.getByRole("button", { name: "Tasdiqlash" }).click();
  await expect(card.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 20_000 });
});
