"""Unit tests for conflict_detector.py (Day 11)."""

import uuid
from datetime import date, time

import pytest

from app.services.scheduling.conflict_detector import (
    AvailabilitySnapshot,
    ConflictDetectorInput,
    ConflictSeverity,
    ConflictType,
    CoverageRequirementSnapshot,
    EmployeeRoleSnapshot,
    ShiftSnapshot,
    TimeOffSnapshot,
    detect_conflicts,
    summarize_conflicts,
)

WEEK_START = date(2026, 6, 1)  # Monday
SHIFT_DATE = date(2026, 6, 2)  # Tuesday


def _shift(
    *,
    shift_id: uuid.UUID | None = None,
    shift_date: date = SHIFT_DATE,
    start: str = "09:00",
    end: str = "17:00",
    role_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
    coverage_requirement_id: uuid.UUID | None = None,
) -> ShiftSnapshot:
    return ShiftSnapshot(
        id=shift_id or uuid.uuid4(),
        shift_date=shift_date,
        start_time=time.fromisoformat(start),
        end_time=time.fromisoformat(end),
        job_role_id=role_id or uuid.uuid4(),
        assignee_id=assignee_id,
        coverage_requirement_id=coverage_requirement_id,
    )


def test_detects_overlapping_shifts() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift_a = _shift(assignee_id=employee_id, role_id=role_id, start="09:00", end="13:00")
    shift_b = _shift(assignee_id=employee_id, role_id=role_id, start="12:00", end="17:00")

    conflicts = detect_conflicts(
        ConflictDetectorInput(week_start=WEEK_START, shifts=[shift_a, shift_b])
    )

    overlap = [conflict for conflict in conflicts if conflict.type == ConflictType.OVERLAP]
    assert len(overlap) == 2
    assert all(conflict.severity == ConflictSeverity.ERROR for conflict in overlap)


def test_no_overlap_for_non_overlapping_shifts() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift_a = _shift(assignee_id=employee_id, role_id=role_id, start="09:00", end="12:00")
    shift_b = _shift(assignee_id=employee_id, role_id=role_id, start="12:00", end="17:00")

    conflicts = detect_conflicts(
        ConflictDetectorInput(week_start=WEEK_START, shifts=[shift_a, shift_b])
    )

    assert not any(conflict.type == ConflictType.OVERLAP for conflict in conflicts)


def test_detects_availability_conflict_when_outside_window() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift = _shift(assignee_id=employee_id, role_id=role_id, start="18:00", end="22:00")

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[shift],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
            availability=[
                AvailabilitySnapshot(
                    employee_id=employee_id,
                    day_of_week=1,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )
            ],
        )
    )

    availability = [c for c in conflicts if c.type == ConflictType.AVAILABILITY]
    assert len(availability) == 1
    assert availability[0].severity == ConflictSeverity.ERROR


def test_no_availability_conflict_when_inside_window() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift = _shift(assignee_id=employee_id, role_id=role_id, start="10:00", end="16:00")

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[shift],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
            availability=[
                AvailabilitySnapshot(
                    employee_id=employee_id,
                    day_of_week=1,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )
            ],
        )
    )

    assert not any(conflict.type == ConflictType.AVAILABILITY for conflict in conflicts)


def test_detects_availability_conflict_when_no_window_for_day() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift = _shift(assignee_id=employee_id, role_id=role_id)

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[shift],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
            availability=[
                AvailabilitySnapshot(
                    employee_id=employee_id,
                    day_of_week=0,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                )
            ],
        )
    )

    assert any(conflict.type == ConflictType.AVAILABILITY for conflict in conflicts)


def test_detects_role_mismatch() -> None:
    employee_id = uuid.uuid4()
    cashier_role = uuid.uuid4()
    cook_role = uuid.uuid4()
    shift = _shift(assignee_id=employee_id, role_id=cook_role)

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[shift],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({cashier_role}))],
        )
    )

    role_conflicts = [c for c in conflicts if c.type == ConflictType.ROLE_MISMATCH]
    assert len(role_conflicts) == 1
    assert role_conflicts[0].employee_id == employee_id


