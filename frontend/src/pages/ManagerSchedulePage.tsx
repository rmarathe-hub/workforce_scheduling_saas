import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { ManagerSetupPanel } from "../components/ManagerSetupPanel";
import { addDays, formatDate, formatDayLabel, formatTime, getMonday } from "../shared/dates";
import { resourceApi, schedulingApi } from "../shared/services";
import type { CoverageRequirement, Shift } from "../types";

export function ManagerSchedulePage() {
  const { organization, token } = useAuth();
  const queryClient = useQueryClient();
  const [weekStart, setWeekStart] = useState(() => formatDate(getMonday()));

  const orgId = organization?.id ?? "";

  const scheduleQuery = useQuery({
    queryKey: ["schedule", orgId, weekStart],
    queryFn: () => schedulingApi.weekSchedule(orgId, weekStart, token!),
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

  const assignMutation = useMutation({
    mutationFn: ({ shiftId, assigneeId }: { shiftId: string; assigneeId: string }) =>
      schedulingApi.assignShift(orgId, shiftId, token!, assigneeId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["schedule", orgId, weekStart] });
    },
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
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["schedule", orgId, weekStart] });
    },
  });

  const moveWeek = (delta: number) => {
    const monday = getMonday(new Date(`${weekStart}T12:00:00`));
    setWeekStart(formatDate(addDays(monday, delta * 7)));
  };

  const schedule = scheduleQuery.data;
  const employees =
    employeesQuery.data?.filter((employee) => employee.membership_role === "EMPLOYEE") ?? [];

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Weekly schedule</h1>
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
            onClick={() => setWeekStart(formatDate(getMonday()))}
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

      <ManagerSetupPanel
        orgId={orgId}
        hasLocations={(locationsQuery.data?.length ?? 0) > 0}
        hasJobRoles={(jobRolesQuery.data?.length ?? 0) > 0}
      />

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
            <h2 className="text-lg font-medium">Shifts</h2>
            {schedule.shifts.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">No shifts yet. Add coverage, then create shifts.</p>
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
                      <th className="py-2">Assign</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.shifts.map((shift) => (
                      <ShiftRow
                        key={shift.id}
                        shift={shift}
                        employees={employees}
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
  onAssign,
  isAssigning,
}: {
  shift: Shift;
  employees: { user_id: string; full_name: string; job_roles: { id: string; name: string }[] }[];
  onAssign: (assigneeId: string) => void;
  isAssigning: boolean;
}) {
  const eligible = employees.filter((employee) =>
    employee.job_roles.some((role) => role.id === shift.job_role_id),
  );

  return (
    <tr className="border-b border-slate-100">
      <td className="py-3 pr-4">{formatDayLabel(shift.shift_date)}</td>
      <td className="py-3 pr-4">
        {formatTime(shift.start_time)} – {formatTime(shift.end_time)}
      </td>
      <td className="py-3 pr-4">{shift.job_role?.name ?? "—"}</td>
      <td className="py-3 pr-4">{shift.location?.name ?? "—"}</td>
      <td className="py-3 pr-4">{shift.assignee_name ?? "Unassigned"}</td>
      <td className="py-3">
        {!shift.assignee_id && eligible.length > 0 ? (
          <select
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
