import { expect, test } from "@playwright/test";

import {
  completeQuickSetup,
  login,
  loginAsEmployee,
  logout,
  registerOwner,
} from "./helpers";

test.describe("manager employee availability", () => {
  test("manager views employee availability windows", async ({ page }) => {
    const owner = await registerOwner(page);
    const { employee } = await completeQuickSetup(page);

    await logout(page);
    await loginAsEmployee(page, employee);
    await page.getByRole("link", { name: "Availability" }).click();
    await page.getByTestId("availability-form").getByRole("button", { name: "Add window" }).click();
    await expect(page.getByText(/Monday · 09:00 – 17:00/)).toBeVisible();

    await logout(page);
    await login(page, owner.email, owner.password);
    await page.getByRole("link", { name: "Availability" }).click();
    await expect(page.getByTestId("manager-employee-availability-page")).toBeVisible();

    const employeeSelect = page.locator("select").first();
    await employeeSelect.selectOption({ label: employee.fullName });
    await expect(page.getByText(/Monday · 09:00 – 17:00/)).toBeVisible({ timeout: 30_000 });
  });
});
