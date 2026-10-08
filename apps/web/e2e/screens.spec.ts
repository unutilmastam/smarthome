import { expect, test } from "@playwright/test";

// Only runs when SCREENSHOTS_DIR is set (documentation screenshots).
test.skip(!process.env.SCREENSHOTS_DIR, "SCREENSHOTS_DIR not set");

test("screenshots", async ({ page }, info) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  const card = page.getByTestId("device-garden_lights");
  await expect(card.getByTestId("value-Holat")).toContainText("Tasdiqlangan", { timeout: 20_000 });
  const sw = card.getByRole("switch");
  if (await sw.getAttribute("aria-checked") !== "true") {
    await sw.click();
    await expect(card.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 15_000 });
  }
  await page.screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-dashboard.png`, fullPage: true });
  await page.getByRole("link", { name: "Bog' chiroqlari" }).click();
  await expect(page.getByText("Buyruqlar tarixi")).toBeVisible();
  await page.screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-device.png`, fullPage: true });
  await page.goto("/rooms");
  await expect(page.getByRole("heading", { name: "Bo'limlar" })).toBeVisible();
  await page.screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-rooms.png`, fullPage: true });
  await page.getByRole("button", { name: "Nima qo'shamiz?" }).click();
  await page.getByRole("dialog").getByRole("button", { name: /Qurilma qo'shish/ }).click();
  await expect(page.getByRole("heading", { name: "Qurilma turini tanlang" })).toBeVisible();
  await page.screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-add-type.png` });
  await page.getByRole("button", { name: "Chiroq", exact: true }).click();
  await page.screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-add-details.png` });
  await page.keyboard.press("Escape");
  await page.goto("/automations");
  await page.getByRole("button", { name: "Yangi avtomatika" }).click();
  const dlg = page.getByRole("dialog");
  await dlg.getByLabel("Nomi").fill("Kechqurun eshik ochilsa");
  await dlg.getByRole("button", { name: /Qurilma holati/ }).first().click();
  await dlg.getByRole("combobox", { name: "Qurilma", exact: true }).first().selectOption({ label: "Kirish eshigi" });
  await dlg.getByRole("button", { name: /Kun \/ tun/ }).click();
  await dlg.getByRole("button", { name: /Buyruq/ }).click();
  await dlg.getByRole("combobox", { name: "Qurilma", exact: true }).last().selectOption({ label: "Bog' chiroqlari" });
  await page.screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-automation-editor.png` });
  await page.keyboard.press("Escape");
  await page.goto("/notifications");
  await page.getByTestId("notification-cover.sensor_conflict").waitFor();
  await page.screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-notifications.png`, fullPage: true });
  await page.goto("/settings#notifications");
  await page.locator("#notifications").getByText("Telegram").waitFor();
  await page.locator("#notifications").screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-notify-settings.png` });
});
