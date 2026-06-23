from datetime import date

from pydantic import BaseModel


class DashboardAnalyticsResponse(BaseModel):
    week_start: date
    week_end: date
    total_employees: int
    published_shifts: int
    open_shifts: int
    pending_time_off: int
    pending_shift_swaps: int
    conflict_count: int
    coverage_fill_rate: float
    scheduled_hours: float
