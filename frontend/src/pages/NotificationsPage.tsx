import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../context/AuthContext";
import { notificationsApi } from "../shared/services";
import type { NotificationType } from "../types";

const TYPE_LABELS: Record<NotificationType, string> = {
  SCHEDULE_PUBLISHED: "Schedule published",
  TIME_OFF_APPROVED: "Time off approved",
  TIME_OFF_REJECTED: "Time off rejected",
  SHIFT_SWAP_REQUESTED: "Shift swap requested",
  SHIFT_SWAP_APPROVED: "Shift swap approved",
  SHIFT_SWAP_REJECTED: "Shift swap rejected",
  DOCUMENT_UPLOADED: "Document uploaded",
  OPEN_SHIFT_CREATED: "Open shifts created",
};

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function notificationStatusLabel(notification: {
  read_at: string | null;
  status: string;
}): string {
  if (notification.read_at !== null || notification.status === "READ") {
    return "Read";
  }
  return "Unread";
}

function notificationStatusClass(notification: {
  read_at: string | null;
  status: string;
}): string {
  if (notification.read_at !== null || notification.status === "READ") {
    return "bg-slate-200 text-slate-700";
  }
  return "bg-blue-600 text-white";
}

export function NotificationsPage() {
  const { organization, token } = useAuth();
  const queryClient = useQueryClient();
  const orgId = organization?.id ?? "";

  const notificationsQuery = useQuery({
    queryKey: ["notifications", orgId],
    queryFn: () => notificationsApi.list(orgId, token!),
    enabled: Boolean(orgId && token),
  });

  const readMutation = useMutation({
    mutationFn: (notificationId: string) => notificationsApi.markRead(orgId, notificationId, token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications", orgId] });
    },
  });

  const readAllMutation = useMutation({
    mutationFn: () => notificationsApi.markAllRead(orgId, token!),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications", orgId] });
    },
  });

  return (
    <div className="space-y-6" data-testid="notifications-page">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Notifications</h1>
          <p className="text-sm text-slate-500">
            {notificationsQuery.data?.unread_count ?? 0} unread
          </p>
        </div>
        {(notificationsQuery.data?.unread_count ?? 0) > 0 && (
          <button
            type="button"
            onClick={() => readAllMutation.mutate()}
            disabled={readAllMutation.isPending}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm hover:bg-slate-50"
            data-testid="mark-all-notifications-read"
          >
            Mark all as read
          </button>
        )}
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        {notificationsQuery.isLoading && <p className="text-slate-600">Loading notifications...</p>}
        {notificationsQuery.data?.items.length === 0 && (
          <p className="text-sm text-slate-500" data-testid="notifications-empty">
            No notifications yet.
          </p>
        )}
        {notificationsQuery.data && notificationsQuery.data.items.length > 0 && (
          <ul className="divide-y divide-slate-100">
            {notificationsQuery.data.items.map((notification) => {
              const isUnread = notification.read_at === null;
              return (
                <li
                  key={notification.id}
                  className={`flex flex-wrap items-start justify-between gap-3 py-3 ${
                    isUnread ? "bg-blue-50/40" : ""
                  }`}
                  data-testid="notification-item"
                >
                  <div>
                    <p className="font-medium">{notification.title}</p>
                    <p className="text-sm text-slate-600">{TYPE_LABELS[notification.type]}</p>
                    <p className="mt-1 text-sm text-slate-700">{notification.message}</p>
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${notificationStatusClass(notification)}`}
                      data-testid="notification-status-badge"
                    >
                      {notificationStatusLabel(notification)}
                    </span>
                    <time className="text-sm text-slate-500">
                      {formatTimestamp(notification.created_at)}
                    </time>
                    {isUnread && (
                      <button
                        type="button"
                        onClick={() => readMutation.mutate(notification.id)}
                        disabled={readMutation.isPending}
                        className="text-sm text-blue-600 hover:underline"
                        data-testid="mark-notification-read"
                      >
                        Mark read
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}
