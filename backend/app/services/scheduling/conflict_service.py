"""Load org scheduling data and run conflict detection."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models.availability_window import AvailabilityWindow
from app.models.coverage_requirement import CoverageRequirement
from app.models.employee_profile import EmployeeProfile
from app.models.organization import Organization
from app.models.shift import Shift
from app.models.time_off_request import TimeOffRequest
from app.services.org_validation import get_week_end
from app.services.scheduling.conflict_detector import (
    AvailabilitySnapshot,
    Conflict,
    ConflictDetectorInput,
    CoverageRequirementSnapshot,
    EmployeeRoleSnapshot,
    ShiftSnapshot,
    TimeOffSnapshot,
    detect_conflicts,
    summarize_conflicts,
)


def _build_detector_input(
    db: Session,
    organization_id: uuid.UUID,
    week_start: date,
) -> ConflictDetectorInput:
    organization = db.get(Organization, organization_id)
    assert organization is not None
    week_end = get_week_end(week_start)

    shifts = db.scalars(
        select(Shift).where(
            Shift.organization_id == organization_id,
            Shift.shift_date >= week_start,
            Shift.shift_date <= week_end,
        )
    ).all()

    requirements = db.scalars(
        select(CoverageRequirement).where(
            CoverageRequirement.organization_id == organization_id,
            CoverageRequirement.week_start == week_start,
        )
    ).all()

    availability = db.scalars(
        select(AvailabilityWindow).where(
            AvailabilityWindow.organization_id == organization_id,
        )
    ).all()

    time_off = db.scalars(
        select(TimeOffRequest).where(
            TimeOffRequest.organization_id == organization_id,
        )
    ).all()

    profiles = db.scalars(
        select(EmployeeProfile)
        .where(EmployeeProfile.organization_id == organization_id)
        .options(selectinload(EmployeeProfile.job_roles))
    ).all()

    return ConflictDetectorInput(
        week_start=week_start,
        shifts=[
            ShiftSnapshot(
                id=shift.id,
                shift_date=shift.shift_date,
                start_time=shift.start_time,
                end_time=shift.end_time,
                job_role_id=shift.job_role_id,
                assignee_id=shift.assignee_id,
                coverage_requirement_id=shift.coverage_requirement_id,
            )
            for shift in shifts
        ],
        availability=[
            AvailabilitySnapshot(
                employee_id=window.employee_id,
                day_of_week=window.day_of_week,
                start_time=window.start_time,
                end_time=window.end_time,
            )
            for window in availability
        ],
        time_off=[
            TimeOffSnapshot(
                employee_id=request.employee_id,
                start_date=request.start_date,
                end_date=request.end_date,
                status=request.status.value,
            )
            for request in time_off
        ],
        employee_roles=[
            EmployeeRoleSnapshot(
                employee_id=profile.user_id,
                job_role_ids=frozenset(role.id for role in profile.job_roles),
            )
            for profile in profiles
        ],
        coverage_requirements=[
            CoverageRequirementSnapshot(
                id=requirement.id,
                shift_date=requirement.shift_date,
                start_time=requirement.start_time,
                end_time=requirement.end_time,
                job_role_id=requirement.job_role_id,
                headcount=requirement.headcount,
            )
            for requirement in requirements
        ],
        max_weekly_hours=settings.max_weekly_hours,
        org_timezone=organization.timezone,
    )


def get_week_conflicts(
    db: Session,
    organization_id: uuid.UUID,
    week_start: date,
) -> tuple[list[Conflict], dict[str, int]]:
    detector_input = _build_detector_input(db, organization_id, week_start)
    conflicts = detect_conflicts(detector_input)
    return conflicts, summarize_conflicts(conflicts)


def get_shift_conflicts(
    db: Session,
    organization_id: uuid.UUID,
    week_start: date,
    shift_id: uuid.UUID,
) -> list[Conflict]:
    conflicts, _ = get_week_conflicts(db, organization_id, week_start)
    return [conflict for conflict in conflicts if conflict.shift_id == shift_id]
