import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { ManagerAnalyticsCards } from "../components/ManagerAnalyticsCards";
import { ManagerSetupPanel } from "../components/ManagerSetupPanel";
import { addDays, formatDate, formatDayLabel, formatTime, getMonday } from "../shared/dates";
import { analyticsApi, resourceApi, schedulingApi } from "../shared/services";
import type {
  Conflict,
  ConflictSeverity,
  CoverageRequirement,
  GenerateWeekResult,
  Shift,
  WeekScheduleStatus,
} from "../types";

function severityRank(severity: ConflictSeverity): number {
  if (severity === "ERROR") return 3;
  if (severity === "WARNING") return 2;
  return 1;
}

function buildShiftSeverityMap(conflicts: Conflict[], shifts: Shift[]): Map<string, ConflictSeverity> {
  const map = new Map<string, ConflictSeverity>();

  const upsert = (shiftId: string, severity: ConflictSeverity) => {
    const current = map.get(shiftId);
    if (!current || severityRank(severity) > severityRank(current)) {
      map.set(shiftId, severity);
    }
  };

  for (const conflict of conflicts) {
    if (conflict.shift_id) {
      upsert(conflict.shift_id, conflict.severity);
      continue;
    }
    if (conflict.employee_id) {
      for (const shift of shifts) {
        if (shift.assignee_id === conflict.employee_id) {
          upsert(shift.id, conflict.severity);
        }
      }
    }
  }

  return map;
}

function shiftRowClassName(severity: ConflictSeverity | undefined): string {
  if (severity === "ERROR") return "border-l-4 border-l-red-500 bg-red-50";
  if (severity === "WARNING") return "border-l-4 border-l-amber-500 bg-amber-50";
  return "border-b border-slate-100";
}

function conflictTypeLabel(type: Conflict["type"]): string {
  return type.replaceAll("_", " ").toLowerCase();
}

