import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { useAuth } from "../context/AuthContext";
import { ApiError } from "../shared/api";
import { formatDate, getMonday } from "../shared/dates";
import { resourceApi, schedulingApi } from "../shared/services";

const schema = z.object({
  location_id: z.string().min(1, "Select a location"),
  job_role_id: z.string().min(1, "Select a role"),
  shift_date: z.string().min(1, "Select a date"),
  start_time: z.string().min(1, "Start time required"),
  end_time: z.string().min(1, "End time required"),
  headcount: z.number().min(1).max(50),
});

type FormValues = z.infer<typeof schema>;

export function CreateCoveragePage() {
  const { organization, token } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const weekStart = formatDate(getMonday());

  const orgId = organization?.id ?? "";

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

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      shift_date: weekStart,
      start_time: "09:00",
      end_time: "17:00",
      headcount: 1,
    },
  });

  const onSubmit = async (values: FormValues) => {
    if (!token || !orgId) return;
    setError(null);
    try {
      const shiftDate = new Date(`${values.shift_date}T12:00:00`);
      const monday = getMonday(shiftDate);
      await schedulingApi.createCoverageRequirement(orgId, token, {
        ...values,
        week_start: formatDate(monday),
        start_time: `${values.start_time}:00`,
        end_time: `${values.end_time}:00`,
      });
      navigate("/manager/schedule");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create coverage");
    }
  };

  const locations = locationsQuery.data ?? [];
  const jobRoles = jobRolesQuery.data ?? [];

  return (
    <div className="mx-auto max-w-xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">New coverage requirement</h1>
        <Link to="/manager/schedule" className="text-sm text-blue-600 hover:underline">
          Back to schedule
        </Link>
      </div>

      {(locations.length === 0 || jobRoles.length === 0) && (
        <p className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
          Create at least one location and job role via the API or add seed data before scheduling.
        </p>
      )}

      <form data-testid="create-coverage-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label htmlFor="coverage_location_id" className="mb-1 block text-sm font-medium">
            Location
          </label>
          <select
            id="coverage_location_id"
            className="w-full rounded-md border border-slate-300 px-3 py-2"
            {...register("location_id")}
          >
            <option value="">Select location</option>
            {locations.map((location) => (
              <option key={location.id} value={location.id}>
                {location.name}
              </option>
            ))}
          </select>
          {errors.location_id && <p className="mt-1 text-sm text-red-600">{errors.location_id.message}</p>}
        </div>

        <div>
          <label htmlFor="coverage_job_role_id" className="mb-1 block text-sm font-medium">
            Job role
          </label>
          <select
            id="coverage_job_role_id"
            className="w-full rounded-md border border-slate-300 px-3 py-2"
            {...register("job_role_id")}
          >
            <option value="">Select role</option>
            {jobRoles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
          {errors.job_role_id && <p className="mt-1 text-sm text-red-600">{errors.job_role_id.message}</p>}
        </div>

        <div>
          <label htmlFor="coverage_shift_date" className="mb-1 block text-sm font-medium">
            Shift date
          </label>
          <input
            id="coverage_shift_date"
            type="date"
            className="w-full rounded-md border border-slate-300 px-3 py-2"
            {...register("shift_date")}
          />
          {errors.shift_date && <p className="mt-1 text-sm text-red-600">{errors.shift_date.message}</p>}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Start time</label>
            <input type="time" className="w-full rounded-md border border-slate-300 px-3 py-2" {...register("start_time")} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">End time</label>
            <input type="time" className="w-full rounded-md border border-slate-300 px-3 py-2" {...register("end_time")} />
          </div>
        </div>

        <div>
          <label htmlFor="coverage_headcount" className="mb-1 block text-sm font-medium">
            Headcount
          </label>
          <input
            id="coverage_headcount"
            type="number"
            min={1}
            className="w-full rounded-md border border-slate-300 px-3 py-2"
            {...register("headcount", { valueAsNumber: true })}
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {isSubmitting ? "Saving..." : "Create coverage"}
        </button>
      </form>
    </div>
  );
}
