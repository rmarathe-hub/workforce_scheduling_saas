import { expect, test } from "@playwright/test";

import {
  completeQuickSetup,
  loginAsEmployee,
  logout,
  registerOwner,
  tuesdayOfCurrentWeek,
} from "./helpers";

test.describe("employee shifts navigation", () => {
  test("employee can move between week views", async ({ page }) => {
    await registerOwner(page);
    const { employee } = await completeQuickSetup(page);

    await logout(page);
    await loginAsEmployee(page, employee);

    const weekLabel = await page.getByText(/Week of/).textContent();
    await page.getByRole("button", { name: "Next" }).click();
    await expect(page.getByText(/Week of/)).not.toHaveText(weekLabel ?? "");
    await page.getByRole("button", { name: "This week" }).click();
  });

  test("employee can remove availability window", async ({ page }) => {
    await registerOwner(page);
    const { employee } = await completeQuickSetup(page);

    await logout(page);
    await loginAsEmployee(page, employee);
    await page.getByRole("link", { name: "Availability" }).click();
    await page.getByTestId("availability-form").getByRole("button", { name: "Add window" }).click();
    await expect(page.getByText(/Monday · 09:00 – 17:00/)).toBeVisible();
    await page.getByRole("button", { name: "Remove" }).click();
    await expect(page.getByText("No availability set yet.")).toBeVisible({ timeout: 30_000 });
  });
});
