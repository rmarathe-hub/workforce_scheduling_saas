import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../context/AuthContext";
import { notificationsApi } from "../shared/services";

export function NotificationBell() {
  const { organization, token } = useAuth();
  const orgId = organization?.id ?? "";

  const notificationsQuery = useQuery({
    queryKey: ["notifications", orgId],
    queryFn: () => notificationsApi.list(orgId, token!),
    enabled: Boolean(orgId && token),
    refetchInterval: 60_000,
  });

  const unreadCount = notificationsQuery.data?.unread_count ?? 0;

  return (
    <Link
      to="/notifications"
      className="relative inline-flex items-center text-blue-600 hover:underline"
      data-testid="notification-bell"
    >
      Notifications
      {unreadCount > 0 && (
        <span
          className="ml-1 inline-flex min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 py-0.5 text-xs font-medium text-white"
          data-testid="notification-unread-count"
        >
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}
    </Link>
  );
}
