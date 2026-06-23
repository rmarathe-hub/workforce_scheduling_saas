import { expect, test } from "@playwright/test";

import {
  completeQuickSetup,
  createCoverageRequirement,
  generateWeeklySchedule,
  publishSchedule,
  registerOwner,
  setupGenerateReadySchedule,
  tuesdayOfCurrentWeek,
  validateWeek,
} from "./helpers";

test.describe("publish UI", () => {
  test("publish dialog cancel keeps draft status", async ({ page }) => {
    await setupGenerateReadySchedule(page);
    await generateWeeklySchedule(page);
    await validateWeek(page);

    await publishSchedule(page, { accept: false });
    await expect(page.getByTestId("schedule-status-badge")).toHaveText("Draft");
  });

  test("clean conflict panel shows no conflicts message", async ({ page }) => {
    await registerOwner(page);
    await completeQuickSetup(page);
    await createCoverageRequirement(page, { headcount: 1, shiftDate: tuesdayOfCurrentWeek() });
    await generateWeeklySchedule(page);
    await expect(page.getByTestId("conflicts-summary")).toContainText("No conflicts");
  });
});
