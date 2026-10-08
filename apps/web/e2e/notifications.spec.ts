import { expect, test } from "@playwright/test";

// [SIM] Bell badge -> notifications page -> "Ko'rdim" -> settings say honestly what is configured.
// The stack seeds one critical notification; Telegram/Push are not configured in the SIM stack.
test("notifications: bell, ack, channel settings", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  await expect(page.getByRole("heading", { name: "Uy" })).toBeVisible();

  await page.getByTestId("bell").click();
  await expect(page.getByRole("heading", { name: "Bildirishnomalar" })).toBeVisible();
  const item = page.getByTestId("notification-cover.sensor_conflict");
  await expect(item).toContainText("Gerkonlar bir-biriga zid — darvoza bloklandi");
  await expect(item).toContainText("Darvoza");
  const ack = item.getByRole("button", { name: "Ko'rdim" });
  if (await ack.isVisible()) await ack.click();     // the second project finds it already acked
  await expect(item).toContainText("Ko'rdi: Ega");
  await expect(page.getByTestId("bell").locator(".badge")).toHaveCount(0);

  await page.getByRole("link", { name: /Kanallar/ }).click();
  const section = page.locator("#notifications");
  await expect(section.getByText("Serverda hali sozlanmagan.")).toHaveCount(2);
  await section.getByRole("button", { name: /Sinov xabarini yuborish/ }).click();
  await expect(section.getByRole("alert")).toContainText("Hech qaysi kanal ulanmagan");
});
