import { expect, test } from "@playwright/test";

// [SIM] Security system on the hub: set up zones in the app, arm with PIN, disarm.
test("set up the alarm, arm at home with PIN, disarm", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  await expect(page.getByRole("heading", { name: "Uy" })).toBeVisible();
  await page.goto("/security");
  await expect(page.getByRole("heading", { name: "Xavfsizlik", exact: true })).toBeVisible();

  const setup = page.getByRole("button", { name: "Signalizatsiyani sozlash" });
  const state = page.getByTestId("alarm-state");
  // isVisible() does not wait: first let the page load (either the setup card or the alarm).
  await expect(setup.or(state)).toBeVisible({ timeout: 20_000 });
  if (await setup.isVisible()) {           // first run of the suite: configure it
    await setup.click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("checkbox", { name: /Kirish eshigi/ }).check();
    await dialog.getByRole("checkbox", { name: /Sirena/ }).check();
    await dialog.getByLabel("Chiqish vaqti, soniya").fill("2");
    await dialog.getByLabel("Kirish vaqti, soniya").fill("5");
    await dialog.getByRole("button", { name: "Saqlash" }).click();
    await expect(dialog).toHaveCount(0);
  }
  await expect(state).toHaveAttribute("data-state", "disarmed", { timeout: 20_000 });
  await expect(page.getByText("Kirish eshigi").first()).toBeVisible();

  await page.getByRole("button", { name: /Uydaman/ }).click();
  await page.getByLabel("PIN", { exact: true }).fill("4821");
  await page.getByRole("button", { name: "Tasdiqlash" }).click();
  await expect(state).toHaveAttribute("data-state", /arming|armed_home/, { timeout: 10_000 });
  await expect(page.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 20_000 });
  await expect(state).toHaveAttribute("data-state", "armed_home");

  await page.getByRole("button", { name: /Qo'riqlashni o'chirish/ }).click();
  await page.getByLabel("PIN", { exact: true }).fill("4821");
  await page.getByRole("button", { name: "Tasdiqlash" }).click();
  await expect(state).toHaveAttribute("data-state", "disarmed", { timeout: 15_000 });

  // The event feed shows what happened (from the hub, via the backend).
  await page.goto("/events");
  await expect(page.getByTestId("event-alarm.armed").first()).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId("event-alarm.disarmed").first()).toBeVisible({ timeout: 15_000 });
});
