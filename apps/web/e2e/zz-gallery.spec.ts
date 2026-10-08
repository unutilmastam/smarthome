import { expect, test, type Page } from "@playwright/test";

// [SIM] Full screenshot gallery of every screen (phone + iPad). Runs last ("zz-"), only when
// GALLERY_DIR is set, so the other specs have already produced real data (light on via the
// device, alarm configured, events). Nothing here is used as a test of behavior.
test.skip(!process.env.GALLERY_DIR, "GALLERY_DIR not set");

test("gallery", async ({ page }, info) => {
  test.setTimeout(180_000);
  const base = page.viewportSize()!;
  const shot = async (name: string, full = true) => {
    await page.waitForTimeout(600);   // let polling fill values and animations settle
    const path = `${process.env.GALLERY_DIR}/${info.project.name}-${name}.png`;
    if (!full) {
      await page.screenshot({ path });
      return;
    }
    // A fullPage capture paints fixed bars (tab bar) in the middle of long pages; a viewport
    // as tall as the page shows them where the user sees them: at the bottom.
    const h = await page.evaluate(() => document.documentElement.scrollHeight);
    await page.setViewportSize({ width: base.width, height: Math.max(base.height, h) });
    await page.waitForTimeout(300);
    await page.screenshot({ path });
    await page.setViewportSize(base);
  };
  const go = async (path: string, ready: (p: Page) => Promise<void>) => {
    await page.goto(path);
    await ready(page);
  };

  await page.goto("/");
  await expect(page.getByRole("button", { name: "Kirish" })).toBeVisible();
  await shot("01-login", false);
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  const light = page.getByTestId("device-garden_lights");
  await expect(light.getByTestId("value-Holat")).toContainText("Tasdiqlangan", { timeout: 20_000 });
  const sw = light.getByRole("switch");
  if (await sw.getAttribute("aria-checked") !== "true") {      // a real command, confirmed by the device
    await sw.click();
    await expect(light.getByTestId("command-status")).toHaveAttribute("data-status", "confirmed", { timeout: 15_000 });
  }
  await shot("02-bosh-sahifa");

  await go("/rooms", (p) => expect(p.getByRole("heading", { name: "Bo'limlar" })).toBeVisible());
  await shot("03-bolimlar");
  await go("/devices", (p) => expect(p.getByTestId("device-garden_lights")).toBeVisible());
  await shot("04-qurilmalar");
  await page.getByRole("link", { name: "Bog' chiroqlari" }).first().click();
  await expect(page.getByText("Buyruqlar tarixi")).toBeVisible();
  await shot("05-chiroq");
  await go("/devices", (p) => expect(p.getByRole("link", { name: "Darvoza" }).first()).toBeVisible());
  await page.getByRole("link", { name: "Darvoza" }).first().click();
  await expect(page.getByText("Buyruqlar tarixi")).toBeVisible();
  await shot("06-darvoza");

  await page.getByRole("button", { name: "Nima qo'shamiz?" }).click();
  await shot("07-qoshish-menyu", false);
  await page.getByRole("dialog").getByRole("button", { name: /Qurilma qo'shish/ }).click();
  await expect(page.getByRole("heading", { name: "Qurilma turini tanlang" })).toBeVisible();
  await shot("08-qurilma-turi", false);
  await page.getByRole("button", { name: "Chiroq", exact: true }).click();
  await shot("09-qurilma-malumot", false);
  await page.keyboard.press("Escape");

  await go("/energy", (p) => expect(p.getByRole("heading", { name: /Elektr/ }).first()).toBeVisible());
  await shot("10-elektr");
  await go("/cameras", (p) => expect(p.getByRole("heading", { name: /Kameralar/ }).first()).toBeVisible());
  await shot("11-kameralar");
  await go("/security", (p) => expect(p.getByRole("heading", { name: "Xavfsizlik", exact: true })).toBeVisible());
  await expect(page.getByTestId("alarm-state").or(page.getByRole("button", { name: "Signalizatsiyani sozlash" }))).toBeVisible({ timeout: 20_000 });
  await shot("12-xavfsizlik");
  await go("/events", (p) => expect(p.getByRole("heading", { name: "Voqealar" })).toBeVisible());
  await shot("13-voqealar");

  // An automation saved for the picture (the automation spec deletes its own).
  await go("/automations", (p) => expect(p.getByRole("button", { name: "Yangi avtomatika" })).toBeVisible());
  if (await page.getByTestId("automation-Kechqurun eshik ochilsa").count() === 0) {
    await page.getByRole("button", { name: "Yangi avtomatika" }).click();
    const dlg = page.getByRole("dialog");
    await dlg.getByLabel("Nomi").fill("Kechqurun eshik ochilsa");
    await dlg.getByRole("button", { name: /Qurilma holati/ }).first().click();
    await dlg.getByRole("combobox", { name: "Qurilma", exact: true }).first().selectOption({ label: "Kirish eshigi" });
    await dlg.getByRole("combobox", { name: "bo'lganda" }).selectOption({ label: "Ochiq" });
    await dlg.getByRole("button", { name: /Buyruq/ }).click();
    await dlg.getByRole("combobox", { name: "Qurilma", exact: true }).last().selectOption({ label: "Bog' chiroqlari" });
    await dlg.getByRole("button", { name: /Xabar/ }).click();
    await dlg.getByLabel("Xabar matni").fill("Kirish eshigi ochildi");
    await shot("15-avtomatika-muharrir", false);
    await dlg.getByRole("button", { name: "Saqlash" }).click();
    await expect(dlg).toHaveCount(0);
  }
  await expect(page.getByTestId("automation-Kechqurun eshik ochilsa")).toBeVisible();
  await shot("14-avtomatika");

  await go("/notifications", (p) => expect(p.getByTestId("notification-cover.sensor_conflict")).toBeVisible());
  await shot("16-bildirishnomalar");
  await go("/hub", (p) => expect(p.getByText("Lokal MQTT broker")).toBeVisible({ timeout: 15_000 }));
  await shot("17-hub");
  await go("/settings", (p) => expect(p.locator("#notifications").getByText("Telegram")).toBeVisible());
  await shot("18-sozlamalar");
  await go("/members", (p) => expect(p.getByRole("heading", { name: /A'zolar/ }).first()).toBeVisible());
  await shot("19-azolar");
  await go("/more", (p) => expect(p.getByRole("link", { name: /Xavfsizlik/ }).first()).toBeVisible());
  await shot("20-yana", false);

  // Dark theme
  await go("/settings", (p) => expect(p.getByLabel("Mavzu")).toBeVisible());
  await page.getByLabel("Mavzu").selectOption("dark");
  await go("/", (p) => expect(p.getByTestId("device-garden_lights")).toBeVisible());
  await shot("21-bosh-sahifa-qorongi");
  await go("/security", (p) => expect(p.getByRole("heading", { name: "Xavfsizlik", exact: true })).toBeVisible());
  await shot("22-xavfsizlik-qorongi");
  await go("/settings", (p) => expect(p.getByLabel("Mavzu")).toBeVisible());
  await page.getByLabel("Mavzu").selectOption("system");
});
