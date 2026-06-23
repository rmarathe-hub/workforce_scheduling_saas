import { expect, test } from "@playwright/test";

import { completeQuickSetup, loginAsEmployee, logout, registerOwner } from "./helpers";

test.describe("role-based access", () => {
  test("employee cannot access manager schedule setup or actions", async ({ page }) => {
    await registerOwner(page);
    const { employee } = await completeQuickSetup(page);

    await logout(page);
    await loginAsEmployee(page, employee);
    await expect(page.getByText(/EMPLOYEE/)).toBeVisible();

    await page.goto("/manager/schedule");
    await expect(page).toHaveURL(/\/employee\/shifts/, { timeout: 30_000 });
    await expect(page.getByRole("heading", { name: "My shifts" })).toBeVisible();

    await expect(page.getByRole("link", { name: "Schedule" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "New coverage" })).toHaveCount(0);
    await expect(page.getByTestId("generate-week-button")).toHaveCount(0);
    await expect(page.getByTestId("publish-week-button")).toHaveCount(0);
  });
});
