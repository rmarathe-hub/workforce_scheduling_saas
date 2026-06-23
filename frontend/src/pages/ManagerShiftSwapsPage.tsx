import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../context/AuthContext";
import { formatDayLabel, formatTime } from "../shared/dates";
import { shiftSwapApi } from "../shared/services";

export function ManagerShiftSwapsPage() {
  const { organization, token } = useAuth();
  const queryClient = useQueryClient();
  const orgId = organization?.id ?? "";

  const pendingQuery = useQuery({
    queryKey: ["shift-swaps", "pending", orgId],
    queryFn: () => shiftSwapApi.list(orgId, token!, "PENDING"),
    enabled: Boolean(orgId && token),
  });

  const approveMutation = useMutation({
    mutationFn: (requestId: string) => shiftSwapApi.approve(orgId, requestId, token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["shift-swaps", "pending", orgId] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (requestId: string) => shiftSwapApi.reject(orgId, requestId, token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["shift-swaps", "pending", orgId] });
    },
  });

  return (
    <div className="space-y-6" data-testid="manager-shift-swaps-page">
      <div>
        <h1 className="text-2xl font-semibold">Shift swap requests</h1>
        <p className="text-sm text-slate-500">
          Review employee give-up and swap requests before updating the schedule.
        </p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-medium">Pending queue</h2>
        {pendingQuery.isLoading && <p className="mt-3 text-slate-600">Loading...</p>}
        {pendingQuery.data?.length === 0 && (
          <p className="mt-3 text-sm text-slate-500" data-testid="shift-swaps-empty">
            No pending requests.
          </p>
        )}
        {pendingQuery.data && pendingQuery.data.length > 0 && (
          <ul className="mt-4 space-y-3">
            {pendingQuery.data.map((request) => (
              <li
                key={request.id}
                className="rounded-md border border-slate-100 px-4 py-3"
                data-testid="shift-swap-request-card"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium">{request.requester_name ?? "Employee"}</p>
                    <p className="text-sm text-slate-600">
                      {request.request_type === "GIVE_UP" ? "Give up shift" : "Swap shift"}
                    </p>
                    {request.original_shift && (
                      <p className="mt-1 text-sm text-slate-700">
                        {formatDayLabel(request.original_shift.shift_date)} ·{" "}
                        {formatTime(request.original_shift.start_time)} –{" "}
                        {formatTime(request.original_shift.end_time)}
                      </p>
                    )}
                    {request.request_type === "SWAP" && request.requested_shift && (
                      <p className="text-sm text-slate-600">
                        Swap with {request.target_employee_name ?? "employee"} on{" "}
                        {formatDayLabel(request.requested_shift.shift_date)} (
                        {formatTime(request.requested_shift.start_time)} –{" "}
                        {formatTime(request.requested_shift.end_time)})
                      </p>
                    )}
                    {request.reason && (
                      <p className="mt-1 text-sm text-slate-500">{request.reason}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      data-testid="approve-shift-swap-button"
                      onClick={() => approveMutation.mutate(request.id)}
                      disabled={approveMutation.isPending || rejectMutation.isPending}
                      className="rounded-md bg-green-600 px-3 py-1.5 text-sm text-white hover:bg-green-700 disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      data-testid="reject-shift-swap-button"
                      onClick={() => rejectMutation.mutate(request.id)}
                      disabled={approveMutation.isPending || rejectMutation.isPending}
                      className="rounded-md bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                </div>
                {approveMutation.isError && (
                  <p className="mt-2 text-sm text-red-600">
                    {approveMutation.error instanceof Error
                      ? approveMutation.error.message
                      : "Approval failed"}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
