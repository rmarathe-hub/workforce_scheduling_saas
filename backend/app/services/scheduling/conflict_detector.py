"""
Scheduling conflict detector (Week 2 Day 11).

Severity defaults (drives publish-blocking in Week 3):
- OVERLAP: ERROR
- AVAILABILITY: ERROR
- ROLE_MISMATCH: ERROR
- TIME_OFF (approved): ERROR
- MAX_HOURS: WARNING
- OPEN_SHIFT: WARNING
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from uuid import UUID
from zoneinfo import ZoneInfo

DEFAULT_MAX_WEEKLY_HOURS = 40


class ConflictType(str, Enum):
    OVERLAP = "OVERLAP"
    AVAILABILITY = "AVAILABILITY"
    ROLE_MISMATCH = "ROLE_MISMATCH"
    TIME_OFF = "TIME_OFF"
    MAX_HOURS = "MAX_HOURS"
    OPEN_SHIFT = "OPEN_SHIFT"


class ConflictSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


CONFLICT_SEVERITY: dict[ConflictType, ConflictSeverity] = {
    ConflictType.OVERLAP: ConflictSeverity.ERROR,
    ConflictType.AVAILABILITY: ConflictSeverity.ERROR,
    ConflictType.ROLE_MISMATCH: ConflictSeverity.ERROR,
    ConflictType.TIME_OFF: ConflictSeverity.ERROR,
    ConflictType.MAX_HOURS: ConflictSeverity.WARNING,
    ConflictType.OPEN_SHIFT: ConflictSeverity.WARNING,
}


@dataclass(frozen=True)
class Conflict:
    type: ConflictType
    severity: ConflictSeverity
    message: str
    shift_id: UUID | None = None
    employee_id: UUID | None = None
    coverage_requirement_id: UUID | None = None


@dataclass(frozen=True)
class ShiftSnapshot:
    id: UUID
    shift_date: date
    start_time: time
    end_time: time
    job_role_id: UUID
    assignee_id: UUID | None = None
    coverage_requirement_id: UUID | None = None


@dataclass(frozen=True)
class AvailabilitySnapshot:
    employee_id: UUID
    day_of_week: int
    start_time: time
    end_time: time


@dataclass(frozen=True)
class TimeOffSnapshot:
    employee_id: UUID
    start_date: date
    end_date: date
    status: str


@dataclass(frozen=True)
class EmployeeRoleSnapshot:
    employee_id: UUID
    job_role_ids: frozenset[UUID] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CoverageRequirementSnapshot:
    id: UUID
    shift_date: date
    start_time: time
    end_time: time
    job_role_id: UUID
    headcount: int


@dataclass(frozen=True)
class ConflictDetectorInput:
    week_start: date
    shifts: list[ShiftSnapshot]
    availability: list[AvailabilitySnapshot] = field(default_factory=list)
    time_off: list[TimeOffSnapshot] = field(default_factory=list)
    employee_roles: list[EmployeeRoleSnapshot] = field(default_factory=list)
    coverage_requirements: list[CoverageRequirementSnapshot] = field(default_factory=list)
    max_weekly_hours: float = DEFAULT_MAX_WEEKLY_HOURS
    org_timezone: str = "America/New_York"


def _week_end(week_start: date) -> date:
    return week_start + timedelta(days=6)


def _shift_weekday(shift_date: date, org_timezone: str) -> int:
    """Return 0=Monday .. 6=Sunday using org timezone for the calendar date."""
    tz = ZoneInfo(org_timezone)
    localized = datetime.combine(shift_date, time(12, 0), tzinfo=tz)
    return localized.weekday()


def _duration_hours(start_time: time, end_time: time) -> float:
    start_minutes = start_time.hour * 60 + start_time.minute
    end_minutes = end_time.hour * 60 + end_time.minute
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60
    return (end_minutes - start_minutes) / 60


def _times_overlap(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    a_start = start_a.hour * 60 + start_a.minute
    a_end = end_a.hour * 60 + end_a.minute
    b_start = start_b.hour * 60 + start_b.minute
    b_end = end_b.hour * 60 + end_b.minute
    if a_end <= a_start:
        a_end += 24 * 60
    if b_end <= b_start:
        b_end += 24 * 60
    return a_start < b_end and b_start < a_end


def _shift_within_availability(shift: ShiftSnapshot, windows: list[AvailabilitySnapshot]) -> bool:
    if not windows:
        return False
    return any(
        window.start_time <= shift.start_time and shift.end_time <= window.end_time
        for window in windows
    )


def _conflict(
    conflict_type: ConflictType,
    message: str,
    *,
    shift_id: UUID | None = None,
    employee_id: UUID | None = None,
    coverage_requirement_id: UUID | None = None,
) -> Conflict:
    return Conflict(
        type=conflict_type,
        severity=CONFLICT_SEVERITY[conflict_type],
        message=message,
        shift_id=shift_id,
        employee_id=employee_id,
        coverage_requirement_id=coverage_requirement_id,
    )


def detect_conflicts(detector_input: ConflictDetectorInput) -> list[Conflict]:
    week_end = _week_end(detector_input.week_start)
    conflicts: list[Conflict] = []

    week_shifts = [
        shift
        for shift in detector_input.shifts
        if detector_input.week_start <= shift.shift_date <= week_end
    ]

    availability_by_employee: dict[UUID, list[AvailabilitySnapshot]] = {}
    for window in detector_input.availability:
        availability_by_employee.setdefault(window.employee_id, []).append(window)

    roles_by_employee = {entry.employee_id: entry.job_role_ids for entry in detector_input.employee_roles}

    approved_time_off = [
        request
        for request in detector_input.time_off
        if request.status == "APPROVED"
    ]

    # Open / unassigned shifts
    for shift in week_shifts:
        if shift.assignee_id is None:
            conflicts.append(
                _conflict(
                    ConflictType.OPEN_SHIFT,
                    "Shift has no assignee",
                    shift_id=shift.id,
                )
            )

    # Coverage requirements not fully staffed
    for requirement in detector_input.coverage_requirements:
        if not (detector_input.week_start <= requirement.shift_date <= week_end):
            continue
        assigned_count = sum(
            1
            for shift in week_shifts
            if shift.coverage_requirement_id == requirement.id and shift.assignee_id is not None
        )
        unfilled = requirement.headcount - assigned_count
        for _ in range(unfilled):
            conflicts.append(
                _conflict(
                    ConflictType.OPEN_SHIFT,
                    "Coverage requirement is not fully staffed",
                    coverage_requirement_id=requirement.id,
                )
            )

    assigned_shifts = [shift for shift in week_shifts if shift.assignee_id is not None]

    # Per-shift assignment rules
    for shift in assigned_shifts:
        employee_id = shift.assignee_id
        assert employee_id is not None

        role_ids = roles_by_employee.get(employee_id, frozenset())
        if shift.job_role_id not in role_ids:
            conflicts.append(
                _conflict(
                    ConflictType.ROLE_MISMATCH,
                    "Employee is not eligible for this job role",
                    shift_id=shift.id,
                    employee_id=employee_id,
                )
            )

        employee_windows = availability_by_employee.get(employee_id, [])
        if employee_windows:
            day = _shift_weekday(shift.shift_date, detector_input.org_timezone)
            day_windows = [window for window in employee_windows if window.day_of_week == day]
            if not _shift_within_availability(shift, day_windows):
                conflicts.append(
                    _conflict(
                        ConflictType.AVAILABILITY,
                        "Shift is outside employee availability",
                        shift_id=shift.id,
                        employee_id=employee_id,
                    )
                )

        for request in approved_time_off:
            if request.employee_id != employee_id:
                continue
            if request.start_date <= shift.shift_date <= request.end_date:
                conflicts.append(
                    _conflict(
                        ConflictType.TIME_OFF,
                        "Employee has approved time off on this date",
                        shift_id=shift.id,
                        employee_id=employee_id,
                    )
                )
                break

    # Overlapping shifts per employee
    shifts_by_employee: dict[UUID, list[ShiftSnapshot]] = {}
    for shift in assigned_shifts:
        assert shift.assignee_id is not None
        shifts_by_employee.setdefault(shift.assignee_id, []).append(shift)

    for employee_id, employee_shifts in shifts_by_employee.items():
        for index, left in enumerate(employee_shifts):
            for right in employee_shifts[index + 1 :]:
                if left.shift_date != right.shift_date:
                    continue
                if _times_overlap(left.start_time, left.end_time, right.start_time, right.end_time):
                    conflicts.append(
                        _conflict(
                            ConflictType.OVERLAP,
                            "Employee has overlapping shifts",
                            shift_id=left.id,
                            employee_id=employee_id,
                        )
                    )
                    conflicts.append(
                        _conflict(
                            ConflictType.OVERLAP,
                            "Employee has overlapping shifts",
                            shift_id=right.id,
                            employee_id=employee_id,
                        )
                    )

    # Weekly hour limits
    hours_by_employee: dict[UUID, float] = {}
    for shift in assigned_shifts:
        assert shift.assignee_id is not None
        hours_by_employee[shift.assignee_id] = hours_by_employee.get(shift.assignee_id, 0.0) + (
            _duration_hours(shift.start_time, shift.end_time)
        )

    for employee_id, total_hours in hours_by_employee.items():
        if total_hours > detector_input.max_weekly_hours:
            conflicts.append(
                _conflict(
                    ConflictType.MAX_HOURS,
                    f"Employee scheduled for {total_hours:.1f} hours (max {detector_input.max_weekly_hours:.0f})",
                    employee_id=employee_id,
                )
            )

    return conflicts


def summarize_conflicts(conflicts: list[Conflict]) -> dict[str, int]:
    errors = sum(1 for conflict in conflicts if conflict.severity == ConflictSeverity.ERROR)
    warnings = sum(1 for conflict in conflicts if conflict.severity == ConflictSeverity.WARNING)
    info = sum(1 for conflict in conflicts if conflict.severity == ConflictSeverity.INFO)
    return {"total": len(conflicts), "errors": errors, "warnings": warnings, "info": info}
