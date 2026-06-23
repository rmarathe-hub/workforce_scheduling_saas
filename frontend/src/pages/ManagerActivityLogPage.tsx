import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../context/AuthContext";
import { auditLogApi } from "../shared/services";
import type { AuditAction } from "../types";

const ACTION_LABELS: Record<AuditAction, string> = {
  SHIFT_SWAP_REQUESTED: "Shift swap requested",
  SHIFT_SWAP_APPROVED: "Shift swap approved",
  SHIFT_SWAP_REJECTED: "Shift swap rejected",
  SCHEDULE_GENERATED: "Schedule generated",
  SCHEDULE_PUBLISHED: "Schedule published",
  TIME_OFF_APPROVED: "Time off approved",
  TIME_OFF_REJECTED: "Time off rejected",
};

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function ManagerActivityLogPage() {
  const { organization, token } = useAuth();
  const orgId = organization?.id ?? "";

  const logsQuery = useQuery({
    queryKey: ["audit-logs", orgId],
    queryFn: () => auditLogApi.list(orgId, token!),
    enabled: Boolean(orgId && token),
  });

  return (
    <div className="space-y-6" data-testid="manager-activity-log-page">
      <div>
        <h1 className="text-2xl font-semibold">Activity log</h1>
        <p className="text-sm text-slate-500">
          Recent scheduling, swap, and time-off actions in your organization.
        </p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {logsQuery.isLoading && <p className="text-slate-600">Loading activity...</p>}
        {logsQuery.data?.items.length === 0 && (
          <p className="text-sm text-slate-500" data-testid="activity-log-empty">
            No activity recorded yet.
          </p>
        )}
        {logsQuery.data && logsQuery.data.items.length > 0 && (
          <ul className="divide-y divide-slate-100">
            {logsQuery.data.items.map((entry) => (
              <li
                key={entry.id}
                className="flex flex-wrap items-start justify-between gap-3 py-3"
                data-testid="activity-log-entry"
              >
                <div>
                  <p className="font-medium">{ACTION_LABELS[entry.action]}</p>
                  <p className="text-sm text-slate-600">
                    {entry.actor_name ?? "User"} · {entry.entity_type.replace(/_/g, " ")}
                  </p>
                  {entry.metadata?.week_start != null && (
                    <p className="text-sm text-slate-500">
                      Week of {String(entry.metadata.week_start)}
                    </p>
                  )}
                  {entry.metadata?.request_type != null && (
                    <p className="text-sm text-slate-500">
                      Type: {String(entry.metadata.request_type)}
                    </p>
                  )}
                </div>
                <time className="text-sm text-slate-500">{formatTimestamp(entry.created_at)}</time>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
