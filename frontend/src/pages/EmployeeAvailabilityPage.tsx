import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "../context/AuthContext";
import { availabilityApi } from "../shared/services";

const DAYS = [
  { value: 0, label: "Monday" },
  { value: 1, label: "Tuesday" },
  { value: 2, label: "Wednesday" },
  { value: 3, label: "Thursday" },
  { value: 4, label: "Friday" },
  { value: 5, label: "Saturday" },
  { value: 6, label: "Sunday" },
];

function formatTime(time: string): string {
  return time.slice(0, 5);
}

export function EmployeeAvailabilityPage() {
  const { organization, token } = useAuth();
  const queryClient = useQueryClient();
  const orgId = organization?.id ?? "";

  const [dayOfWeek, setDayOfWeek] = useState(0);
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("17:00");
  const [error, setError] = useState<string | null>(null);

  const availabilityQuery = useQuery({
    queryKey: ["availability", "me", orgId],
    queryFn: () => availabilityApi.mine(orgId, token!),
    enabled: Boolean(orgId && token),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      availabilityApi.create(orgId, token!, {
        day_of_week: dayOfWeek,
        start_time: `${startTime}:00`,
        end_time: `${endTime}:00`,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["availability", "me", orgId] });
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (windowId: string) => availabilityApi.remove(orgId, windowId, token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["availability", "me", orgId] });
    },
  });

  return (
    <div className="space-y-6" data-testid="employee-availability-page">
      <div>
        <h1 className="text-2xl font-semibold">My availability</h1>
        <p className="text-sm text-slate-500">Set recurring weekly windows when you can work.</p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Add window</h2>
        <form
          data-testid="availability-form"
          className="mt-4 grid gap-4 md:grid-cols-4"
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate();
          }}
        >
          <div>
            <label className="mb-1 block text-sm font-medium">Day</label>
            <select
              className="w-full rounded-md border border-slate-300 px-3 py-2"
              value={dayOfWeek}
              onChange={(e) => setDayOfWeek(Number(e.target.value))}
            >
              {DAYS.map((day) => (
                <option key={day.value} value={day.value}>
                  {day.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Start</label>
            <input
              type="time"
              className="w-full rounded-md border border-slate-300 px-3 py-2"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">End</label>
            <input
              type="time"
              className="w-full rounded-md border border-slate-300 px-3 py-2"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="w-full rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? "Saving..." : "Add window"}
            </button>
          </div>
        </form>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Your windows</h2>
        {availabilityQuery.isLoading && <p className="mt-3 text-slate-600">Loading...</p>}
        {availabilityQuery.data?.length === 0 && (
          <p className="mt-3 text-sm text-slate-500">No availability set yet.</p>
        )}
        {availabilityQuery.data && availabilityQuery.data.length > 0 && (
          <ul className="mt-4 space-y-2">
            {availabilityQuery.data.map((window) => (
              <li
                key={window.id}
                className="flex items-center justify-between rounded-md border border-slate-100 px-4 py-3"
              >
                <span>
                  {window.day_name ?? DAYS[window.day_of_week]?.label} ·{" "}
                  {formatTime(window.start_time)} – {formatTime(window.end_time)}
                </span>
                <button
                  type="button"
                  onClick={() => deleteMutation.mutate(window.id)}
                  className="text-sm text-red-600 hover:underline"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
