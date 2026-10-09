import { expect, test } from "@playwright/test";

// [SIM] Smart Life / Tuya devices (ADR 0016): backend + hub gateway with TUYA_SIMULATOR.
// The hub speaks to (simulated) Tuya devices; every state shown is what the device reported.

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  await expect(page.getByRole("heading", { name: "Uy" })).toBeVisible();
});

test("Wi-Fi relay: switched from its tile, confirmed by the relay itself", async ({ page }) => {
  const tile = page.getByTestId("device-wifi_rele");
  await expect(tile.getByTestId("value-Holat")).toContainText("Tasdiqlangan", { timeout: 20_000 });
  const sw = tile.getByRole("switch");
  const was = await sw.getAttribute("aria-checked");
  await sw.click();
  await expect(tile.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 15_000 });
  await expect(sw).toHaveAttribute("aria-checked", was === "true" ? "false" : "true");
});

test("Wi-Fi breaker sits in its own panel with the metering it reports", async ({ page }) => {
  await page.goto("/energy");
  const panel = page.getByRole("region", { name: "Hovli shiti" });
  const brk = panel.getByTestId("breaker-wifi_avtomat");
  await expect(brk).toHaveAttribute("data-state", "on", { timeout: 20_000 });
  await expect(brk).toContainText("280 W");
});

test("TV remote: a button is learned from the old remote, then pressed (sent, never 'confirmed')", async ({ page }) => {
  await page.goto("/devices");
  await page.getByRole("link", { name: "Zal televizori" }).first().click();
  await expect(page.getByText("ta tugma o'rgatilgan")).toBeVisible({ timeout: 20_000 });
  const power = page.getByTestId("rbtn-power");
  if (await power.isDisabled()) {                      // not learned yet (first run)
    await page.getByRole("button", { name: "O'rgatish" }).click();
    await page.getByTestId("rbtn-power").click();
    await expect(page.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 20_000 });
    await page.getByRole("button", { name: "Tayyor" }).click();
  }
  await expect(power).toBeEnabled();
  await power.click();
  await expect(page.getByTestId("command-status")).toHaveAttribute("data-status", "acked", { timeout: 15_000 });
  await page.waitForTimeout(1500);
  await expect(page.getByTestId("command-status")).toHaveAttribute("data-status", "acked");  // IR: no feedback
});

test("add a Smart Life relay: the Local Key is taken but never shown again", async ({ page }) => {
  await page.getByRole("button", { name: "Nima qo'shamiz?" }).click();
  await page.getByRole("dialog").getByRole("button", { name: /Qurilma qo'shish/ }).click();
  await page.getByRole("button", { name: "Wi-Fi rele" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Nomi").fill("Hovli chirog'i relesi");
  await dialog.getByLabel("Device ID").fill("bf0123456789abcdefxyz");
  await dialog.getByLabel("Local Key").fill("fakefakefakefake");
  await dialog.getByLabel(/IP manzil/).fill("192.168.1.77");
  await dialog.getByRole("button", { name: "Qo'shish" }).click();
  await expect(page.getByRole("heading", { name: "Hovli chirog'i relesi" })).toBeVisible({ timeout: 10_000 });
  await expect(page.locator("body")).not.toContainText("fakefakefakefake");
  // Clean up so reruns start from the same state.
  await page.getByRole("button", { name: "Qurilmani tahrirlash" }).click();
  await page.getByRole("button", { name: "Qurilmani olib tashlash" }).click();
  await page.getByRole("button", { name: "Ha, olib tashlash" }).click();
  await expect(page).toHaveURL(/\/devices$/);
});
