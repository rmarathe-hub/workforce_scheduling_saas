import { expect, test } from "@playwright/test";

test.describe("protected routes", () => {
  test("unauthenticated user is redirected from manager schedule to login", async ({ page }) => {
    await page.goto("/manager/schedule");
    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("unauthenticated user is redirected from employee shifts to login", async ({ page }) => {
    await page.goto("/employee/shifts");
    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
  });

  test("unauthenticated user is redirected from new coverage to login", async ({ page }) => {
    await page.goto("/manager/coverage/new");
    await expect(page).toHaveURL(/\/login/, { timeout: 30_000 });
  });
});
