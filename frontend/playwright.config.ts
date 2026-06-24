import { defineConfig, devices } from "@playwright/test";

const baseURL =
  process.env.E2E_BASE_URL?.replace(/\/$/, "") ??
  process.env.E2E_FRONTEND_URL?.replace(/\/$/, "") ??
  "http://localhost:5173";

const isSmoke = process.env.E2E_SMOKE === "1";
const skipWebServer = isSmoke || process.env.E2E_SKIP_WEBSERVER === "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: isSmoke ? 180_000 : 120_000,
  expect: {
    timeout: 30_000,
  },
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  projects: isSmoke
    ? [
        {
          name: "production-smoke",
          testMatch: /production-smoke\.spec\.ts/,
          use: { ...devices["Desktop Chrome"] },
        },
      ]
    : [
        {
          name: "chromium",
          testIgnore: /production-smoke\.spec\.ts/,
          use: { ...devices["Desktop Chrome"] },
        },
      ],
  webServer: skipWebServer
    ? undefined
    : [
        {
          command:
            "cd ../backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000",
          url: "http://127.0.0.1:8000/health",
          reuseExistingServer: true,
          timeout: 120_000,
        },
        {
          command: "npm run dev -- --host localhost --port 5173",
          url: "http://localhost:5173",
          reuseExistingServer: true,
          timeout: 120_000,
        },
      ],
});
