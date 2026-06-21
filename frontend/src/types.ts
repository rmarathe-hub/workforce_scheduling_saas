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

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
