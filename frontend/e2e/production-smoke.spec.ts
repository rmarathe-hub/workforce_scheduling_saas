import { expect, test } from "@playwright/test";

import {
  isProductionSmoke,
  registerOwner,
  setupGenerateReadySchedule,
  validateWeek,
} from "./helpers";

test.describe("production smoke", () => {
  test.skip(!isProductionSmoke, "Set E2E_SMOKE=1 to run production smoke tests");

  test("frontend loads login page", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("register and reach manager schedule", async ({ page }) => {
    await registerOwner(page);
    await expect(page.getByTestId("dashboard")).toBeVisible();
  });

  test("generate and validate schedule on deployed stack", async ({ page }) => {
    await setupGenerateReadySchedule(page);
    await page.getByTestId("generate-week-button").click();
    await expect(page.getByTestId("generation-summary")).toBeVisible({ timeout: 120_000 });
    await validateWeek(page);
    await expect(page.getByTestId("validate-message")).toBeVisible();
  });
});
