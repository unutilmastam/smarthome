import { expect, test } from "@playwright/test";

// [SIM] Create an automation in the visual editor, switch it off/on, delete it.
test("automation: create in the editor, toggle, delete", async ({ page }) => {
  const name = `Eshik ochilsa ${Date.now() % 100000}`;
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  await expect(page.getByRole("heading", { name: "Uy" })).toBeVisible();
  await page.goto("/automations");
  await page.getByRole("button", { name: "Yangi avtomatika" }).click();

  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Nomi").fill(name);
  await dialog.getByRole("button", { name: /Qurilma holati/ }).first().click();
  await dialog.getByRole("combobox", { name: "Qurilma", exact: true }).first().selectOption({ label: "Kirish eshigi" });
  await dialog.getByRole("combobox", { name: "bo'lganda" }).selectOption({ label: "Ochiq" });
  await dialog.getByRole("button", { name: /Buyruq/ }).click();
  const target = dialog.getByRole("combobox", { name: "Qurilma", exact: true }).last();
  await expect(target.locator("option", { hasText: "Darvoza" })).toHaveCount(0);   // high risk: never offered
  await target.selectOption({ label: "Bog' chiroqlari" });
  await dialog.getByRole("button", { name: "Saqlash" }).click();
  await expect(dialog).toHaveCount(0);

  const card = page.getByTestId(`automation-${name}`);
  await expect(card).toContainText("Kirish eshigi: Ochiq → Bog' chiroqlari");
  const sw = card.getByRole("switch");
  await expect(sw).toHaveAttribute("aria-checked", "true");
  await sw.click();
  await expect(sw).toHaveAttribute("aria-checked", "false");
  await sw.click();
  await expect(sw).toHaveAttribute("aria-checked", "true");

  await card.getByRole("button", { name: new RegExp(`Avtomatikani tahrirlash: ${name}`) }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Avtomatikani o'chirish" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Ha, o'chirish" }).click();
  await expect(card).toHaveCount(0);
});
