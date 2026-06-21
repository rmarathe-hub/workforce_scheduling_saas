import { apiRequest } from "./api";
import type {
  CoverageRequirement,
  Employee,
  JobRole,
  Location,
  OrganizationMembership,
  Shift,
  TokenResponse,
  User,
  WeekSchedule,
} from "../types";

export const authApi = {
  register: (body: {
    email: string;
    password: string;
    full_name: string;
    organization_name: string;
    timezone?: string;
  }) => apiRequest<User>("/auth/register", { method: "POST", body: JSON.stringify(body) }),

  login: (body: { email: string; password: string }) =>
    apiRequest<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify(body) }),

  me: (token: string) => apiRequest<User>("/auth/me", {}, token),
};

export const orgApi = {
  myOrganizations: (token: string) =>
    apiRequest<OrganizationMembership[]>("/organizations/me", {}, token),
};

export const resourceApi = {
  locations: (orgId: string, token: string) =>
    apiRequest<Location[]>(`/organizations/${orgId}/locations`, {}, token),

  createLocation: (orgId: string, token: string, body: { name: string; address?: string }) =>
    apiRequest<Location>(`/organizations/${orgId}/locations`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  jobRoles: (orgId: string, token: string) =>
    apiRequest<JobRole[]>(`/organizations/${orgId}/job-roles`, {}, token),

  createJobRole: (orgId: string, token: string, body: { name: string }) =>
    apiRequest<JobRole>(`/organizations/${orgId}/job-roles`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  employees: (orgId: string, token: string) =>
    apiRequest<Employee[]>(`/organizations/${orgId}/employees`, {}, token),

  addMember: (
    orgId: string,
    token: string,
    body: {
      email: string;
      full_name: string;
      password: string;
      membership_role: string;
      location_id?: string;
      job_role_ids?: string[];
    },
  ) =>
    apiRequest<Employee>(`/organizations/${orgId}/members`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),
};

export const schedulingApi = {
  weekSchedule: (orgId: string, weekStart: string, token: string) =>
    apiRequest<WeekSchedule>(`/organizations/${orgId}/schedules/${weekStart}`, {}, token),

  createCoverageRequirement: (
    orgId: string,
    token: string,
    body: {
      location_id: string;
      job_role_id: string;
      shift_date: string;
      week_start: string;
      start_time: string;
      end_time: string;
      headcount: number;
    },
  ) =>
    apiRequest<CoverageRequirement>(`/organizations/${orgId}/coverage-requirements`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  createShift: (
    orgId: string,
    token: string,
    body: {
      location_id: string;
      job_role_id: string;
      shift_date: string;
      start_time: string;
      end_time: string;
      coverage_requirement_id?: string;
    },
  ) =>
    apiRequest<Shift>(`/organizations/${orgId}/shifts`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  assignShift: (orgId: string, shiftId: string, token: string, assigneeId: string) =>
    apiRequest<Shift>(`/organizations/${orgId}/shifts/${shiftId}/assign`, {
      method: "PATCH",
      body: JSON.stringify({ assignee_id: assigneeId }),
    }, token),

  myShifts: (orgId: string, weekStart: string, token: string) =>
    apiRequest<Shift[]>(
      `/organizations/${orgId}/my-shifts?week_start=${weekStart}`,
      {},
      token,
    ),
};
