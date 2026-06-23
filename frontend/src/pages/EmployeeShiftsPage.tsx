import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "../context/AuthContext";
import { addDays, formatDate, formatDayLabel, formatTime, getMonday } from "../shared/dates";
import { schedulingApi, shiftSwapApi } from "../shared/services";
import type { Shift, ShiftSwapRequest } from "../types";

function shiftHasPendingRequest(shiftId: string, requests: ShiftSwapRequest[] | undefined) {
  return requests?.some(
    (request) => request.original_shift_id === shiftId && request.status === "PENDING",
  );
}

export function EmployeeShiftsPage() {
  const { organization, token, user } = useAuth();
  const queryClient = useQueryClient();
  const [weekStart, setWeekStart] = useState(() => formatDate(getMonday()));
  const [swapShift, setSwapShift] = useState<Shift | null>(null);
  const [swapTargetId, setSwapTargetId] = useState("");
  const [reason, setReason] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const orgId = organization?.id ?? "";

  const shiftsQuery = useQuery({
    queryKey: ["my-shifts", orgId, weekStart],
    queryFn: () => schedulingApi.myShifts(orgId, weekStart, token!),
    enabled: Boolean(orgId && token),
  });

  const mySwapRequestsQuery = useQuery({
    queryKey: ["shift-swaps", "mine", orgId],
    queryFn: () => shiftSwapApi.mine(orgId, token!),
    enabled: Boolean(orgId && token),
  });

  const weekScheduleQuery = useQuery({
    queryKey: ["week-schedule", orgId, weekStart],
    queryFn: () => schedulingApi.weekSchedule(orgId, weekStart, token!),
    enabled: Boolean(orgId && token && swapShift !== null),
  });

  const swapTargets =
    weekScheduleQuery.data?.shifts.filter(
      (shift) =>
        shift.status === "PUBLISHED" &&
        shift.assignee_id &&
        shift.assignee_id !== user?.id &&
        shift.id !== swapShift?.id,
    ) ?? [];

  const giveUpMutation = useMutation({
    mutationFn: (shiftId: string) =>
      shiftSwapApi.create(orgId, token!, {
        request_type: "GIVE_UP",
        original_shift_id: shiftId,
        reason: reason || undefined,
      }),
    onSuccess: () => {
      setReason("");
      setActionError(null);
      void queryClient.invalidateQueries({ queryKey: ["shift-swaps", "mine", orgId] });
    },
    onError: (error: Error) => setActionError(error.message),
  });

  const swapMutation = useMutation({
    mutationFn: () =>
      shiftSwapApi.create(orgId, token!, {
        request_type: "SWAP",
        original_shift_id: swapShift!.id,
        requested_shift_id: swapTargetId,
        reason: reason || undefined,
      }),
    onSuccess: () => {
      setSwapShift(null);
      setSwapTargetId("");
      setReason("");
      setActionError(null);
      void queryClient.invalidateQueries({ queryKey: ["shift-swaps", "mine", orgId] });
    },
    onError: (error: Error) => setActionError(error.message),
  });

  const moveWeek = (delta: number) => {
    const monday = getMonday(new Date(`${weekStart}T12:00:00`));
    setWeekStart(formatDate(addDays(monday, delta * 7)));
  };

  return (
    <div className="space-y-6" data-testid="employee-shifts-page">
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

      {actionError && (
        <p className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700" role="alert">
          {actionError}
        </p>
      )}

      {shiftsQuery.isLoading && <p className="text-slate-600">Loading your shifts...</p>}

      {shiftsQuery.data && shiftsQuery.data.length === 0 && (
        <div
          className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500"
          data-testid="employee-shifts-empty"
        >
          No shifts assigned for this week.
        </div>
      )}

      {shiftsQuery.data && shiftsQuery.data.length > 0 && (
        <div className="grid gap-4">
          {shiftsQuery.data.map((shift) => {
            const pending = shiftHasPendingRequest(shift.id, mySwapRequestsQuery.data);
            return (
              <div
                key={shift.id}
                className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
                data-testid="employee-shift-card"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-lg font-medium">{formatDayLabel(shift.shift_date)}</h2>
                  <span className="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700">
                    {pending ? "Swap pending" : shift.status}
                  </span>
                </div>
                <p className="mt-2 text-slate-700">
                  {formatTime(shift.start_time)} – {formatTime(shift.end_time)}
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  {shift.job_role?.name ?? "Role"} · {shift.location?.name ?? "Location"}
                </p>
                {!pending && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      data-testid="give-up-shift-button"
                      onClick={() => {
                        setActionError(null);
                        giveUpMutation.mutate(shift.id);
                      }}
                      disabled={giveUpMutation.isPending}
                      className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50 disabled:opacity-50"
                    >
                      Give up shift
                    </button>
                    <button
                      type="button"
                      data-testid="request-swap-button"
                      onClick={() => {
                        setActionError(null);
                        setSwapShift(shift);
                        setSwapTargetId("");
                        setReason("");
                      }}
                      className="rounded-md bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
                    >
                      Request swap
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {swapShift && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          role="dialog"
          aria-modal="true"
          data-testid="swap-shift-dialog"
        >
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
            <h2 className="text-lg font-semibold">Request shift swap</h2>
            <p className="mt-1 text-sm text-slate-600">
              {formatDayLabel(swapShift.shift_date)} · {formatTime(swapShift.start_time)} –{" "}
              {formatTime(swapShift.end_time)}
            </p>

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="swap-target">
              Swap with another employee&apos;s shift
            </label>
            {weekScheduleQuery.isLoading && (
              <p className="mt-2 text-sm text-slate-500">Loading available shifts...</p>
            )}
            {weekScheduleQuery.data && swapTargets.length === 0 && (
              <p className="mt-2 text-sm text-slate-500">No other assigned shifts this week.</p>
            )}
            {swapTargets.length > 0 && (
              <select
                id="swap-target"
                value={swapTargetId}
                onChange={(event) => setSwapTargetId(event.target.value)}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
              >
                <option value="">Select a shift</option>
                {swapTargets.map((shift) => (
                  <option key={shift.id} value={shift.id}>
                    {formatDayLabel(shift.shift_date)} {formatTime(shift.start_time)} –{" "}
                    {formatTime(shift.end_time)} ({shift.assignee_name ?? "Employee"})
                  </option>
                ))}
              </select>
            )}

            <label className="mt-4 block text-sm font-medium text-slate-700" htmlFor="swap-reason">
              Reason (optional)
            </label>
            <textarea
              id="swap-reason"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              rows={3}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            />

            <div className="mt-6 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setSwapShift(null)}
                className="rounded-md border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                data-testid="submit-swap-request-button"
                onClick={() => swapMutation.mutate()}
                disabled={!swapTargetId || swapMutation.isPending}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                Submit request
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
