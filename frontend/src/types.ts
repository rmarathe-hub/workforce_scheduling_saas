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
  status: string;
  created_at: string;
  location?: Location | null;
  job_role?: JobRole | null;
  assignee_name?: string | null;
}

export interface WeekSchedule {
  week_start: string;
  week_end: string;
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
