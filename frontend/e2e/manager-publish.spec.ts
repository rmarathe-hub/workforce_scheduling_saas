import { expect, test } from "@playwright/test";

import {
  completeQuickSetup,
  createCoverageRequirement,
  generateWeeklySchedule,
  publishSchedule,
  registerOwner,
  tuesdayOfCurrentWeek,
  validateWeek,
} from "./helpers";

test.describe("manager publish", () => {
  test("validates week and publishes a clean generated schedule", async ({ page }) => {
    await registerOwner(page);
    await completeQuickSetup(page);
    await createCoverageRequirement(page, { headcount: 1, shiftDate: tuesdayOfCurrentWeek() });
    await generateWeeklySchedule(page);

    await expect(page.getByTestId("schedule-conflicts-panel")).toBeVisible();
    await validateWeek(page);
    await expect(page.getByTestId("validate-message")).toContainText("valid");

    await publishSchedule(page);
  });
});
