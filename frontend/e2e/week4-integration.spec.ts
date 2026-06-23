import { expect, test } from "@playwright/test";

import {
  employeeGiveUpFirstShift,
  expectManagerAnalyticsCards,
  loginAsEmployee,
  loginAsManager,
  logout,
  managerApproveFirstShiftSwap,
  setupPublishedSchedule,
  uploadEmployeeTestDocument,
} from "./helpers";

test.describe("week 4 integration", () => {
  test("publish, swap, audit log, document upload, and analytics", async ({ page }) => {
    const { owner, employee } = await setupPublishedSchedule(page);
    await expectManagerAnalyticsCards(page);

    await logout(page);
    await loginAsEmployee(page, employee);
    await employeeGiveUpFirstShift(page);

    await logout(page);
    await loginAsManager(page, owner.email);
    await managerApproveFirstShiftSwap(page);

    await page.goto("/manager/activity");
    await expect(page.getByTestId("manager-activity-log-page")).toBeVisible();
    await expect(page.getByText("Shift swap approved")).toBeVisible();
    await expect(page.getByText("Schedule published")).toBeVisible();

    await logout(page);
    await loginAsEmployee(page, employee);
    await uploadEmployeeTestDocument(page);

    await logout(page);
    await loginAsManager(page, owner.email);
    await page.goto("/manager/employee-documents");
    await expect(page.getByTestId("manager-employee-documents-page")).toBeVisible();
    await page.getByTestId("manager-employee-select").selectOption({
      label: `${employee.fullName} (${employee.email})`,
    });
    await expect(page.getByTestId("manager-employee-document-card")).toHaveCount(1, { timeout: 30_000 });

    await page.goto("/manager/schedule");
    await expectManagerAnalyticsCards(page);
    await expect(page.getByTestId("analytics-card-published_shifts")).toContainText(/[1-9]/);
  });
});
