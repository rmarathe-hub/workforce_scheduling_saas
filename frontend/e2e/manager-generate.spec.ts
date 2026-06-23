import { expect, test } from "@playwright/test";

import {
  completeQuickSetup,
  createCoverageRequirement,
  generateWeeklySchedule,
  registerOwner,
  tuesdayOfCurrentWeek,
} from "./helpers";

test.describe("manager generate", () => {
  test("generates weekly schedule and shows assignment summary", async ({ page }) => {
    await registerOwner(page);
    await completeQuickSetup(page);
    await createCoverageRequirement(page, { headcount: 2, shiftDate: tuesdayOfCurrentWeek() });

    await generateWeeklySchedule(page);

    const summary = page.getByTestId("generation-summary");
    await expect(summary).toContainText("Generation summary");
    await expect(summary).toContainText("Assigned");
    await expect(summary).toContainText("open shift");

    await expect(page.getByTestId("shift-counts-summary")).toContainText("assigned");
    await expect(page.getByTestId("shift-counts-summary")).toContainText("open");
    await expect(page.getByTestId("schedule-status-badge")).toHaveText("Draft");
  });
});
