import { apiRequest } from "./api";
import type {
  AvailabilityWindow,
  CoverageRequirement,
  Employee,
  JobRole,
  Location,
  OrganizationMembership,
  Shift,
  TimeOffRequest,
  TokenResponse,
  User,
  ValidateShiftResult,
  ValidateWeekResult,
  GenerateWeekResult,
  PublishWeekResult,
  WeekConflicts,
  WeekSchedule,
  WeekScheduleStatusResult,
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

  weekConflicts: (orgId: string, weekStart: string, token: string) =>
    apiRequest<WeekConflicts>(`/organizations/${orgId}/schedules/${weekStart}/conflicts`, {}, token),

  validateWeek: (orgId: string, weekStart: string, token: string) =>
    apiRequest<ValidateWeekResult>(`/organizations/${orgId}/schedules/${weekStart}/validate`, {
      method: "POST",
    }, token),

  validateShift: (orgId: string, shiftId: string, token: string) =>
    apiRequest<ValidateShiftResult>(`/organizations/${orgId}/shifts/${shiftId}/validate`, {
      method: "POST",
    }, token),

  generateWeek: (orgId: string, weekStart: string, token: string) =>
    apiRequest<GenerateWeekResult>(`/organizations/${orgId}/schedules/${weekStart}/generate`, {
      method: "POST",
    }, token),

  publishWeek: (orgId: string, weekStart: string, token: string) =>
    apiRequest<PublishWeekResult>(`/organizations/${orgId}/schedules/${weekStart}/publish`, {
      method: "POST",
    }, token),

  weekStatus: (orgId: string, weekStart: string, token: string) =>
    apiRequest<WeekScheduleStatusResult>(
      `/organizations/${orgId}/schedules/${weekStart}/status`,
      {},
      token,
    ),
};

export const availabilityApi = {
  create: (
    orgId: string,
    token: string,
    body: { day_of_week: number; start_time: string; end_time: string },
  ) =>
    apiRequest<AvailabilityWindow>(`/organizations/${orgId}/availability`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  mine: (orgId: string, token: string) =>
    apiRequest<AvailabilityWindow[]>(`/organizations/${orgId}/availability/me`, {}, token),

  forEmployee: (orgId: string, employeeId: string, token: string) =>
    apiRequest<AvailabilityWindow[]>(
      `/organizations/${orgId}/employees/${employeeId}/availability`,
      {},
      token,
    ),

  update: (
    orgId: string,
    windowId: string,
    token: string,
    body: { day_of_week?: number; start_time?: string; end_time?: string },
  ) =>
    apiRequest<AvailabilityWindow>(`/organizations/${orgId}/availability/${windowId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }, token),

  remove: (orgId: string, windowId: string, token: string) =>
    apiRequest<void>(`/organizations/${orgId}/availability/${windowId}`, {
      method: "DELETE",
    }, token),
};

export const timeOffApi = {
  create: (
    orgId: string,
    token: string,
    body: { start_date: string; end_date: string; reason?: string },
  ) =>
    apiRequest<TimeOffRequest>(`/organizations/${orgId}/time-off-requests`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  mine: (orgId: string, token: string) =>
    apiRequest<TimeOffRequest[]>(
      `/organizations/${orgId}/time-off-requests/me`,
      {},
      token,
    ),

  list: (orgId: string, token: string, status?: string) => {
    const query = status ? `?status=${status}` : "";
    return apiRequest<TimeOffRequest[]>(
      `/organizations/${orgId}/time-off-requests${query}`,
      {},
      token,
    );
  },

  approve: (orgId: string, requestId: string, token: string) =>
    apiRequest<TimeOffRequest>(
      `/organizations/${orgId}/time-off-requests/${requestId}/approve`,
      { method: "PATCH" },
      token,
    ),

  reject: (orgId: string, requestId: string, token: string) =>
    apiRequest<TimeOffRequest>(
      `/organizations/${orgId}/time-off-requests/${requestId}/reject`,
      { method: "PATCH" },
      token,
    ),

  cancel: (orgId: string, requestId: string, token: string) =>
    apiRequest<TimeOffRequest>(
      `/organizations/${orgId}/time-off-requests/${requestId}/cancel`,
      { method: "PATCH" },
      token,
    ),
};
