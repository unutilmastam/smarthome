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
  await card.getByRole("button", { name: "Yoqish" }).click();
  await expect(card.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 15_000 });
  await expect(card.getByTestId("value-Holat")).toContainText("Yoqilgan", { timeout: 10_000 });
  // Reload: access token was only in memory, the HttpOnly refresh cookie restores the session.
  await page.reload();
  await expect(page.getByTestId("device-garden_lights").getByTestId("value-Holat")).toContainText("Yoqilgan");
  // Turn it off again so tests stay independent.
  await page.getByTestId("device-garden_lights").getByRole("button", { name: "O'chirish" }).click();
  await expect(page.getByTestId("device-garden_lights").getByTestId("command-status"))
    .toHaveAttribute("data-status", "confirmed", { timeout: 15_000 });
});

test("gate asks for PIN and is confirmed by the reed switch", async ({ page }) => {
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
