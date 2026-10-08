import { expect, test } from "@playwright/test";

// [SIM] Electrical panel (ADR 0015): 12 breakers in label order; switch one off and on with
// the PIN, each confirmed by the breaker's own contact; the tripped pump cannot be switched on.
test("panel: breakers in order, switch with PIN, tripped one refused", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  await expect(page.getByRole("heading", { name: "Uy" })).toBeVisible();
  await page.goto("/energy");
  await expect(page.getByRole("heading", { name: "Elektr shiti" })).toBeVisible();

  const panel = page.getByRole("region", { name: "Asosiy shit" });
  const levers = panel.getByRole("switch");
  await expect(levers).toHaveCount(12);
  await expect(levers.first()).toHaveAccessibleName("1 — Oshxona");
  await expect(levers.nth(11)).toHaveAccessibleName("12 — Nasos");
  // Reported states arrive from the devices (nothing guessed before that).
  const kitchen = panel.getByTestId("breaker-brk_oshxona");
  await expect(kitchen).toHaveAttribute("data-state", "on", { timeout: 20_000 });
  await expect(panel.getByTestId("breaker-brk_nasos")).toHaveAttribute("data-state", "tripped");
  await expect(panel.getByTestId("breaker-brk_nasos").getByRole("switch")).toBeDisabled();

  const pin = async () => {
    await page.getByLabel("PIN", { exact: true }).fill("4821");
    await page.getByRole("button", { name: "Tasdiqlash" }).click();
  };
  await kitchen.getByRole("switch").click();
  await expect(page.getByText("1 — Oshxona: O'chirish")).toBeVisible();
  await pin();
  await expect(kitchen).toHaveAttribute("data-state", "off", { timeout: 15_000 });
  await expect(kitchen.getByText("Tasdiqlandi")).toBeVisible({ timeout: 15_000 });
  await kitchen.getByRole("switch").click();
  await pin();
  await expect(kitchen).toHaveAttribute("data-state", "on", { timeout: 15_000 });
});
