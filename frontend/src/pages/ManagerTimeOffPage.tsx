import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../context/AuthContext";
import { timeOffApi } from "../shared/services";

function formatDate(dateStr: string): string {
  return new Date(`${dateStr}T12:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function ManagerTimeOffPage() {
  const { organization, token } = useAuth();
  const queryClient = useQueryClient();
  const orgId = organization?.id ?? "";

  const pendingQuery = useQuery({
    queryKey: ["time-off", "pending", orgId],
    queryFn: () => timeOffApi.list(orgId, token!, "PENDING"),
    enabled: Boolean(orgId && token),
  });

  const approveMutation = useMutation({
    mutationFn: (requestId: string) => timeOffApi.approve(orgId, requestId, token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["time-off", "pending", orgId] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (requestId: string) => timeOffApi.reject(orgId, requestId, token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["time-off", "pending", orgId] });
    },
  });

  return (
    <div className="space-y-6" data-testid="manager-time-off-page">
      <div>
        <h1 className="text-2xl font-semibold">Time-off requests</h1>
        <p className="text-sm text-slate-500">Review and approve employee time away.</p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Pending queue</h2>
        {pendingQuery.isLoading && <p className="mt-3 text-slate-600">Loading...</p>}
        {pendingQuery.data?.length === 0 && (
          <p className="mt-3 text-sm text-slate-500">No pending requests.</p>
        )}
        {pendingQuery.data && pendingQuery.data.length > 0 && (
          <ul className="mt-4 space-y-3">
            {pendingQuery.data.map((request) => (
              <li
                key={request.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-100 px-4 py-3"
              >
                <div>
                  <p className="font-medium">{request.employee_name ?? "Employee"}</p>
                  <p className="text-sm text-slate-600">
                    {formatDate(request.start_date)} – {formatDate(request.end_date)}
                  </p>
                  {request.reason && <p className="text-sm text-slate-500">{request.reason}</p>}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    data-testid="approve-time-off-button"
                    onClick={() => approveMutation.mutate(request.id)}
                    disabled={approveMutation.isPending || rejectMutation.isPending}
                    className="rounded-md bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    data-testid="reject-time-off-button"
                    onClick={() => rejectMutation.mutate(request.id)}
                    disabled={approveMutation.isPending || rejectMutation.isPending}
                    className="rounded-md bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
