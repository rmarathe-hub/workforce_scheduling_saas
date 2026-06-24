import { expect, test } from "@playwright/test";

import {
  expectManagerAnalyticsCards,
  generateWeeklySchedule,
  isProductionSmoke,
  loginAsEmployee,
  logout,
  openEmployeeDocumentsPage,
  openManagerEmployeeDocumentsPage,
  openNotificationsPage,
  publishSchedule,
  registerOwner,
  setupGenerateReadySchedule,
  smokeOrgName,
  validateWeek,
} from "./helpers";

test.describe("production smoke", () => {
  test.skip(!isProductionSmoke, "Set E2E_SMOKE=1 to run production smoke tests");

  test("frontend loads login page", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("register and reach manager schedule", async ({ page }) => {
    await registerOwner(page, { orgName: smokeOrgName() });
    await expect(page.getByTestId("dashboard")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Weekly schedule" })).toBeVisible();
    await expectManagerAnalyticsCards(page);
  });

  test("generate and validate schedule on deployed stack", async ({ page }) => {
    await setupGenerateReadySchedule(page, 1, { orgName: smokeOrgName() });
    await page.getByTestId("generate-week-button").click();
    await expect(page.getByTestId("generation-summary")).toBeVisible({ timeout: 120_000 });
    await validateWeek(page);
    await expect(page.getByTestId("validate-message")).toBeVisible();
    await expectManagerAnalyticsCards(page);
  });

  test("publish schedule, activity log, notifications, and documents on deployed stack", async ({
    page,
  }) => {
    const fixture = await setupGenerateReadySchedule(page, 1, { orgName: smokeOrgName() });
    await generateWeeklySchedule(page);
    await validateWeek(page);
    await publishSchedule(page);
    await expectManagerAnalyticsCards(page);
    await expect(page.getByTestId("analytics-card-published_shifts")).toContainText(/[1-9]/);

    await page.goto("/manager/activity");
    await expect(page.getByTestId("manager-activity-log-page")).toBeVisible();
    await expect(page.getByText("Schedule published")).toBeVisible({ timeout: 60_000 });

    await openNotificationsPage(page);
    await openManagerEmployeeDocumentsPage(page);

    await logout(page);
    await loginAsEmployee(page, fixture.employee);
    await openNotificationsPage(page);
    await openEmployeeDocumentsPage(page);
  });
});
