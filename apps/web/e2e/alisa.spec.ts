import { expect, test } from "@playwright/test";

// [SIM] Yandex Alisa link (ADR 0016) against a fake Yandex API (e2e/fake_yandex.py):
// paste the token once, Alisa devices appear; commands are confirmed by reading Yandex back.

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  await expect(page.getByRole("heading", { name: "Uy" })).toBeVisible();
});

test("link Alisa, switch an Alisa lamp (confirmed), TV volume step", async ({ page }) => {
  const loaded = page.waitForResponse((r) => r.url().includes("/integrations/yandex"));
  await page.goto("/settings");
  await loaded;
  const box = page.getByTestId("alisa");
  if (await box.getByLabel("Yandex OAuth token").count()) {
    await box.getByLabel("Yandex OAuth token").fill("y0_e2e_fake_token_not_secret_0000");
    await box.getByRole("button", { name: "Alisa'ni ulash" }).click();
  }
  await expect(box.locator(".badge")).toHaveText("Ulangan", { timeout: 10_000 });
  await expect(box.getByRole("button", { name: /Kino rejimi/ })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("y0_e2e_fake_token");

  await page.goto("/devices");
  const lamp = page.locator("article", { hasText: "Alisa chirog'i" });
  const sw = lamp.getByRole("switch");
  const was = await sw.getAttribute("aria-checked");
  await sw.click();
  await expect(lamp.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 10_000 });
  await expect(sw).toHaveAttribute("aria-checked", was === "true" ? "false" : "true");

  await page.getByRole("link", { name: "Yandex TV" }).first().click();
  const vol = page.locator(".rval", { hasText: "Ovoz" }).locator("strong");
  const before = Number(await vol.textContent());
  await page.getByRole("button", { name: "Ovoz +" }).click();
  await expect(page.getByTestId("command-status")).toHaveAttribute("data-status", "acked", { timeout: 10_000 });
  await expect(vol).toHaveText(String(before + 1), { timeout: 10_000 });
});
