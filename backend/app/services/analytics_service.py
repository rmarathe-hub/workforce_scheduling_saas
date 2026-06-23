"""Organization-scoped manager dashboard analytics."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.coverage_requirement import CoverageRequirement
from app.models.employee_profile import EmployeeProfile
from app.models.enums import ShiftStatus, ShiftSwapStatus, TimeOffStatus
from app.models.shift import Shift
from app.models.shift_swap_request import ShiftSwapRequest
from app.models.time_off_request import TimeOffRequest
from app.schemas.analytics import DashboardAnalyticsResponse
from app.services.org_validation import get_week_end
from app.services.scheduling.conflict_detector import _duration_hours
from app.services.scheduling.conflict_service import get_week_conflicts


def get_dashboard_analytics(
    db: Session,
    organization_id: uuid.UUID,
    week_start: date,
) -> DashboardAnalyticsResponse:
    week_end = get_week_end(week_start)

    total_employees = db.scalar(
        select(func.count())
        .select_from(EmployeeProfile)
        .where(EmployeeProfile.organization_id == organization_id)
    )
    assert total_employees is not None

    week_shifts = list(
        db.scalars(
            select(Shift).where(
                Shift.organization_id == organization_id,
                Shift.shift_date >= week_start,
                Shift.shift_date <= week_end,
            )
        ).all()
    )

    published_shifts = sum(
        1 for shift in week_shifts if shift.status == ShiftStatus.PUBLISHED
    )
    open_shifts = sum(1 for shift in week_shifts if shift.assignee_id is None)

    pending_time_off = db.scalar(
        select(func.count())
        .select_from(TimeOffRequest)
        .where(
            TimeOffRequest.organization_id == organization_id,
            TimeOffRequest.status == TimeOffStatus.PENDING,
        )
    )
    assert pending_time_off is not None

    pending_shift_swaps = db.scalar(
        select(func.count())
        .select_from(ShiftSwapRequest)
        .where(
            ShiftSwapRequest.organization_id == organization_id,
            ShiftSwapRequest.status == ShiftSwapStatus.PENDING,
        )
    )
    assert pending_shift_swaps is not None

    _, conflict_summary = get_week_conflicts(db, organization_id, week_start)

    requirements = list(
        db.scalars(
            select(CoverageRequirement).where(
                CoverageRequirement.organization_id == organization_id,
                CoverageRequirement.week_start == week_start,
            )
        ).all()
    )

    total_required_slots = sum(requirement.headcount for requirement in requirements)
    filled_slots = 0
    for requirement in requirements:
        assigned_count = sum(
            1
            for shift in week_shifts
            if shift.coverage_requirement_id == requirement.id and shift.assignee_id is not None
        )
        filled_slots += min(assigned_count, requirement.headcount)

    if total_required_slots == 0:
        coverage_fill_rate = 100.0
    else:
        coverage_fill_rate = round((filled_slots / total_required_slots) * 100, 1)

    scheduled_hours = round(
        sum(
            _duration_hours(shift.start_time, shift.end_time)
            for shift in week_shifts
            if shift.assignee_id is not None
        ),
        1,
    )

    return DashboardAnalyticsResponse(
        week_start=week_start,
        week_end=week_end,
        total_employees=total_employees,
        published_shifts=published_shifts,
        open_shifts=open_shifts,
        pending_time_off=pending_time_off,
        pending_shift_swaps=pending_shift_swaps,
        conflict_count=conflict_summary["total"],
        coverage_fill_rate=coverage_fill_rate,
        scheduled_hours=scheduled_hours,
    )
