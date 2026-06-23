import { expect, test } from "@playwright/test";

import { registerOwner } from "./helpers";

test.describe("manager route protection", () => {
  test("manager is redirected from employee shifts to manager schedule", async ({ page }) => {
    await registerOwner(page);
    await page.goto("/employee/shifts");
    await expect(page).toHaveURL(/\/manager\/schedule/, { timeout: 30_000 });
    await expect(page.getByRole("heading", { name: "Weekly schedule" })).toBeVisible();
  });

  test("manager is redirected from employee availability to manager schedule", async ({ page }) => {
    await registerOwner(page);
    await page.goto("/employee/availability");
    await expect(page).toHaveURL(/\/manager\/schedule/, { timeout: 30_000 });
  });

  test("manager is redirected from employee time-off to manager schedule", async ({ page }) => {
    await registerOwner(page);
    await page.goto("/employee/time-off");
    await expect(page).toHaveURL(/\/manager\/schedule/, { timeout: 30_000 });
  });
});
