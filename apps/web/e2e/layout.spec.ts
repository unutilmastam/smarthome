import { expect, test } from "@playwright/test";

// Regression: a long nav once widened the whole page on phones (CSS grid min-width).
test("no horizontal overflow on any main page", async ({ page }, info) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  await expect(page.getByRole("heading", { name: "Uy" })).toBeVisible();
  const expected = info.project.use.viewport?.width;
  for (const path of ["/", "/rooms", "/devices", "/energy", "/cameras", "/hub", "/settings", "/members", "/security", "/events", "/automations"]) {
    await page.goto(path);
    await page.waitForTimeout(300);
    const m = await page.evaluate(() => ({ vw: window.innerWidth, sw: document.documentElement.scrollWidth }));
    expect(m.vw, `${path}: layout viewport`).toBe(expected);
    expect(m.sw, `${path}: horizontal overflow`).toBeLessThanOrEqual(m.vw);
  }
});
