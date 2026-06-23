"""Extended shift swap tests (Week 4 Day 23)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_employee_member, cleanup_user, register_user_with_org
from tests.test_schedule_integration import (
    SHIFT_DATE,
    _create_coverage,
    _set_employee_availability,
)
from tests.test_scheduling import WEEK_START, _setup_org_scheduling

TUESDAY = "2026-06-03"
WEDNESDAY = "2026-06-04"


@pytest.fixture
def two_employee_published_shifts(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    employee2 = add_employee_member(client, org_id, auth_headers)

    _set_employee_availability(client, org_id, setup["employee_headers"], day_of_week=1)
    _set_employee_availability(client, org_id, setup["employee_headers"], day_of_week=3)
    _set_employee_availability(client, org_id, employee2["headers"], day_of_week=1)
    _set_employee_availability(client, org_id, employee2["headers"], day_of_week=3)

    _create_coverage(client, org_id, auth_headers, setup, headcount=1)
    client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": TUESDAY,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 1,
        },
    ).raise_for_status()
    client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": WEDNESDAY,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 1,
        },
    ).raise_for_status()

    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    ).raise_for_status()
    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    ).raise_for_status()

    schedule = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    ).json()

    emp1_shifts = [
        shift
        for shift in schedule["shifts"]
        if shift["assignee_id"] == setup["employee_user_id"] and shift["status"] == "PUBLISHED"
    ]
    emp2_shifts = [
        shift
        for shift in schedule["shifts"]
        if shift["assignee_id"] == employee2["user_id"] and shift["status"] == "PUBLISHED"
    ]
    assert len(emp1_shifts) >= 1
    assert len(emp2_shifts) >= 1

    yield {
        **setup,
        "employee2": employee2,
        "emp1_shift_id": emp1_shifts[0]["id"],
        "emp2_shift_id": emp2_shifts[0]["id"],
    }

    cleanup_user(db, employee2["user_id"])
    cleanup_user(db, setup["employee_user_id"])


@pytest.fixture
def overlap_swap_setup(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    employee2 = add_employee_member(client, org_id, auth_headers)

    _set_employee_availability(client, org_id, setup["employee_headers"])
    _set_employee_availability(client, org_id, setup["employee_headers"], day_of_week=2)
    _set_employee_availability(client, org_id, employee2["headers"], day_of_week=2)

    _create_coverage(client, org_id, auth_headers, setup, headcount=1)
    client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": TUESDAY,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 2,
        },
    ).raise_for_status()

    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    ).raise_for_status()
    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    ).raise_for_status()

    schedule = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    ).json()
    published = [shift for shift in schedule["shifts"] if shift["status"] == "PUBLISHED"]

    emp1_monday = next(
        shift
        for shift in published
        if shift["assignee_id"] == setup["employee_user_id"] and shift["shift_date"] == SHIFT_DATE
    )
    emp1_tuesday = next(
        shift
        for shift in published
        if shift["assignee_id"] == setup["employee_user_id"] and shift["shift_date"] == TUESDAY
    )
    emp2_tuesday = next(
        shift
        for shift in published
        if shift["assignee_id"] == employee2["user_id"] and shift["shift_date"] == TUESDAY
    )

    yield {
        **setup,
        "employee2": employee2,
        "emp1_monday_shift_id": emp1_monday["id"],
        "emp1_tuesday_shift_id": emp1_tuesday["id"],
        "emp2_tuesday_shift_id": emp2_tuesday["id"],
    }

    cleanup_user(db, employee2["user_id"])
    cleanup_user(db, setup["employee_user_id"])


def test_employee_can_request_swap_for_own_shift(
    client: TestClient,
    org_id: str,
    two_employee_published_shifts: dict[str, str],
) -> None:
    setup = two_employee_published_shifts
    response = client.post(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=setup["employee_headers"],
        json={
            "request_type": "SWAP",
            "original_shift_id": setup["emp1_shift_id"],
            "requested_shift_id": setup["emp2_shift_id"],
            "reason": "Need Wednesday off",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["request_type"] == "SWAP"
    assert data["status"] == "PENDING"
    assert data["target_employee_id"] == setup["employee2"]["user_id"]


def test_employee_cannot_request_swap_for_someone_elses_shift(
    client: TestClient,
    org_id: str,
    two_employee_published_shifts: dict[str, str],
) -> None:
    setup = two_employee_published_shifts
    response = client.post(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=setup["employee2"]["headers"],
        json={
            "request_type": "GIVE_UP",
            "original_shift_id": setup["emp1_shift_id"],
        },
    )
    assert response.status_code == 400


def test_manager_can_approve_valid_swap(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    two_employee_published_shifts: dict[str, str],
) -> None:
    setup = two_employee_published_shifts
    create = client.post(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=setup["employee_headers"],
        json={
            "request_type": "SWAP",
            "original_shift_id": setup["emp1_shift_id"],
            "requested_shift_id": setup["emp2_shift_id"],
        },
    )
    assert create.status_code == 201
    request_id = create.json()["id"]

    approve = client.patch(
        f"/organizations/{org_id}/shift-swap-requests/{request_id}/approve",
        headers=auth_headers,
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == "APPROVED"

    schedule = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    ).json()
    shift_map = {shift["id"]: shift for shift in schedule["shifts"]}
    assert shift_map[setup["emp1_shift_id"]]["assignee_id"] == setup["employee2"]["user_id"]
    assert shift_map[setup["emp2_shift_id"]]["assignee_id"] == setup["employee_user_id"]


def test_approval_blocked_if_swap_creates_error_conflict(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    overlap_swap_setup: dict[str, str],
) -> None:
    setup = overlap_swap_setup
    create = client.post(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=setup["employee_headers"],
        json={
            "request_type": "SWAP",
            "original_shift_id": setup["emp1_monday_shift_id"],
            "requested_shift_id": setup["emp2_tuesday_shift_id"],
        },
    )
    assert create.status_code == 201

    approve = client.patch(
        f"/organizations/{org_id}/shift-swap-requests/{create.json()['id']}/approve",
        headers=auth_headers,
    )
    assert approve.status_code == 400
    assert "conflict" in approve.json()["detail"].lower()


def test_cross_org_swap_request_blocked(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    two_employee_published_shifts: dict[str, str],
) -> None:
    setup = two_employee_published_shifts
    org_b = register_user_with_org(client)

    response = client.post(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=org_b["headers"],
        json={
            "request_type": "GIVE_UP",
            "original_shift_id": setup["emp1_shift_id"],
        },
    )
    assert response.status_code == 403

    cleanup_user(db, org_b["user_id"])
