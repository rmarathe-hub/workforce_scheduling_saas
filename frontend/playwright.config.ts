import { defineConfig, devices } from "@playwright/test";

const baseURL =
  process.env.E2E_FRONTEND_URL?.replace(/\/$/, "") ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
