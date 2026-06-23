import { expect, test } from "@playwright/test";

import {
  completeQuickSetup,
  loginAsEmployee,
  logout,
  registerOwner,
  tuesdayOfCurrentWeek,
} from "./helpers";

test.describe("employee flow", () => {
  test("employee can view shifts, availability, and request time off", async ({ page }) => {
    await registerOwner(page);
    const { employee } = await completeQuickSetup(page);

    await logout(page);
    await loginAsEmployee(page, employee);

    await expect(page.getByTestId("employee-shifts-empty")).toBeVisible();

    await page.getByRole("link", { name: "Availability" }).click();
    await expect(page.getByTestId("employee-availability-page")).toBeVisible();
    await page.getByTestId("availability-form").getByRole("button", { name: "Add window" }).click();
    await expect(page.getByRole("heading", { name: "Your windows" }).locator("..").getByText(/Monday · 09:00 – 17:00/)).toBeVisible({
      timeout: 30_000,
    });

    await page.getByRole("link", { name: "Time off" }).click();
    await expect(page.getByTestId("employee-time-off-page")).toBeVisible();
    await page.getByLabel("Start date").fill(tuesdayOfCurrentWeek());
    await page.getByLabel("End date").fill(tuesdayOfCurrentWeek());
    await page.getByLabel("Reason (optional)").fill("E2E time off");
    await page.getByTestId("time-off-form").getByRole("button", { name: "Submit request" }).click();
    await expect(page.getByText("PENDING")).toBeVisible({ timeout: 30_000 });
  });
});
