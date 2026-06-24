export type MembershipRole = "OWNER" | "MANAGER" | "EMPLOYEE";

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  timezone: string;
  created_at: string;
}

export interface OrganizationMembership {
  organization: Organization;
  role: MembershipRole;
}

export interface Location {
  id: string;
  organization_id: string;
  name: string;
  address: string | null;
  created_at: string;
}

export interface JobRole {
  id: string;
  organization_id: string;
  name: string;
  created_at: string;
}

export interface Employee {
  user_id: string;
  email: string;
  full_name: string;
  membership_role: MembershipRole;
  location: Location | null;
  job_title: string | null;
  job_roles: JobRole[];
}

export interface CoverageRequirement {
  id: string;
  organization_id: string;
  location_id: string;
  job_role_id: string;
  shift_date: string;
  week_start: string;
  start_time: string;
  end_time: string;
  headcount: number;
  created_at: string;
  location?: Location | null;
  job_role?: JobRole | null;
}

export type ShiftStatus = "DRAFT" | "PUBLISHED" | "CANCELLED";

export type WeekScheduleStatus = "empty" | "draft" | "published";

export interface Shift {
  id: string;
  organization_id: string;
  coverage_requirement_id: string | null;
  location_id: string;
  job_role_id: string;
  shift_date: string;
  start_time: string;
  end_time: string;
  assignee_id: string | null;
  status: ShiftStatus;
  created_at: string;
  location?: Location | null;
  job_role?: JobRole | null;
  assignee_name?: string | null;
}

export interface WeekSchedule {
  week_start: string;
  week_end: string;
  schedule_status: WeekScheduleStatus;
  coverage_requirements: CoverageRequirement[];
  shifts: Shift[];
}

export type ConflictSeverity = "ERROR" | "WARNING" | "INFO";

export type ConflictType =
  | "OVERLAP"
  | "AVAILABILITY"
  | "ROLE_MISMATCH"
  | "TIME_OFF"
  | "MAX_HOURS"
  | "OPEN_SHIFT";

export interface Conflict {
  type: ConflictType;
  severity: ConflictSeverity;
  message: string;
  shift_id: string | null;
  employee_id: string | null;
  coverage_requirement_id: string | null;
}

export interface ConflictSummary {
  total: number;
  errors: number;
  warnings: number;
  info: number;
}

export interface WeekConflicts {
  week_start: string;
  week_end: string;
  summary: ConflictSummary;
  conflicts: Conflict[];
}

export interface ValidateWeekResult {
  week_start: string;
  week_end: string;
  valid: boolean;
  summary: ConflictSummary;
  conflicts: Conflict[];
}

export interface ValidateShiftResult {
  shift_id: string;
  valid: boolean;
  conflicts: Conflict[];
}

export interface GenerateWeekResult {
  week_start: string;
  week_end: string;
  assigned_count: number;
  open_shift_count: number;
  conflict_count: number;
  conflict_summary: ConflictSummary;
  warnings: string[];
  shifts: Shift[];
}

export interface PublishWeekResult {
  week_start: string;
  week_end: string;
  status: string;
  published_shift_count: number;
  warnings: string[];
}

export interface WeekScheduleStatusResult {
  week_start: string;
  week_end: string;
  schedule_status: WeekScheduleStatus;
  draft_shift_count: number;
  published_shift_count: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface AvailabilityWindow {
  id: string;
  organization_id: string;
  employee_id: string;
  day_of_week: number;
  start_time: string;
  end_time: string;
  created_at: string;
  day_name?: string | null;
}

export type TimeOffStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";

export interface TimeOffRequest {
  id: string;
  organization_id: string;
  employee_id: string;
  start_date: string;
  end_date: string;
  reason: string | null;
  status: TimeOffStatus;
  reviewed_by_id: string | null;
  created_at: string;
  updated_at: string;
  employee_name?: string | null;
  reviewed_by_name?: string | null;
}

export type ShiftSwapRequestType = "GIVE_UP" | "SWAP";
export type ShiftSwapStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";

export interface ShiftSummary {
  id: string;
  shift_date: string;
  start_time: string;
  end_time: string;
  assignee_id: string | null;
  status: string;
  location_name?: string | null;
  job_role_name?: string | null;
}

export interface ShiftSwapRequest {
  id: string;
  organization_id: string;
  requester_id: string;
  target_employee_id: string | null;
  original_shift_id: string;
  requested_shift_id: string | null;
  request_type: ShiftSwapRequestType;
  status: ShiftSwapStatus;
  reason: string | null;
  decided_by_id: string | null;
  created_at: string;
  decided_at: string | null;
  requester_name?: string | null;
  target_employee_name?: string | null;
  decided_by_name?: string | null;
  original_shift?: ShiftSummary | null;
  requested_shift?: ShiftSummary | null;
}

export type AuditAction =
  | "SHIFT_SWAP_REQUESTED"
  | "SHIFT_SWAP_APPROVED"
  | "SHIFT_SWAP_REJECTED"
  | "SCHEDULE_GENERATED"
  | "SCHEDULE_PUBLISHED"
  | "TIME_OFF_APPROVED"
  | "TIME_OFF_REJECTED";

export interface AuditLogEntry {
  id: string;
  organization_id: string;
  actor_user_id: string;
  action: AuditAction;
  entity_type: string;
  entity_id: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  actor_name?: string | null;
}

export interface AuditLogList {
  items: AuditLogEntry[];
  total: number;
  limit: number;
  offset: number;
}

export type DocumentType =
  | "TRAINING_CERTIFICATE"
  | "FOOD_SAFETY_CERTIFICATE"
  | "CPR_CERTIFICATE"
  | "SIGNED_EMPLOYMENT_FORM"
  | "ID_WORK_AUTHORIZATION";

export interface EmployeeDocument {
  id: string;
  organization_id: string;
  employee_id: string;
  uploaded_by_user_id: string;
  document_type: DocumentType;
  file_name: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
  employee_name?: string | null;
  uploaded_by_name?: string | null;
}

export interface PresignDownloadResult {
  download_url: string;
  expires_in: number;
  file_name: string;
  content_type: string;
}

export interface PresignUploadResult {
  document_id: string;
  upload_url: string;
  s3_key: string;
  expires_in: number;
}

export interface DashboardAnalytics {
  week_start: string;
  week_end: string;
  total_employees: number;
  published_shifts: number;
  open_shifts: number;
  pending_time_off: number;
  pending_shift_swaps: number;
  conflict_count: number;
  coverage_fill_rate: number;
  scheduled_hours: number;
}

export type NotificationType =
  | "SCHEDULE_PUBLISHED"
  | "TIME_OFF_APPROVED"
  | "TIME_OFF_REJECTED"
  | "SHIFT_SWAP_REQUESTED"
  | "SHIFT_SWAP_APPROVED"
  | "SHIFT_SWAP_REJECTED"
  | "DOCUMENT_UPLOADED"
  | "OPEN_SHIFT_CREATED";

export type NotificationStatus = "PENDING" | "SENT" | "FAILED" | "READ";

export type NotificationChannel = "IN_APP" | "EMAIL";

export interface Notification {
  id: string;
  organization_id: string;
  recipient_user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  status: NotificationStatus;
  channel: NotificationChannel;
  entity_type: string | null;
  entity_id: string | null;
  created_at: string;
  sent_at: string | null;
  read_at: string | null;
  error_message?: string | null;
  retry_count?: number;
}

export interface NotificationList {
  items: Notification[];
  unread_count: number;
}
