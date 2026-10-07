import { expect, test } from "@playwright/test";

// [SIM] The owner adds a section and a device from the UI, edits and removes them.
test("add a section and a device, then remove both", async ({ page }) => {
  const room = `Oshxona ${Date.now() % 100000}`;
  await page.goto("/");
  await page.getByLabel("Email").fill("owner@example.com");
  await page.getByLabel("Parol").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Kirish" }).click();
  await expect(page.getByRole("heading", { name: "Uy" })).toBeVisible();

  // + -> section
  await page.getByRole("button", { name: "Nima qo'shamiz?" }).click();
  await page.getByRole("dialog").getByRole("button", { name: /Bo'lim qo'shish/ }).click();
  await page.getByLabel("Bo'lim nomi").fill(room);
  await page.getByRole("radio", { name: "Oshxona" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Qo'shish" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);

  // + -> device of type "Rozetka" in that section
  await page.getByRole("button", { name: "Nima qo'shamiz?" }).click();
  await page.getByRole("dialog").getByRole("button", { name: /Qurilma qo'shish/ }).click();
  await page.getByRole("button", { name: "Rozetka", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Nomi").fill(`Choynak ${room}`);
  await dialog.getByRole("radio", { name: new RegExp(room) }).click();
  await dialog.getByRole("radio", { name: "Muzlatkich" }).click();
  await dialog.getByRole("button", { name: "Qo'shish" }).click();

  // Lands on the device page; the state is honestly unknown (no hub report yet).
  await expect(page.getByRole("heading", { name: `Choynak ${room}` })).toBeVisible();
  await expect(page.getByTestId("value-Holat")).toContainText("Noma'lum");
  await expect(page.getByRole("switch")).toHaveCount(0);

  // The section shows it.
  await page.goto("/rooms");
  await expect(page.getByTestId(`room-${room}`)).toContainText("1 ta qurilma");

  // Remove the device (with confirmation), then the section.
  await page.getByRole("link", { name: `Choynak ${room}` }).first().click();
  await page.getByRole("button", { name: "Qurilmani tahrirlash" }).click();
  await page.getByRole("button", { name: "Qurilmani olib tashlash" }).click();
  await page.getByRole("button", { name: "Ha, olib tashlash" }).click();
  await expect(page).toHaveURL(/\/devices$/);
  await page.goto("/rooms");
  await page.getByRole("button", { name: `Bo'limni tahrirlash: ${room}` }).click();
  await page.getByRole("button", { name: "Bo'limni o'chirish" }).click();
  await page.getByRole("button", { name: "Ha, o'chirish" }).click();
  await expect(page.getByTestId(`room-${room}`)).toHaveCount(0);
});
