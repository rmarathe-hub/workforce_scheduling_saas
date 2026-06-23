"""
Automatic schedule generator (Week 3 Day 15).

Assigns draft shifts from coverage requirements using the same eligibility
rules as conflict_detector: role, availability, approved time off, overlap,
and weekly hour limits. Prefers employees with fewer scheduled hours.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, time

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models.availability_window import AvailabilityWindow
from app.models.coverage_requirement import CoverageRequirement
from app.models.employee_profile import EmployeeProfile
from app.models.enums import ShiftStatus
from app.models.organization import Organization
from app.models.shift import Shift
from app.models.time_off_request import TimeOffRequest
from app.services.org_validation import get_week_end
from app.services.scheduling.conflict_detector import (
    AvailabilitySnapshot,
    EmployeeRoleSnapshot,
    ShiftSnapshot,
    TimeOffSnapshot,
    _duration_hours,
    _shift_weekday,
    _shift_within_availability,
    _times_overlap,
)


@dataclass(frozen=True)
class GeneratorCoverageRequirement:
    id: uuid.UUID
    location_id: uuid.UUID
    job_role_id: uuid.UUID
    shift_date: date
    start_time: time
    end_time: time
    headcount: int


@dataclass(frozen=True)
class ProposedShift:
    coverage_requirement_id: uuid.UUID
    location_id: uuid.UUID
    job_role_id: uuid.UUID
    shift_date: date
    start_time: time
    end_time: time
    assignee_id: uuid.UUID | None


@dataclass
class ScheduleGeneratorInput:
    week_start: date
    coverage_requirements: list[GeneratorCoverageRequirement]
    existing_shifts: list[ShiftSnapshot] = field(default_factory=list)
    availability: list[AvailabilitySnapshot] = field(default_factory=list)
    time_off: list[TimeOffSnapshot] = field(default_factory=list)
    employee_roles: list[EmployeeRoleSnapshot] = field(default_factory=list)
    max_weekly_hours: float = settings.max_weekly_hours
    org_timezone: str = "America/New_York"


@dataclass
class ScheduleGeneratorResult:
    shifts: list[ProposedShift]
    assigned_count: int
    open_shift_count: int
    warnings: list[str]


def get_employee_weekly_hours(
    employee_id: uuid.UUID,
    shifts: list[ShiftSnapshot],
    week_start: date,
    week_end: date,
) -> float:
    total = 0.0
    for shift in shifts:
        if shift.assignee_id != employee_id:
            continue
        if not (week_start <= shift.shift_date <= week_end):
            continue
        total += _duration_hours(shift.start_time, shift.end_time)
    return total


def is_employee_available(
    employee_id: uuid.UUID,
    shift_date: date,
    start_time: time,
    end_time: time,
    availability: list[AvailabilitySnapshot],
    org_timezone: str,
) -> bool:
    employee_windows = [window for window in availability if window.employee_id == employee_id]
    if not employee_windows:
        return True

    shift = ShiftSnapshot(
        id=uuid.uuid4(),
        shift_date=shift_date,
        start_time=start_time,
        end_time=end_time,
        job_role_id=uuid.uuid4(),
        assignee_id=employee_id,
    )
    day = _shift_weekday(shift_date, org_timezone)
    day_windows = [window for window in employee_windows if window.day_of_week == day]
    return _shift_within_availability(shift, day_windows)


def has_time_off_conflict(
    employee_id: uuid.UUID,
    shift_date: date,
    time_off: list[TimeOffSnapshot],
) -> bool:
    for request in time_off:
        if request.employee_id != employee_id or request.status != "APPROVED":
            continue
        if request.start_date <= shift_date <= request.end_date:
            return True
    return False


def has_shift_overlap(
    employee_id: uuid.UUID,
    shift_date: date,
    start_time: time,
    end_time: time,
    shifts: list[ShiftSnapshot],
) -> bool:
    for shift in shifts:
        if shift.assignee_id != employee_id or shift.shift_date != shift_date:
            continue
        if _times_overlap(start_time, end_time, shift.start_time, shift.end_time):
            return True
    return False


def score_employee_for_shift(
    employee_id: uuid.UUID,
    shifts: list[ShiftSnapshot],
    week_start: date,
    week_end: date,
) -> float:
    return get_employee_weekly_hours(employee_id, shifts, week_start, week_end)


def _eligible_employees(
    requirement: GeneratorCoverageRequirement,
    generator_input: ScheduleGeneratorInput,
    assigned_shifts: list[ShiftSnapshot],
) -> list[uuid.UUID]:
    week_end = get_week_end(generator_input.week_start)
    shift_hours = _duration_hours(requirement.start_time, requirement.end_time)
    eligible: list[uuid.UUID] = []

    for entry in generator_input.employee_roles:
        employee_id = entry.employee_id
        if requirement.job_role_id not in entry.job_role_ids:
            continue
        if not is_employee_available(
            employee_id,
            requirement.shift_date,
            requirement.start_time,
            requirement.end_time,
            generator_input.availability,
            generator_input.org_timezone,
        ):
            continue
        if has_time_off_conflict(employee_id, requirement.shift_date, generator_input.time_off):
            continue
        if has_shift_overlap(
            employee_id,
            requirement.shift_date,
            requirement.start_time,
            requirement.end_time,
            assigned_shifts,
        ):
            continue
        current_hours = get_employee_weekly_hours(
            employee_id, assigned_shifts, generator_input.week_start, week_end
        )
        if current_hours + shift_hours > generator_input.max_weekly_hours:
            continue
        eligible.append(employee_id)

    eligible.sort(
        key=lambda employee_id: score_employee_for_shift(
            employee_id, assigned_shifts, generator_input.week_start, week_end
        )
    )
    return eligible


def generate_schedule(generator_input: ScheduleGeneratorInput) -> ScheduleGeneratorResult:
    """Pure assignment pass from coverage requirements to proposed shifts."""
    assigned_shifts = list(generator_input.existing_shifts)
    proposed: list[ProposedShift] = []
    warnings: list[str] = []
    assigned_count = 0
    open_shift_count = 0

    requirements = sorted(
        generator_input.coverage_requirements,
        key=lambda requirement: (requirement.shift_date, requirement.start_time, requirement.id),
    )

    for requirement in requirements:
        for _ in range(requirement.headcount):
            candidates = _eligible_employees(requirement, generator_input, assigned_shifts)
            assignee_id = candidates[0] if candidates else None

            proposed_shift = ProposedShift(
                coverage_requirement_id=requirement.id,
                location_id=requirement.location_id,
                job_role_id=requirement.job_role_id,
                shift_date=requirement.shift_date,
                start_time=requirement.start_time,
                end_time=requirement.end_time,
                assignee_id=assignee_id,
            )
            proposed.append(proposed_shift)

            if assignee_id is None:
                open_shift_count += 1
                warnings.append(
                    f"{requirement.shift_date} {requirement.start_time.strftime('%H:%M')}"
                    f"-{requirement.end_time.strftime('%H:%M')} shift could not be filled."
                )
            else:
                assigned_count += 1
                assigned_shifts.append(
                    ShiftSnapshot(
                        id=uuid.uuid4(),
                        shift_date=requirement.shift_date,
                        start_time=requirement.start_time,
                        end_time=requirement.end_time,
                        job_role_id=requirement.job_role_id,
                        assignee_id=assignee_id,
                        coverage_requirement_id=requirement.id,
                    )
                )

    return ScheduleGeneratorResult(
        shifts=proposed,
        assigned_count=assigned_count,
        open_shift_count=open_shift_count,
        warnings=warnings,
    )


def _build_generator_input(
    db: Session,
    organization_id: uuid.UUID,
    week_start: date,
) -> ScheduleGeneratorInput:
    organization = db.get(Organization, organization_id)
    assert organization is not None
    week_end = get_week_end(week_start)

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

    return ScheduleGeneratorInput(
        week_start=week_start,
        coverage_requirements=[
            GeneratorCoverageRequirement(
                id=requirement.id,
                location_id=requirement.location_id,
                job_role_id=requirement.job_role_id,
                shift_date=requirement.shift_date,
                start_time=requirement.start_time,
                end_time=requirement.end_time,
                headcount=requirement.headcount,
            )
            for requirement in requirements
        ],
        existing_shifts=[],
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
        max_weekly_hours=settings.max_weekly_hours,
        org_timezone=organization.timezone,
    )


def generate_weekly_schedule(
    db: Session,
    organization_id: uuid.UUID,
    week_start: date,
) -> ScheduleGeneratorResult:
    """
    Replace draft shifts for the week, then create new assignments from coverage.
    """
    week_end = get_week_end(week_start)
    generator_input = _build_generator_input(db, organization_id, week_start)
    result = generate_schedule(generator_input)

    db.execute(
        delete(Shift).where(
            Shift.organization_id == organization_id,
            Shift.shift_date >= week_start,
            Shift.shift_date <= week_end,
            Shift.status == ShiftStatus.DRAFT,
        )
    )

    for proposed in result.shifts:
        db.add(
            Shift(
                organization_id=organization_id,
                coverage_requirement_id=proposed.coverage_requirement_id,
                location_id=proposed.location_id,
                job_role_id=proposed.job_role_id,
                shift_date=proposed.shift_date,
                start_time=proposed.start_time,
                end_time=proposed.end_time,
                assignee_id=proposed.assignee_id,
                status=ShiftStatus.DRAFT,
            )
        )

    db.commit()
    return result
