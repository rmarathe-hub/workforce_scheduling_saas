import { expect, test } from "@playwright/test";

import { E2E_PASSWORD, uniqueEmail } from "./helpers";

test.describe("auth negative paths", () => {
  test("shows validation error for empty organization on register", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel("Full name").fill("No Org User");
    await page.getByLabel("Organization").fill("");
    await page.getByLabel("Email").fill(uniqueEmail("noorg"));
    await page.getByLabel("Password").fill(E2E_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Organization name is required")).toBeVisible();
  });

  test("shows validation error for short register password", async ({ page }) => {
    await page.goto("/register");
    await page.getByLabel("Full name").fill("Short Pass");
    await page.getByLabel("Organization").fill("Org");
    await page.getByLabel("Email").fill(uniqueEmail("short"));
    await page.getByLabel("Password").fill("short");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByText("Password must be at least 8 characters")).toBeVisible();
  });

  test("shows error for invalid login credentials", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(uniqueEmail("nouser"));
    await page.getByLabel("Password").fill("wrongpassword");
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page.getByText("Incorrect email or password")).toBeVisible({ timeout: 30_000 });
  });
});
