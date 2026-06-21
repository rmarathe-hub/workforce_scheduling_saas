import { expect, test, type Page } from "@playwright/test";

const PASSWORD = "password123";

async function fillRegisterForm(
  page: Page,
  values: { fullName: string; organization: string; email: string; password: string },
) {
  const form = page.locator("form").first();
  await form.locator('input:not([type="email"]):not([type="password"])').nth(0).fill(values.fullName);
  await form.locator('input:not([type="email"]):not([type="password"])').nth(1).fill(values.organization);
  await form.locator('input[type="email"]').fill(values.email);
  await form.locator('input[type="password"]').fill(values.password);
}

test.describe("deployed frontend smoke", () => {
  test("login page renders", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  });

  test("register owner and complete quick setup", async ({ page }) => {
    const suffix = Date.now();
    const email = `e2e+${suffix}@example.com`;
    const orgName = `E2E Org ${suffix}`;

    await page.goto("/register");
    await expect(page.getByRole("heading", { name: "Create account" })).toBeVisible();

    await fillRegisterForm(page, {
      fullName: "E2E User",
      organization: orgName,
      email,
      password: PASSWORD,
    });
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page).toHaveURL(/\/manager\/schedule/, { timeout: 90_000 });
    await expect(page.getByRole("heading", { name: "Weekly schedule" })).toBeVisible();

    await page.getByRole("button", { name: "Add location" }).click();
    await expect(page.getByRole("button", { name: "Add job role" })).toBeVisible({
      timeout: 30_000,
    });

    await page.getByRole("button", { name: "Add job role" }).click();
    await expect(page.getByRole("heading", { name: "Add employee" })).toBeVisible({
      timeout: 30_000,
    });
  });
});
