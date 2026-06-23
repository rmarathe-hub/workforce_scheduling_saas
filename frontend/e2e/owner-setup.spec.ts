import { expect, test } from "@playwright/test";

import { completeQuickSetup, registerOwner } from "./helpers";

test.describe("owner setup", () => {
  test("creates location, job role, and employee", async ({ page }) => {
    const owner = await registerOwner(page);
    const setup = await completeQuickSetup(page);

    await expect(page.getByText(owner.orgName)).toBeVisible();
    await expect(page.getByTestId("add-employee-form")).toBeVisible();

    await page.goto("/manager/coverage/new");
    const form = page.getByTestId("create-coverage-form");
    const locationOptions = form.getByLabel("Location").locator("option");
    await expect(locationOptions).toHaveCount(2, { timeout: 30_000 });
    await expect(locationOptions.nth(1)).toHaveText(setup.locationName);

    const roleOptions = form.getByLabel("Job role").locator("option");
    await expect(roleOptions).toHaveCount(2, { timeout: 30_000 });
    await expect(roleOptions.nth(1)).toHaveText(setup.roleName);
  });
});
