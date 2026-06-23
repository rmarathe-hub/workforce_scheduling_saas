import { expect, test } from "@playwright/test";

import { login, logout, registerOwner } from "./helpers";

test.describe("authentication", () => {
  test("register, logout, login, and reach manager dashboard", async ({ page }) => {
    const owner = await registerOwner(page);

    await expect(page.getByText(owner.orgName)).toBeVisible();
    await expect(page.getByTestId("dashboard")).toBeVisible();

    await logout(page);
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

    await login(page, owner.email, owner.password);
    await expect(page).toHaveURL(/\/manager\/schedule/, { timeout: 30_000 });
    await expect(page.getByRole("heading", { name: "Weekly schedule" })).toBeVisible();
    await expect(page.getByText(owner.fullName)).toBeVisible();
  });
});
