import { expect, test } from "@playwright/test";

import {
  completeQuickSetup,
  createCoverageRequirement,
  registerOwner,
  tuesdayOfCurrentWeek,
} from "./helpers";

test.describe("manager coverage", () => {
  test("creates coverage requirement for the current week", async ({ page }) => {
    await registerOwner(page);
    const setup = await completeQuickSetup(page);
    const shiftDate = tuesdayOfCurrentWeek();

    await createCoverageRequirement(page, { headcount: 2, shiftDate });

    const coverageSection = page.getByRole("heading", { name: "Coverage needs" }).locator("..");
    await expect(coverageSection.getByText(setup.roleName)).toBeVisible();
    await expect(coverageSection.getByText(setup.locationName)).toBeVisible();
    await expect(coverageSection.getByRole("cell", { name: "2", exact: true })).toBeVisible();
    await expect(coverageSection.getByRole("button", { name: "Add shift" })).toBeVisible();
  });
});