function severityBadgeClass(severity: ConflictSeverity): string {
  if (severity === "ERROR") return "bg-red-100 text-red-800";
  if (severity === "WARNING") return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

function scheduleStatusLabel(status: WeekScheduleStatus): string {
  if (status === "published") return "Published";
  if (status === "draft") return "Draft";
  return "Empty";
}

function scheduleStatusBadgeClass(status: WeekScheduleStatus): string {
  if (status === "published") return "bg-green-100 text-green-800";
  if (status === "draft") return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-600";
}

export function ManagerSchedulePage() {
  const { organization, token } = useAuth();
  const queryClient = useQueryClient();
  const [weekStart, setWeekStart] = useState(() => formatDate(getMonday()));
  const [validateMessage, setValidateMessage] = useState<string | null>(null);
  const [generateSummary, setGenerateSummary] = useState<GenerateWeekResult | null>(null);
  const [publishMessage, setPublishMessage] = useState<string | null>(null);

  const orgId = organization?.id ?? "";

  const scheduleQuery = useQuery({
    queryKey: ["schedule", orgId, weekStart],
    queryFn: () => schedulingApi.weekSchedule(orgId, weekStart, token!),
    enabled: Boolean(orgId && token),
  });

  const conflictsQuery = useQuery({
    queryKey: ["conflicts", orgId, weekStart],
    queryFn: () => schedulingApi.weekConflicts(orgId, weekStart, token!),
    enabled: Boolean(orgId && token),
  });

  const analyticsQuery = useQuery({
    queryKey: ["analytics", orgId, weekStart],
    queryFn: () => analyticsApi.dashboard(orgId, weekStart, token!),
    enabled: Boolean(orgId && token),
  });

  const employeesQuery = useQuery({
    queryKey: ["employees", orgId],
    queryFn: () => resourceApi.employees(orgId, token!),
    enabled: Boolean(orgId && token),
  });

  const locationsQuery = useQuery({
    queryKey: ["locations", orgId],
    queryFn: () => resourceApi.locations(orgId, token!),
    enabled: Boolean(orgId && token),
  });

  const jobRolesQuery = useQuery({
    queryKey: ["job-roles", orgId],
    queryFn: () => resourceApi.jobRoles(orgId, token!),
    enabled: Boolean(orgId && token),
  });

  const invalidateSchedule = () => {
    void queryClient.invalidateQueries({ queryKey: ["schedule", orgId, weekStart] });
    void queryClient.invalidateQueries({ queryKey: ["conflicts", orgId, weekStart] });
    void queryClient.invalidateQueries({ queryKey: ["analytics", orgId, weekStart] });
    setValidateMessage(null);
    setPublishMessage(null);
  };

  const clearWeekMessages = () => {
    setValidateMessage(null);
    setGenerateSummary(null);
    setPublishMessage(null);
  };

  const assignMutation = useMutation({
    mutationFn: ({ shiftId, assigneeId }: { shiftId: string; assigneeId: string }) =>
      schedulingApi.assignShift(orgId, shiftId, token!, assigneeId),
    onSuccess: invalidateSchedule,
  });

  const createShiftMutation = useMutation({
    mutationFn: (requirement: CoverageRequirement) =>
      schedulingApi.createShift(orgId, token!, {
        location_id: requirement.location_id,
        job_role_id: requirement.job_role_id,
        shift_date: requirement.shift_date,
        start_time: requirement.start_time,
        end_time: requirement.end_time,
        coverage_requirement_id: requirement.id,
      }),
    onSuccess: invalidateSchedule,
  });

  const validateWeekMutation = useMutation({
    mutationFn: () => schedulingApi.validateWeek(orgId, weekStart, token!),
    onSuccess: (result) => {
      setValidateMessage(
        result.valid
          ? "Schedule is valid — no blocking errors."
          : `${result.summary.errors} error${result.summary.errors === 1 ? "" : "s"} must be resolved before publishing.`,
      );
    },
  });

  const generateWeekMutation = useMutation({
    mutationFn: () => schedulingApi.generateWeek(orgId, weekStart, token!),
    onSuccess: async (result) => {
      setGenerateSummary(result);
      invalidateSchedule();
      await queryClient.refetchQueries({ queryKey: ["conflicts", orgId, weekStart] });
    },
  });

  const publishWeekMutation = useMutation({
    mutationFn: () => schedulingApi.publishWeek(orgId, weekStart, token!),
    onSuccess: (result) => {
      setPublishMessage(
        `Published ${result.published_shift_count} shift${result.published_shift_count === 1 ? "" : "s"}.`,
      );
      setGenerateSummary(null);
      invalidateSchedule();
    },
  });

  const moveWeek = (delta: number) => {
    const monday = getMonday(new Date(`${weekStart}T12:00:00`));
    setWeekStart(formatDate(addDays(monday, delta * 7)));
    clearWeekMessages();
  };

  const schedule = scheduleQuery.data;
  const conflicts = conflictsQuery.data;
  const employees =
    employeesQuery.data?.filter((employee) => employee.membership_role === "EMPLOYEE") ?? [];

  const shiftSeverityMap = useMemo(
    () => buildShiftSeverityMap(conflicts?.conflicts ?? [], schedule?.shifts ?? []),
    [conflicts?.conflicts, schedule?.shifts],
  );

  const hasBlockingErrors = (conflicts?.summary.errors ?? 0) > 0;
  const scheduleStatus = schedule?.schedule_status ?? "empty";
  const assignedShifts = schedule?.shifts.filter((shift) => shift.assignee_id) ?? [];
  const openShifts = schedule?.shifts.filter((shift) => !shift.assignee_id) ?? [];
  const canPublish =
    scheduleStatus === "draft" && !hasBlockingErrors && (schedule?.shifts.length ?? 0) > 0;

  const handlePublish = () => {
    if (!canPublish) return;
    const confirmed = window.confirm(
      "Publish this week's schedule? Employees will see their assigned shifts.",
    );
    if (confirmed) {
      publishWeekMutation.mutate();
    }
  };

  return (
    <div className="space-y-8" data-testid="dashboard">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold">Weekly schedule</h1>
            {schedule && (
              <span
                className={`rounded-full px-3 py-1 text-xs font-medium uppercase ${scheduleStatusBadgeClass(scheduleStatus)}`}
                data-testid="schedule-status-badge"
              >
                {scheduleStatusLabel(scheduleStatus)}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500">
            Week of {weekStart}
            {schedule ? ` – ${schedule.week_end}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => moveWeek(-1)}
            className="rounded-md border border-slate-300 px-3 py-1.5 hover:bg-white"
          >
            Previous
          </button>
          <button
            type="button"
            onClick={() => {
              setWeekStart(formatDate(getMonday()));
              clearWeekMessages();
            }}
            className="rounded-md border border-slate-300 px-3 py-1.5 hover:bg-white"
          >
            This week
          </button>
          <button
            type="button"
            onClick={() => moveWeek(1)}
            className="rounded-md border border-slate-300 px-3 py-1.5 hover:bg-white"
          >
            Next
          </button>
          <Link
            to="/manager/coverage/new"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            New coverage
          </Link>
        </div>
      </div>

      <ManagerAnalyticsCards
        analytics={analyticsQuery.data}
        isLoading={analyticsQuery.isLoading}
      />

      <ManagerSetupPanel
        orgId={orgId}
        hasLocations={(locationsQuery.data?.length ?? 0) > 0}
        hasJobRoles={(jobRolesQuery.data?.length ?? 0) > 0}
      />

      <section
        className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        data-testid="schedule-actions-panel"
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-medium">Schedule actions</h2>
            <p className="mt-1 text-sm text-slate-500">
              Generate draft shifts from coverage, then publish when conflicts are clear.
            </p>
            {publishMessage && (
              <p className="mt-2 text-sm font-medium text-green-700" data-testid="publish-message">
                {publishMessage}
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              data-testid="generate-week-button"
              onClick={() => generateWeekMutation.mutate()}
              disabled={generateWeekMutation.isPending || publishWeekMutation.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {generateWeekMutation.isPending ? "Generating..." : "Generate weekly schedule"}
            </button>
            <button
              type="button"
              data-testid="publish-week-button"
              onClick={handlePublish}
              disabled={!canPublish || publishWeekMutation.isPending || generateWeekMutation.isPending}
              className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {publishWeekMutation.isPending ? "Publishing..." : "Publish schedule"}
            </button>
          </div>
        </div>

        {generateSummary && (
          <div
            className="mt-4 rounded-md border border-blue-100 bg-blue-50 px-4 py-3 text-sm"
            data-testid="generation-summary"
          >
            <p className="font-medium text-blue-900">Generation summary</p>
            <p className="mt-1 text-blue-800">
              Generated {generateSummary.shifts.length} shift
              {generateSummary.shifts.length === 1 ? "" : "s"} · Assigned{" "}
              {generateSummary.assigned_count} · {generateSummary.open_shift_count} open shift
              {generateSummary.open_shift_count === 1 ? "" : "s"} need coverage
            </p>
            {generateSummary.conflict_count > 0 && (
              <p className="mt-1 text-blue-800" data-testid="generation-conflict-summary">
                {generateSummary.conflict_summary.errors} error
                {generateSummary.conflict_summary.errors === 1 ? "" : "s"},{" "}
                {generateSummary.conflict_summary.warnings} warning
                {generateSummary.conflict_summary.warnings === 1 ? "" : "s"}
                {generateSummary.conflict_summary.info > 0
                  ? `, ${generateSummary.conflict_summary.info} info`
                  : ""}{" "}
                — see conflict panel below
              </p>
            )}
            {generateSummary.warnings.length > 0 && (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-blue-800">
                {generateSummary.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {hasBlockingErrors && (
          <p className="mt-3 text-sm text-red-600" data-testid="publish-blocked-message">
            Resolve error conflicts before publishing.
          </p>
        )}
      </section>

      {conflictsQuery.isLoading && (
        <p className="text-sm text-slate-500" data-testid="conflicts-loading">
          Checking schedule conflicts...
        </p>
      )}

      {conflicts && (
        <section
          className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
          data-testid="schedule-conflicts-panel"
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-medium">Schedule conflicts</h2>
              {conflicts.summary.total === 0 ? (
                <p className="mt-1 text-sm text-green-700" data-testid="conflicts-summary">
                  No conflicts this week.
                </p>
              ) : (
                <p className="mt-1 text-sm text-slate-600" data-testid="conflicts-summary">
                  {conflicts.summary.total} conflict{conflicts.summary.total === 1 ? "" : "s"}:{" "}
                  {conflicts.summary.errors} error{conflicts.summary.errors === 1 ? "" : "s"},{" "}
                  {conflicts.summary.warnings} warning{conflicts.summary.warnings === 1 ? "" : "s"}
                  {conflicts.summary.info > 0
                    ? `, ${conflicts.summary.info} info`
                    : ""}
                </p>
              )}
              {validateMessage && (
                <p className="mt-2 text-sm font-medium text-slate-700" data-testid="validate-message">
                  {validateMessage}
                </p>
              )}
            </div>
            <button
              type="button"
              data-testid="validate-week-button"
              onClick={() => validateWeekMutation.mutate()}
              disabled={validateWeekMutation.isPending}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
            >
              {validateWeekMutation.isPending ? "Validating..." : "Validate week"}
            </button>
          </div>

          {conflicts.conflicts.length > 0 && (
            <ul className="mt-4 max-h-48 space-y-2 overflow-y-auto">
              {conflicts.conflicts.map((conflict, index) => (
                <li
                  key={`${conflict.type}-${conflict.shift_id ?? conflict.employee_id ?? index}`}
                  className="flex flex-wrap items-center gap-2 rounded-md border border-slate-100 px-3 py-2 text-sm"
                  data-testid="conflict-item"
                >
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-medium uppercase ${severityBadgeClass(conflict.severity)}`}
                  >
                    {conflict.severity}
                  </span>
                  <span className="text-slate-500">{conflictTypeLabel(conflict.type)}</span>
                  <span className="text-slate-700">{conflict.message}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {scheduleQuery.isLoading && <p className="text-slate-600">Loading schedule...</p>}
      {scheduleQuery.error && (
        <p className="text-red-600">Failed to load schedule. Add locations and roles first.</p>
      )}

      {schedule && (
        <>
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-medium">Coverage needs</h2>
            {schedule.coverage_requirements.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No coverage requirements this week.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b text-slate-500">
                    <tr>
                      <th className="py-2 pr-4">Day</th>
                      <th className="py-2 pr-4">Time</th>
                      <th className="py-2 pr-4">Role</th>
                      <th className="py-2 pr-4">Location</th>
                      <th className="py-2 pr-4">Needed</th>
                      <th className="py-2">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.coverage_requirements.map((requirement) => (
                      <tr key={requirement.id} className="border-b border-slate-100">
                        <td className="py-3 pr-4">{formatDayLabel(requirement.shift_date)}</td>
                        <td className="py-3 pr-4">
                          {formatTime(requirement.start_time)} – {formatTime(requirement.end_time)}
                        </td>
                        <td className="py-3 pr-4">{requirement.job_role?.name ?? "—"}</td>
                        <td className="py-3 pr-4">{requirement.location?.name ?? "—"}</td>
                        <td className="py-3 pr-4">{requirement.headcount}</td>
                        <td className="py-3">
                          <button
                            type="button"
                            onClick={() => createShiftMutation.mutate(requirement)}
                            className="text-blue-600 hover:underline"
                          >
                            Add shift
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-medium">Shifts</h2>
              {schedule.shifts.length > 0 && (
                <p className="text-sm text-slate-500" data-testid="shift-counts-summary">
                  {assignedShifts.length} assigned · {openShifts.length} open
                </p>
              )}
            </div>
            {schedule.shifts.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">
                No shifts yet. Add coverage, then generate or create shifts manually.
              </p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="border-b text-slate-500">
                    <tr>
                      <th className="py-2 pr-4">Day</th>
                      <th className="py-2 pr-4">Time</th>
                      <th className="py-2 pr-4">Role</th>
                      <th className="py-2 pr-4">Location</th>
                      <th className="py-2 pr-4">Assignee</th>
                      <th className="py-2 pr-4">Status</th>
                      <th className="py-2">Assign</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.shifts.map((shift) => (
                      <ShiftRow
                        key={shift.id}
                        shift={shift}
                        employees={employees}
                        conflictSeverity={shiftSeverityMap.get(shift.id)}
                        onAssign={(assigneeId) =>
                          assignMutation.mutate({ shiftId: shift.id, assigneeId })
                        }
                        isAssigning={assignMutation.isPending}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function ShiftRow({
  shift,
  employees,
  conflictSeverity,
  onAssign,
  isAssigning,
}: {
  shift: Shift;
  employees: { user_id: string; full_name: string; job_roles: { id: string; name: string }[] }[];
  conflictSeverity?: ConflictSeverity;
  onAssign: (assigneeId: string) => void;
  isAssigning: boolean;
}) {
  const eligible = employees.filter((employee) =>
    employee.job_roles.some((role) => role.id === shift.job_role_id),
  );

  return (
    <tr
      className={shiftRowClassName(conflictSeverity)}
      data-testid={conflictSeverity ? "shift-with-conflict" : "shift-row"}
      data-conflict-severity={conflictSeverity ?? ""}
    >
      <td className="py-3 pr-4">{formatDayLabel(shift.shift_date)}</td>
      <td className="py-3 pr-4">
        {formatTime(shift.start_time)} – {formatTime(shift.end_time)}
      </td>
      <td className="py-3 pr-4">{shift.job_role?.name ?? "—"}</td>
      <td className="py-3 pr-4">{shift.location?.name ?? "—"}</td>
      <td className="py-3 pr-4">
        {shift.assignee_name ?? "Unassigned"}
        {conflictSeverity && (
          <span className="ml-2 text-xs text-slate-500">({conflictSeverity.toLowerCase()})</span>
        )}
      </td>
      <td className="py-3 pr-4">
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            shift.status === "PUBLISHED"
              ? "bg-green-100 text-green-800"
              : "bg-slate-100 text-slate-700"
          }`}
        >
          {shift.status}
        </span>
      </td>
      <td className="py-3">
        {shift.status === "PUBLISHED" ? (
          <span className="text-slate-400">—</span>
        ) : !shift.assignee_id && eligible.length > 0 ? (
          <select
            data-testid="assign-shift-button"
            className="rounded-md border border-slate-300 px-2 py-1"
            defaultValue=""
            disabled={isAssigning}
            onChange={(event) => {
              if (event.target.value) {
                onAssign(event.target.value);
              }
            }}
          >
            <option value="" disabled>
              Assign employee
            </option>
            {eligible.map((employee) => (
              <option key={employee.user_id} value={employee.user_id}>
                {employee.full_name}
              </option>
            ))}
          </select>
        ) : (
          <span className="text-slate-400">—</span>
        )}
      </td>
    </tr>
  );
}
