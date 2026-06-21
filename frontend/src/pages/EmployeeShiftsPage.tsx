import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "../context/AuthContext";
import { addDays, formatDate, formatDayLabel, formatTime, getMonday } from "../lib/dates";
import { schedulingApi } from "../lib/services";

export function EmployeeShiftsPage() {
  const { organization, token } = useAuth();
  const [weekStart, setWeekStart] = useState(() => formatDate(getMonday()));
  const orgId = organization?.id ?? "";

  const shiftsQuery = useQuery({
    queryKey: ["my-shifts", orgId, weekStart],
    queryFn: () => schedulingApi.myShifts(orgId, weekStart, token!),
    enabled: Boolean(orgId && token),
  });

  const moveWeek = (delta: number) => {
    const monday = getMonday(new Date(`${weekStart}T12:00:00`));
    setWeekStart(formatDate(addDays(monday, delta * 7)));
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">My shifts</h1>
          <p className="text-sm text-slate-500">Week of {weekStart}</p>
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
        </div>
      </div>

      {shiftsQuery.isLoading && <p className="text-slate-600">Loading your shifts...</p>}

      {shiftsQuery.data && shiftsQuery.data.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">
          No shifts assigned for this week.
        </div>
      )}

      {shiftsQuery.data && shiftsQuery.data.length > 0 && (
        <div className="grid gap-4">
          {shiftsQuery.data.map((shift) => (
            <div
              key={shift.id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-medium">{formatDayLabel(shift.shift_date)}</h2>
                <span className="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700">
                  {shift.status}
                </span>
              </div>
              <p className="mt-2 text-slate-700">
                {formatTime(shift.start_time)} – {formatTime(shift.end_time)}
              </p>
              <p className="mt-1 text-sm text-slate-500">
                {shift.job_role?.name ?? "Role"} · {shift.location?.name ?? "Location"}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
