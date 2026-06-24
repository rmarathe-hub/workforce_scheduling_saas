import { expect, type Page } from "@playwright/test";

export const E2E_PASSWORD = "password123";
export const isProductionSmoke = process.env.E2E_SMOKE === "1";

/** Unique org name for production smoke runs (e.g. Smoke Test Org 20260623-123456). */
export function smokeOrgName(): string {
  const stamp = new Date()
    .toISOString()
    .slice(0, 19)
    .replace(/[-:T]/g, "")
    .replace(/(\d{8})(\d{6})/, "$1-$2");
  return `Smoke Test Org ${stamp}`;
}

export function uniqueId(): string {
  return `${Date.now()}-${Math.floor(Math.random() * 10_000)}`;
}

export function uniqueEmail(prefix = "e2e"): string {
  return `${prefix}+${uniqueId()}@example.com`;
}

export function formatDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function getMonday(date: Date = new Date()): Date {
  const copy = new Date(date);
  const day = copy.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  copy.setDate(copy.getDate() + diff);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

export function addDays(date: Date, days: number): Date {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

export function tuesdayOfCurrentWeek(): string {
  return formatDate(addDays(getMonday(), 1));
}

export interface OwnerSession {
  email: string;
  password: string;
  orgName: string;
  fullName: string;
}

export interface EmployeeSession {
  email: string;
  password: string;
  fullName: string;
}

export interface SchedulingFixture {
  owner: OwnerSession;
  employee: EmployeeSession;
  locationName: string;
  roleName: string;
}

export async function registerOwner(
  page: Page,
  options?: { orgName?: string; fullName?: string },
): Promise<OwnerSession> {
  const email = uniqueEmail("owner");
  const orgName = options?.orgName ?? `E2E Org ${uniqueId()}`;
  const fullName = options?.fullName ?? "E2E Owner";

  await page.goto("/register");
  await expect(page.getByRole("heading", { name: "Create account" })).toBeVisible();
  await page.getByLabel("Full name").fill(fullName);
  await page.getByLabel("Organization").fill(orgName);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByText("Registration failed")).toBeHidden({ timeout: 90_000 });
  await expect(page).toHaveURL(/\/manager\/schedule/, { timeout: 90_000 });
  await waitForManagerSchedule(page);

  return { email, password: E2E_PASSWORD, orgName, fullName };
}

export async function login(page: Page, email: string, password = E2E_PASSWORD): Promise<void> {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Login failed")).toBeHidden({ timeout: 30_000 });
}

export async function logout(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login/);
}

