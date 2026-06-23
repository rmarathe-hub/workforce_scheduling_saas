import { expect, test } from "@playwright/test";

import {
  completeQuickSetup,
  login,
  loginAsEmployee,
  logout,
  registerOwner,
  tuesdayOfCurrentWeek,
} from "./helpers";

test.describe("manager time off", () => {
  test("manager approves employee time-off request", async ({ page }) => {
    const owner = await registerOwner(page);
    const { employee } = await completeQuickSetup(page);

    await logout(page);
    await loginAsEmployee(page, employee);
    await page.getByRole("link", { name: "Time off" }).click();
    await page.getByLabel("Start date").fill(tuesdayOfCurrentWeek());
    await page.getByLabel("End date").fill(tuesdayOfCurrentWeek());
    await page.getByTestId("time-off-form").getByRole("button", { name: "Submit request" }).click();
    await expect(page.getByText("PENDING")).toBeVisible();

    await logout(page);
    await login(page, owner.email, owner.password);
    await expect(page).toHaveURL(/\/manager\/schedule/);

    await page.getByRole("link", { name: "Time off" }).click();
    await expect(page.getByTestId("manager-time-off-page")).toBeVisible();
    await page.getByTestId("approve-time-off-button").first().click();
    await expect(page.getByText("No pending requests.")).toBeVisible({ timeout: 30_000 });
  });

  test("manager rejects employee time-off request", async ({ page }) => {
    const owner = await registerOwner(page);
    const { employee } = await completeQuickSetup(page);

    await logout(page);
    await loginAsEmployee(page, employee);
    await page.getByRole("link", { name: "Time off" }).click();
    await page.getByLabel("Start date").fill(tuesdayOfCurrentWeek());
    await page.getByLabel("End date").fill(tuesdayOfCurrentWeek());
    await page.getByTestId("time-off-form").getByRole("button", { name: "Submit request" }).click();

    await logout(page);
    await login(page, owner.email, owner.password);
    await page.getByRole("link", { name: "Time off" }).click();
    await page.getByTestId("reject-time-off-button").first().click();
    await expect(page.getByText("No pending requests.")).toBeVisible({ timeout: 30_000 });
  });
});
