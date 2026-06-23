import { expect, test } from "@playwright/test";

import {
  completeQuickSetup,
  createCoverageRequirement,
  generateWeeklySchedule,
  registerOwner,
  tuesdayOfCurrentWeek,
  validateWeek,
} from "./helpers";

test.describe("schedule conflicts", () => {
  test("shows warning conflicts for open shifts after generation", async ({ page }) => {
    await registerOwner(page);
    await completeQuickSetup(page);
    await createCoverageRequirement(page, { headcount: 2, shiftDate: tuesdayOfCurrentWeek() });

    await generateWeeklySchedule(page);

    await expect(page.getByTestId("schedule-conflicts-panel")).toBeVisible();
    await expect(page.getByTestId("conflicts-summary")).toContainText("warning");
    await expect(page.getByTestId("conflict-item").first()).toContainText("WARNING");
    await expect(page.getByTestId("publish-week-button")).toBeEnabled();
  });

  test("blocks publish when overlap error conflicts exist", async ({ page }) => {
    await registerOwner(page);
    const { employee } = await completeQuickSetup(page);
    await createCoverageRequirement(page, { headcount: 1, shiftDate: tuesdayOfCurrentWeek() });
    await generateWeeklySchedule(page);

    await Promise.all([
      page.waitForResponse(
        (response) =>
          response.request().method() === "POST" &&
          response.url().includes("/shifts") &&
          response.ok(),
        { timeout: 30_000 },
      ),
      page.getByRole("button", { name: "Add shift" }).click(),
    ]);
    await expect(page.locator('[data-testid="shift-row"], [data-testid="shift-with-conflict"]')).toHaveCount(
      2,
      { timeout: 30_000 },
    );

    const assignSelect = page.getByTestId("assign-shift-button");
    await assignSelect.selectOption({ label: employee.fullName });
    await expect(page.getByTestId("conflicts-loading")).toBeHidden({ timeout: 60_000 });
    await expect(page.getByTestId("shift-with-conflict").first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("conflict-item").filter({ hasText: "ERROR" }).first()).toBeVisible();

    await validateWeek(page);
    await expect(page.getByTestId("validate-message")).toContainText("error");

    await expect(page.getByTestId("publish-week-button")).toBeDisabled();
    await expect(page.getByTestId("publish-blocked-message")).toBeVisible();
  });
});
