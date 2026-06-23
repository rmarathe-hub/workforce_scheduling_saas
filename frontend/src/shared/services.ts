import { apiRequest } from "./api";
import type {
  AvailabilityWindow,
  CoverageRequirement,
  Employee,
  JobRole,
  Location,
  OrganizationMembership,
  Shift,
  ShiftSwapRequest,
  AuditLogList,
  EmployeeDocument,
  DashboardAnalytics,
  PresignDownloadResult,
  PresignUploadResult,
  DocumentType,
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

export const shiftSwapApi = {
  create: (
    orgId: string,
    token: string,
    body: {
      request_type: string;
      original_shift_id: string;
      requested_shift_id?: string;
      reason?: string;
    },
  ) =>
    apiRequest<ShiftSwapRequest>(`/organizations/${orgId}/shift-swap-requests`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  mine: (orgId: string, token: string) =>
    apiRequest<ShiftSwapRequest[]>(
      `/organizations/${orgId}/shift-swap-requests/me`,
      {},
      token,
    ),

  list: (orgId: string, token: string, status?: string) => {
    const query = status ? `?status=${status}` : "";
    return apiRequest<ShiftSwapRequest[]>(
      `/organizations/${orgId}/shift-swap-requests${query}`,
      {},
      token,
    );
  },

  approve: (orgId: string, requestId: string, token: string) =>
    apiRequest<ShiftSwapRequest>(
      `/organizations/${orgId}/shift-swap-requests/${requestId}/approve`,
      { method: "PATCH" },
      token,
    ),

  reject: (orgId: string, requestId: string, token: string) =>
    apiRequest<ShiftSwapRequest>(
      `/organizations/${orgId}/shift-swap-requests/${requestId}/reject`,
      { method: "PATCH" },
      token,
    ),

  cancel: (orgId: string, requestId: string, token: string) =>
    apiRequest<ShiftSwapRequest>(
      `/organizations/${orgId}/shift-swap-requests/${requestId}/cancel`,
      { method: "PATCH" },
      token,
    ),
};

export const analyticsApi = {
  dashboard: (orgId: string, weekStart: string, token: string) =>
    apiRequest<DashboardAnalytics>(
      `/organizations/${orgId}/analytics/dashboard?week_start=${weekStart}`,
      {},
      token,
    ),
};

export const auditLogApi = {
  list: (orgId: string, token: string, limit = 50, offset = 0) =>
    apiRequest<AuditLogList>(
      `/organizations/${orgId}/audit-logs?limit=${limit}&offset=${offset}`,
      {},
      token,
    ),
};

const ALLOWED_UPLOAD_TYPES = new Set([
  "application/pdf",
  "image/jpeg",
  "image/png",
]);
const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

export async function uploadFileToPresignedUrl(uploadUrl: string, file: File): Promise<void> {
  const response = await fetch(uploadUrl, {
    method: "PUT",
    body: file,
    headers: { "Content-Type": file.type },
  });
  if (!response.ok) {
    throw new Error("Upload to S3 failed");
  }
}

export const documentsApi = {
  presignUpload: (
    orgId: string,
    token: string,
    body: {
      employee_id: string;
      document_type: DocumentType;
      file_name: string;
      content_type: string;
      size_bytes: number;
    },
  ) =>
    apiRequest<PresignUploadResult>(`/organizations/${orgId}/documents/presign-upload`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  completeUpload: (
    orgId: string,
    token: string,
    body: {
      document_id: string;
      employee_id: string;
      document_type: DocumentType;
      file_name: string;
      s3_key: string;
      content_type: string;
      size_bytes: number;
    },
  ) =>
    apiRequest<EmployeeDocument>(`/organizations/${orgId}/documents/complete-upload`, {
      method: "POST",
      body: JSON.stringify(body),
    }, token),

  listForEmployee: (orgId: string, employeeId: string, token: string) =>
    apiRequest<EmployeeDocument[]>(
      `/organizations/${orgId}/employees/${employeeId}/documents`,
      {},
      token,
    ),

  delete: (orgId: string, documentId: string, token: string) =>
    apiRequest<void>(`/organizations/${orgId}/documents/${documentId}`, {
      method: "DELETE",
    }, token),

  getDownloadUrl: (orgId: string, documentId: string, token: string) =>
    apiRequest<PresignDownloadResult>(
      `/organizations/${orgId}/documents/${documentId}/download-url`,
      {},
      token,
    ),

  uploadDocument: async (
    orgId: string,
    token: string,
    employeeId: string,
    documentType: DocumentType,
    file: File,
  ): Promise<EmployeeDocument> => {
    if (!ALLOWED_UPLOAD_TYPES.has(file.type)) {
      throw new Error("Only PDF, JPEG, and PNG files are allowed");
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      throw new Error("File must be 5MB or smaller");
    }
    const presign = await documentsApi.presignUpload(orgId, token, {
      employee_id: employeeId,
      document_type: documentType,
      file_name: file.name,
      content_type: file.type,
      size_bytes: file.size,
    });
    await uploadFileToPresignedUrl(presign.upload_url, file);
    return documentsApi.completeUpload(orgId, token, {
      document_id: presign.document_id,
      employee_id: employeeId,
      document_type: documentType,
      file_name: file.name,
      s3_key: presign.s3_key,
      content_type: file.type,
      size_bytes: file.size,
    });
  },
};
