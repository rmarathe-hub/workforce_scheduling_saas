import type { DashboardAnalytics } from "../types";

interface ManagerAnalyticsCardsProps {
  analytics: DashboardAnalytics | undefined;
  isLoading: boolean;
}

const CARDS: {
  key: keyof DashboardAnalytics;
  label: string;
  format: (value: DashboardAnalytics) => string;
}[] = [
  { key: "total_employees", label: "Employees", format: (data) => String(data.total_employees) },
  {
    key: "published_shifts",
    label: "Published shifts",
    format: (data) => String(data.published_shifts),
  },
  { key: "open_shifts", label: "Open shifts", format: (data) => String(data.open_shifts) },
  {
    key: "pending_time_off",
    label: "Pending time off",
    format: (data) => String(data.pending_time_off),
  },
  {
    key: "pending_shift_swaps",
    label: "Pending swaps",
    format: (data) => String(data.pending_shift_swaps),
  },
  {
    key: "conflict_count",
    label: "Conflicts",
    format: (data) => String(data.conflict_count),
  },
  {
    key: "coverage_fill_rate",
    label: "Coverage fill",
    format: (data) => `${data.coverage_fill_rate.toFixed(1)}%`,
  },
  {
    key: "scheduled_hours",
    label: "Scheduled hours",
    format: (data) => `${data.scheduled_hours.toFixed(1)}h`,
  },
];

export function ManagerAnalyticsCards({ analytics, isLoading }: ManagerAnalyticsCardsProps) {
  return (
    <section
      className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      data-testid="manager-analytics-cards"
    >
      <h2 className="text-lg font-medium">Week overview</h2>
      <p className="mt-1 text-sm text-slate-500">Live metrics for the selected schedule week.</p>
      {isLoading && <p className="mt-4 text-sm text-slate-600">Loading analytics...</p>}
      {analytics && (
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CARDS.map((card) => (
            <div
              key={card.key}
              className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3"
              data-testid={`analytics-card-${card.key}`}
            >
              <p className="text-sm text-slate-600">{card.label}</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">
                {card.format(analytics)}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
