import { expect, test } from "@playwright/test";

import { login, registerOwner } from "./helpers";

test.describe("navigation stability", () => {
  test("manager can navigate schedule, coverage, and back", async ({ page }) => {
    await registerOwner(page);
    await page.getByRole("banner").getByRole("link", { name: "New coverage" }).click();
    await expect(page).toHaveURL(/\/manager\/coverage\/new/);
    await page.getByRole("link", { name: "Back to schedule" }).click();
    await expect(page).toHaveURL(/\/manager\/schedule/);
    await expect(page.getByTestId("dashboard")).toBeVisible();
  });

  test("reload keeps manager session on schedule page", async ({ page }) => {
    const owner = await registerOwner(page);
    await page.reload();
    await expect(page.getByTestId("dashboard")).toBeVisible();
    await expect(page.getByText(owner.orgName)).toBeVisible();
  });

  test("logout and login restores manager access", async ({ page }) => {
    const owner = await registerOwner(page);
    await page.getByRole("button", { name: "Logout" }).click();
    await login(page, owner.email, owner.password);
    await expect(page).toHaveURL(/\/manager\/schedule/);
  });
});
