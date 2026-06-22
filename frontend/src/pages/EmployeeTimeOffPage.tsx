import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "../context/AuthContext";
import { timeOffApi } from "../shared/services";
import type { TimeOffRequest } from "../types";

function formatDate(dateStr: string): string {
  return new Date(`${dateStr}T12:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function EmployeeTimeOffPage() {
  const { organization, token } = useAuth();
  const queryClient = useQueryClient();
  const orgId = organization?.id ?? "";

  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const requestsQuery = useQuery({
    queryKey: ["time-off", "me", orgId],
    queryFn: () => timeOffApi.mine(orgId, token!),
    enabled: Boolean(orgId && token),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      timeOffApi.create(orgId, token!, {
        start_date: startDate,
        end_date: endDate,
        reason: reason || undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["time-off", "me", orgId] });
      setStartDate("");
      setEndDate("");
      setReason("");
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const cancelMutation = useMutation({
    mutationFn: (requestId: string) => timeOffApi.cancel(orgId, requestId, token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["time-off", "me", orgId] });
    },
  });

  return (
    <div className="space-y-6" data-testid="employee-time-off-page">
      <div>
        <h1 className="text-2xl font-semibold">Time off</h1>
        <p className="text-sm text-slate-500">Request time away from scheduled shifts.</p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">New request</h2>
        <form
          data-testid="time-off-form"
          className="mt-4 grid gap-4 md:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            createMutation.mutate();
          }}
        >
          <div>
            <label htmlFor="start_date" className="mb-1 block text-sm font-medium">
              Start date
            </label>
            <input
              id="start_date"
              type="date"
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="end_date" className="mb-1 block text-sm font-medium">
              End date
            </label>
            <input
              id="end_date"
              type="date"
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <div className="md:col-span-2">
            <label htmlFor="reason" className="mb-1 block text-sm font-medium">
              Reason (optional)
            </label>
            <textarea
              id="reason"
              className="w-full rounded-md border border-slate-300 px-3 py-2"
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <div className="md:col-span-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="rounded-md bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createMutation.isPending ? "Submitting..." : "Submit request"}
            </button>
          </div>
        </form>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">My requests</h2>
        {requestsQuery.isLoading && <p className="mt-3 text-slate-600">Loading...</p>}
        {requestsQuery.data?.length === 0 && (
          <p className="mt-3 text-sm text-slate-500">No time-off requests yet.</p>
        )}
        {requestsQuery.data && requestsQuery.data.length > 0 && (
          <ul className="mt-4 space-y-3">
            {requestsQuery.data.map((request: TimeOffRequest) => (
              <li
                key={request.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-100 px-4 py-3"
              >
                <div>
                  <p className="font-medium">
                    {formatDate(request.start_date)} – {formatDate(request.end_date)}
                  </p>
                  {request.reason && <p className="text-sm text-slate-500">{request.reason}</p>}
                </div>
                <div className="flex items-center gap-3">
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">{request.status}</span>
                  {request.status === "PENDING" && (
                    <button
                      type="button"
                      onClick={() => cancelMutation.mutate(request.id)}
                      className="text-sm text-red-600 hover:underline"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
