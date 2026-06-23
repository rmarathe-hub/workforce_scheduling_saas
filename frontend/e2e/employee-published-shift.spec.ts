import { expect, test } from "@playwright/test";

import {
  loginAsEmployee,
  logout,
  setupPublishedSchedule,
} from "./helpers";

test.describe("employee published shifts", () => {
  test("employee sees published shift after manager publishes schedule", async ({ page }) => {
    const { employee } = await setupPublishedSchedule(page);

    await logout(page);
    await loginAsEmployee(page, employee);

    await expect(page.getByTestId("employee-shifts-empty")).toHaveCount(0);
    await expect(page.getByTestId("employee-shift-card")).toHaveCount(1);
    await expect(page.getByTestId("employee-shift-card").first()).toContainText("PUBLISHED");
  });
});
