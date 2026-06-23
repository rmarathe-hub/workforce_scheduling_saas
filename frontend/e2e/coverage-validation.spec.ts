import { expect, test } from "@playwright/test";

import { registerOwner } from "./helpers";

test.describe("coverage form validation", () => {
  test("shows validation error when location not selected", async ({ page }) => {
    await registerOwner(page);
    await page.goto("/manager/coverage/new");

    const form = page.getByTestId("create-coverage-form");
    await form.getByRole("button", { name: "Create coverage" }).click();
    await expect(form.getByText("Select a location")).toBeVisible();
  });
});
