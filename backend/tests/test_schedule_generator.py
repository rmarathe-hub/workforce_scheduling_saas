"""Unit and integration tests for schedule_generator.py (Week 3 Day 16)."""

import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.shift import Shift
from app.services.scheduling.conflict_detector import (
    AvailabilitySnapshot,
    EmployeeRoleSnapshot,
    ShiftSnapshot,
    TimeOffSnapshot,
)
from app.services.scheduling.schedule_generator import (
    GeneratorCoverageRequirement,
    ScheduleGeneratorInput,
    generate_schedule,
    generate_weekly_schedule,
)
from tests.test_scheduling import WEEK_START, _setup_org_scheduling

WEEK_START_DATE = date(2026, 6, 1)
SHIFT_DATE = date(2026, 6, 2)  # Tuesday, day_of_week=1


def _requirement(
    *,
    requirement_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    job_role_id: uuid.UUID | None = None,
    shift_date: date = SHIFT_DATE,
    start: str = "09:00",
    end: str = "17:00",
    headcount: int = 1,
) -> GeneratorCoverageRequirement:
    return GeneratorCoverageRequirement(
        id=requirement_id or uuid.uuid4(),
        location_id=location_id or uuid.uuid4(),
        job_role_id=job_role_id or uuid.uuid4(),
        shift_date=shift_date,
        start_time=time.fromisoformat(start),
        end_time=time.fromisoformat(end),
        headcount=headcount,
    )


def _shift(
    *,
    shift_id: uuid.UUID | None = None,
    shift_date: date = SHIFT_DATE,
    start: str = "09:00",
    end: str = "17:00",
    role_id: uuid.UUID | None = None,
    assignee_id: uuid.UUID | None = None,
) -> ShiftSnapshot:
    return ShiftSnapshot(
        id=shift_id or uuid.uuid4(),
        shift_date=shift_date,
        start_time=time.fromisoformat(start),
        end_time=time.fromisoformat(end),
        job_role_id=role_id or uuid.uuid4(),
        assignee_id=assignee_id,
    )


def test_assigns_eligible_employee() -> None:
    role_id = uuid.uuid4()
    employee_id = uuid.uuid4()
    requirement = _requirement(job_role_id=role_id)

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
        )
    )

    assert result.assigned_count == 1
    assert result.open_shift_count == 0
    assert result.shifts[0].assignee_id == employee_id


def test_skips_employee_without_required_role() -> None:
    required_role = uuid.uuid4()
    other_role = uuid.uuid4()
    employee_id = uuid.uuid4()
    requirement = _requirement(job_role_id=required_role)

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({other_role}))],
        )
    )

    assert result.assigned_count == 0
    assert result.open_shift_count == 1
    assert result.shifts[0].assignee_id is None


def test_skips_unavailable_employee() -> None:
    role_id = uuid.uuid4()
    employee_id = uuid.uuid4()
    requirement = _requirement(job_role_id=role_id, start="18:00", end="22:00")

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
            availability=[
                AvailabilitySnapshot(
                    employee_id=employee_id,
                    day_of_week=1,
                    start_time=time(9, 0),
                    end_time=time(12, 0),
                )
            ],
        )
    )

    assert result.open_shift_count == 1
    assert result.shifts[0].assignee_id is None


def test_skips_employee_with_approved_time_off() -> None:
    role_id = uuid.uuid4()
    employee_id = uuid.uuid4()
    requirement = _requirement(job_role_id=role_id)

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
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

    assert result.open_shift_count == 1
    assert result.shifts[0].assignee_id is None


def test_skips_employee_with_overlapping_shift() -> None:
    role_id = uuid.uuid4()
    employee_id = uuid.uuid4()
    requirement = _requirement(job_role_id=role_id, start="12:00", end="17:00")
    existing = _shift(
        assignee_id=employee_id,
        role_id=role_id,
        start="09:00",
        end="13:00",
    )

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
            existing_shifts=[existing],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
        )
    )

    assert result.open_shift_count == 1
    assert result.shifts[0].assignee_id is None


def test_skips_employee_over_max_weekly_hours() -> None:
    role_id = uuid.uuid4()
    employee_id = uuid.uuid4()
    requirement = _requirement(job_role_id=role_id, start="09:00", end="17:00")
    existing = _shift(assignee_id=employee_id, role_id=role_id, start="09:00", end="17:00")

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
            existing_shifts=[existing],
            employee_roles=[EmployeeRoleSnapshot(employee_id, frozenset({role_id}))],
            max_weekly_hours=8,
        )
    )

    assert result.open_shift_count == 1
    assert result.shifts[0].assignee_id is None


def test_chooses_employee_with_fewer_weekly_hours() -> None:
    role_id = uuid.uuid4()
    busy_employee = uuid.uuid4()
    free_employee = uuid.uuid4()
    requirement = _requirement(job_role_id=role_id, start="09:00", end="13:00")
    existing = _shift(
        assignee_id=busy_employee,
        role_id=role_id,
        shift_date=date(2026, 6, 3),
        start="09:00",
        end="17:00",
    )

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
            existing_shifts=[existing],
            employee_roles=[
                EmployeeRoleSnapshot(busy_employee, frozenset({role_id})),
                EmployeeRoleSnapshot(free_employee, frozenset({role_id})),
            ],
        )
    )

    assert result.assigned_count == 1
    assert result.shifts[0].assignee_id == free_employee


def test_creates_open_shift_when_nobody_qualifies() -> None:
    requirement = _requirement()

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
            employee_roles=[],
        )
    )

    assert result.assigned_count == 0
    assert result.open_shift_count == 1
    assert len(result.warnings) == 1
    assert result.shifts[0].assignee_id is None


def test_generates_multiple_shifts_when_headcount_gt_one() -> None:
    role_id = uuid.uuid4()
    employee_a = uuid.uuid4()
    employee_b = uuid.uuid4()
    requirement = _requirement(job_role_id=role_id, headcount=2)

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
            employee_roles=[
                EmployeeRoleSnapshot(employee_a, frozenset({role_id})),
                EmployeeRoleSnapshot(employee_b, frozenset({role_id})),
            ],
        )
    )

    assert len(result.shifts) == 2
    assert result.assigned_count == 2
    assert result.open_shift_count == 0
    assignees = {shift.assignee_id for shift in result.shifts}
    assert assignees == {employee_a, employee_b}


def test_pending_time_off_does_not_block_assignment() -> None:
    role_id = uuid.uuid4()
    employee_id = uuid.uuid4()
    requirement = _requirement(job_role_id=role_id)

    result = generate_schedule(
        ScheduleGeneratorInput(
            week_start=WEEK_START_DATE,
            coverage_requirements=[requirement],
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

    assert result.assigned_count == 1
    assert result.shifts[0].assignee_id == employee_id


def test_generate_weekly_schedule_does_not_duplicate_on_rerun(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE.isoformat(),
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 2,
        },
    )

    organization_uuid = uuid.UUID(org_id)
    week_start = WEEK_START_DATE

    first = generate_weekly_schedule(db, organization_uuid, week_start)
    second = generate_weekly_schedule(db, organization_uuid, week_start)

    shift_count = db.scalar(
        select(func.count())
        .select_from(Shift)
        .where(
            Shift.organization_id == organization_uuid,
            Shift.shift_date >= week_start,
            Shift.shift_date <= date(2026, 6, 7),
        )
    )

    assert first.assigned_count == 1
    assert first.open_shift_count == 1
    assert second.assigned_count == 1
    assert second.open_shift_count == 1
    assert shift_count == 2
