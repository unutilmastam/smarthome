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
  await card.getByRole("button", { name: "Yoqish" }).click();
  await expect(card.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 15_000 });
  await page.screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-dashboard.png`, fullPage: true });
  await page.getByRole("link", { name: "Bog' chiroqlari" }).click();
  await expect(page.getByText("Buyruqlar tarixi")).toBeVisible();
  await page.screenshot({ path: `${process.env.SCREENSHOTS_DIR}/${info.project.name}-device.png`, fullPage: true });
});