export async function waitForManagerSchedule(page: Page): Promise<void> {
  await expect(page.getByTestId("dashboard")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Weekly schedule" })).toBeVisible();
  await expect(page.getByTestId("conflicts-loading")).toBeHidden({ timeout: 60_000 });
  await expect(page.getByTestId("schedule-conflicts-panel")).toBeVisible({ timeout: 60_000 });
}

export async function completeQuickSetup(
  page: Page,
  options?: {
    locationName?: string;
    roleName?: string;
    employee?: EmployeeSession;
  },
): Promise<{ locationName: string; roleName: string; employee: EmployeeSession }> {
  const locationName = options?.locationName ?? `Main ${uniqueId()}`;
  const roleName = options?.roleName ?? `Cashier ${uniqueId()}`;
  const employee = options?.employee ?? {
    fullName: `Employee ${uniqueId()}`,
    email: uniqueEmail("employee"),
    password: E2E_PASSWORD,
  };

  const locationForm = page.getByTestId("create-location-form");
  if (await locationForm.isVisible()) {
    await locationForm.locator("input").fill(locationName);
    await page.getByTestId("create-location-button").click();
    await expect(page.getByTestId("create-role-form")).toBeVisible({ timeout: 30_000 });
  }

  const roleForm = page.getByTestId("create-role-form");
  if (await roleForm.isVisible()) {
    await roleForm.locator("input").fill(roleName);
    await page.getByTestId("create-role-button").click();
    await expect(page.getByTestId("add-employee-form")).toBeVisible({ timeout: 30_000 });
  }

  const employeeForm = page.getByTestId("add-employee-form");
  await employeeForm.getByPlaceholder("Full name").fill(employee.fullName);
  await employeeForm.getByPlaceholder("Email").fill(employee.email);
  await employeeForm.getByRole("button", { name: "Add employee" }).click();
  await expect(employeeForm.getByPlaceholder("Email")).toHaveValue("", { timeout: 30_000 });
  await expect(employeeForm.locator(".text-red-600")).toHaveCount(0);

  return { locationName, roleName, employee };
}

export async function createSchedulingFixture(
  page: Page,
  options?: { orgName?: string },
): Promise<SchedulingFixture> {
  const owner = await registerOwner(
    page,
    options?.orgName ? { orgName: options.orgName } : undefined,
  );
  const setup = await completeQuickSetup(page);
  return { owner, ...setup };
}

export async function createCoverageRequirement(
  page: Page,
  options?: { headcount?: number; shiftDate?: string },
): Promise<void> {
  await page.goto("/manager/coverage/new");
  await expect(page.getByRole("heading", { name: "New coverage requirement" })).toBeVisible();

  const form = page.getByTestId("create-coverage-form");
  const locationSelect = form.getByLabel("Location");
  await expect(locationSelect.locator("option")).toHaveCount(2, { timeout: 30_000 });
  await locationSelect.selectOption({ index: 1 });

  const roleSelect = form.getByLabel("Job role");
  await expect(roleSelect.locator("option")).toHaveCount(2, { timeout: 30_000 });
  await roleSelect.selectOption({ index: 1 });

  if (options?.shiftDate) {
    await form.getByLabel("Shift date").fill(options.shiftDate);
  }

  if (options?.headcount !== undefined) {
    await form.getByLabel("Headcount").fill(String(options.headcount));
  }

  await form.getByRole("button", { name: "Create coverage" }).click();
  await expect(page).toHaveURL(/\/manager\/schedule/, { timeout: 30_000 });
  await waitForManagerSchedule(page);
}

export async function generateWeeklySchedule(page: Page): Promise<void> {
  await page.getByTestId("generate-week-button").click();
  await expect(page.getByTestId("generation-summary")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByTestId("conflicts-loading")).toBeHidden({ timeout: 60_000 });
}

export async function validateWeek(page: Page): Promise<void> {
  await page.getByTestId("validate-week-button").click();
  await expect(page.getByTestId("validate-message")).toBeVisible({ timeout: 30_000 });
}

export async function publishSchedule(page: Page, options?: { accept?: boolean }): Promise<void> {
  const accept = options?.accept ?? true;
  page.once("dialog", (dialog) => {
    void (accept ? dialog.accept() : dialog.dismiss());
  });
  await page.getByTestId("publish-week-button").click();
  if (accept) {
    await expect(page.getByTestId("schedule-status-badge")).toHaveText("Published", {
      timeout: 60_000,
    });
  }
}

export async function loginAsEmployee(page: Page, employee: EmployeeSession): Promise<void> {
  await login(page, employee.email, employee.password);
  await expect(page).toHaveURL(/\/employee\/shifts/, { timeout: 30_000 });
  await expect(page.getByTestId("employee-shifts-page")).toBeVisible();
}

export async function loginAsManager(page: Page, email: string, password = E2E_PASSWORD): Promise<void> {
  await login(page, email, password);
  await expect(page).toHaveURL(/\/manager\/schedule/, { timeout: 30_000 });
  await waitForManagerSchedule(page);
}

export async function employeeGiveUpFirstShift(page: Page): Promise<void> {
  await expect(page.getByTestId("employee-shift-card").first()).toBeVisible();
  await page.getByTestId("give-up-shift-button").first().click();
  await expect(page.getByText("Swap pending").first()).toBeVisible({ timeout: 30_000 });
}

export async function managerApproveFirstShiftSwap(page: Page): Promise<void> {
  await page.goto("/manager/shift-swaps");
  await expect(page.getByTestId("manager-shift-swaps-page")).toBeVisible();
  await expect(page.getByTestId("shift-swap-request-card")).toHaveCount(1, { timeout: 30_000 });
  await page.getByTestId("approve-shift-swap-button").first().click();
  await expect(page.getByTestId("shift-swaps-empty")).toBeVisible({ timeout: 60_000 });
}

export async function uploadEmployeeTestDocument(page: Page): Promise<void> {
  await page.goto("/employee/documents");
  await expect(page.getByTestId("employee-documents-page")).toBeVisible();
  await page.getByTestId("employee-document-file-input").setInputFiles("e2e/fixtures/sample-certificate.pdf");
  await expect(page.getByTestId("document-upload-success")).toBeVisible({ timeout: 90_000 });
  await expect(page.getByTestId("employee-document-card")).toHaveCount(1);
}

export async function expectManagerAnalyticsCards(page: Page): Promise<void> {
  await expect(page.getByTestId("manager-analytics-cards")).toBeVisible();
  await expect(page.getByTestId("analytics-card-published_shifts")).toBeVisible();
  await expect(page.getByTestId("analytics-card-coverage_fill_rate")).toBeVisible();
}

export async function setupGenerateReadySchedule(
  page: Page,
  headcount = 1,
  options?: { orgName?: string },
): Promise<SchedulingFixture> {
  const fixture = await createSchedulingFixture(page, options);
  await createCoverageRequirement(page, {
    headcount,
    shiftDate: tuesdayOfCurrentWeek(),
  });
  return fixture;
}

export async function openNotificationsPage(page: Page): Promise<void> {
  await page.goto("/notifications");
  await expect(page.getByTestId("notifications-page")).toBeVisible({ timeout: 60_000 });
}

export async function openEmployeeDocumentsPage(page: Page): Promise<void> {
  await page.goto("/employee/documents");
  await expect(page.getByTestId("employee-documents-page")).toBeVisible({ timeout: 60_000 });
}

export async function openManagerEmployeeDocumentsPage(page: Page): Promise<void> {
  await page.goto("/manager/employee-documents");
  await expect(page.getByTestId("manager-employee-documents-page")).toBeVisible({
    timeout: 60_000,
  });
}

export async function setupPublishedSchedule(page: Page): Promise<SchedulingFixture> {
  const fixture = await setupGenerateReadySchedule(page, 1);
  await generateWeeklySchedule(page);
  await validateWeek(page);
  await publishSchedule(page);
  return fixture;
}