def test_no_role_mismatch_when_eligible() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift = _shift(assignee_id=employee_id, role_id=role_id)

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[shift],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
        )
    )

    assert not any(conflict.type == ConflictType.ROLE_MISMATCH for conflict in conflicts)


def test_detects_approved_time_off_conflict() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift = _shift(assignee_id=employee_id, role_id=role_id)

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[shift],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
            time_off=[
                TimeOffSnapshot(
                    employee_id=employee_id,
                    start_date=SHIFT_DATE,
                    end_date=SHIFT_DATE,
                    status="APPROVED",
                )
            ],
        )
    )

    time_off_conflicts = [c for c in conflicts if c.type == ConflictType.TIME_OFF]
    assert len(time_off_conflicts) == 1


def test_pending_time_off_does_not_conflict() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift = _shift(assignee_id=employee_id, role_id=role_id)

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[shift],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
            time_off=[
                TimeOffSnapshot(
                    employee_id=employee_id,
                    start_date=SHIFT_DATE,
                    end_date=SHIFT_DATE,
                    status="PENDING",
                )
            ],
        )
    )

    assert not any(conflict.type == ConflictType.TIME_OFF for conflict in conflicts)


def test_detects_max_hours_warning() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shifts = [
        _shift(
            assignee_id=employee_id,
            role_id=role_id,
            shift_date=date(2026, 6, day),
            start="09:00",
            end="17:00",
        )
        for day in range(1, 7)
    ]

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=shifts,
            max_weekly_hours=40,
        )
    )

    max_hour_conflicts = [c for c in conflicts if c.type == ConflictType.MAX_HOURS]
    assert len(max_hour_conflicts) == 1
    assert max_hour_conflicts[0].severity == ConflictSeverity.WARNING


def test_no_max_hours_warning_under_limit() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift = _shift(assignee_id=employee_id, role_id=role_id, start="09:00", end="17:00")

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[shift],
            max_weekly_hours=40,
        )
    )

    assert not any(conflict.type == ConflictType.MAX_HOURS for conflict in conflicts)


def test_detects_open_unassigned_shift() -> None:
    shift = _shift(assignee_id=None)

    conflicts = detect_conflicts(ConflictDetectorInput(week_start=WEEK_START, shifts=[shift]))

    open_conflicts = [c for c in conflicts if c.type == ConflictType.OPEN_SHIFT]
    assert len(open_conflicts) == 1
    assert open_conflicts[0].shift_id == shift.id


def test_detects_unfilled_coverage_requirement() -> None:
    requirement_id = uuid.uuid4()
    role_id = uuid.uuid4()

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[],
            coverage_requirements=[
                CoverageRequirementSnapshot(
                    id=requirement_id,
                    shift_date=SHIFT_DATE,
                    start_time=time(9, 0),
                    end_time=time(17, 0),
                    job_role_id=role_id,
                    headcount=2,
                )
            ],
        )
    )

    open_conflicts = [
        c for c in conflicts if c.type == ConflictType.OPEN_SHIFT and c.coverage_requirement_id
    ]
    assert len(open_conflicts) == 2


def test_summarize_conflicts_counts_errors_and_warnings() -> None:
    employee_id = uuid.uuid4()
    role_id = uuid.uuid4()
    shift = _shift(assignee_id=employee_id, role_id=role_id)
    unassigned = _shift(assignee_id=None)

    conflicts = detect_conflicts(
        ConflictDetectorInput(
            week_start=WEEK_START,
            shifts=[shift, unassigned],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({uuid.uuid4()}))],
        )
    )

    summary = summarize_conflicts(conflicts)
    assert summary["total"] == len(conflicts)
    assert summary["errors"] >= 1
    assert summary["warnings"] >= 1
