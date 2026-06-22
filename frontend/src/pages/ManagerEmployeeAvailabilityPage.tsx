import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "../context/AuthContext";
import { availabilityApi, resourceApi } from "../shared/services";
import type { AvailabilityWindow } from "../types";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function formatTime(time: string): string {
  return time.slice(0, 5);
}

export function ManagerEmployeeAvailabilityPage() {
  const { organization, token } = useAuth();
  const orgId = organization?.id ?? "";
  const [employeeId, setEmployeeId] = useState("");

  const employeesQuery = useQuery({
    queryKey: ["employees", orgId],
    queryFn: () => resourceApi.employees(orgId, token!),
    enabled: Boolean(orgId && token),
  });

  const employees =
    employeesQuery.data?.filter((employee) => employee.membership_role === "EMPLOYEE") ?? [];

  const availabilityQuery = useQuery({
    queryKey: ["availability", "employee", orgId, employeeId],
    queryFn: () => availabilityApi.forEmployee(orgId, employeeId, token!),
    enabled: Boolean(orgId && token && employeeId),
  });

  return (
    <div className="space-y-6" data-testid="manager-employee-availability-page">
      <div>
        <h1 className="text-2xl font-semibold">Employee availability</h1>
        <p className="text-sm text-slate-500">View recurring availability for your team.</p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <label className="mb-1 block text-sm font-medium">Employee</label>
        <select
          className="w-full max-w-md rounded-md border border-slate-300 px-3 py-2"
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value)}
        >
          <option value="">Select employee</option>
          {employees.map((employee) => (
            <option key={employee.user_id} value={employee.user_id}>
              {employee.full_name}
            </option>
          ))}
        </select>
      </section>

      {employeeId && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-medium">Availability windows</h2>
          {availabilityQuery.isLoading && <p className="mt-3 text-slate-600">Loading...</p>}
          {availabilityQuery.data?.length === 0 && (
            <p className="mt-3 text-sm text-slate-500">No availability set for this employee.</p>
          )}
          {availabilityQuery.data && availabilityQuery.data.length > 0 && (
            <ul className="mt-4 space-y-2">
              {availabilityQuery.data.map((window: AvailabilityWindow) => (
                <li
                  key={window.id}
                  className="rounded-md border border-slate-100 px-4 py-3 text-sm"
                >
                  {window.day_name ?? DAYS[window.day_of_week]} · {formatTime(window.start_time)} –{" "}
                  {formatTime(window.end_time)}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
