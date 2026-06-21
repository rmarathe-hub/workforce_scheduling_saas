import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";
import { resourceApi } from "../lib/services";

interface ManagerSetupPanelProps {
  orgId: string;
  hasLocations: boolean;
  hasJobRoles: boolean;
}

export function ManagerSetupPanel({ orgId, hasLocations, hasJobRoles }: ManagerSetupPanelProps) {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [locationName, setLocationName] = useState("Main");
  const [roleName, setRoleName] = useState("Cashier");
  const [employeeName, setEmployeeName] = useState("");
  const [employeeEmail, setEmployeeEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["locations", orgId] });
    void queryClient.invalidateQueries({ queryKey: ["job-roles", orgId] });
    void queryClient.invalidateQueries({ queryKey: ["employees", orgId] });
  };

  const locationMutation = useMutation({
    mutationFn: () => resourceApi.createLocation(orgId, token!, { name: locationName }),
    onSuccess: invalidate,
  });

  const roleMutation = useMutation({
    mutationFn: () => resourceApi.createJobRole(orgId, token!, { name: roleName }),
    onSuccess: invalidate,
  });

  const employeeMutation = useMutation({
    mutationFn: async () => {
      const roles = await resourceApi.jobRoles(orgId, token!);
      const locations = await resourceApi.locations(orgId, token!);
      const roleId = roles[0]?.id;
      const locationId = locations[0]?.id;
      if (!roleId) throw new Error("Create a job role first");

      return resourceApi.addMember(orgId, token!, {
        email: employeeEmail,
        full_name: employeeName,
        password: "password123",
        membership_role: "EMPLOYEE",
        location_id: locationId,
        job_role_ids: [roleId],
      });
    },
    onSuccess: () => {
      invalidate();
      setEmployeeName("");
      setEmployeeEmail("");
    },
  });

  const run = async (action: () => Promise<unknown>) => {
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Failed");
    }
  };

  if (hasLocations && hasJobRoles) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Add employee</h2>
        <p className="mt-1 text-sm text-slate-500">Invite someone to assign shifts.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <input
            placeholder="Full name"
            className="rounded-md border border-slate-300 px-3 py-2"
            value={employeeName}
            onChange={(e) => setEmployeeName(e.target.value)}
          />
          <input
            placeholder="Email"
            className="rounded-md border border-slate-300 px-3 py-2"
            value={employeeEmail}
            onChange={(e) => setEmployeeEmail(e.target.value)}
          />
          <button
            type="button"
            onClick={() => run(() => employeeMutation.mutateAsync())}
            className="rounded-md bg-slate-900 px-4 py-2 text-white hover:bg-slate-800"
          >
            Add employee
          </button>
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-amber-200 bg-amber-50 p-6">
      <h2 className="text-lg font-medium text-amber-900">Quick setup</h2>
      <p className="mt-1 text-sm text-amber-800">
        Create a location and job role before scheduling.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        {!hasLocations && (
          <>
            <input
              className="rounded-md border border-slate-300 px-3 py-2"
              value={locationName}
              onChange={(e) => setLocationName(e.target.value)}
            />
            <button
              type="button"
              onClick={() => run(() => locationMutation.mutateAsync())}
              className="rounded-md bg-slate-900 px-4 py-2 text-white"
            >
              Add location
            </button>
          </>
        )}
        {!hasJobRoles && (
          <>
            <input
              className="rounded-md border border-slate-300 px-3 py-2"
              value={roleName}
              onChange={(e) => setRoleName(e.target.value)}
            />
            <button
              type="button"
              onClick={() => run(() => roleMutation.mutateAsync())}
              className="rounded-md bg-slate-900 px-4 py-2 text-white"
            >
              Add job role
            </button>
          </>
        )}
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </section>
  );
}
