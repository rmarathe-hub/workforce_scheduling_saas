"""Integration tests for POST /schedules/{week_start}/generate (Day 17)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import cleanup_user
from tests.test_scheduling import WEEK_START, _setup_org_scheduling

SHIFT_DATE = "2026-06-02"


def test_generate_schedule_creates_draft_shifts(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 1,
        },
    )

    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["week_start"] == WEEK_START
    assert data["assigned_count"] == 1
    assert data["open_shift_count"] == 0
    assert data["conflict_count"] >= 0
    assert data["conflict_summary"]["errors"] == 0
    assert len(data["shifts"]) == 1
    assert data["shifts"][0]["assignee_id"] == setup["employee_user_id"]
    assert data["shifts"][0]["status"] == "DRAFT"

    cleanup_user(db, setup["employee_user_id"])


def test_generate_schedule_returns_open_shift_when_unfilled(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 2,
        },
    )

    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["assigned_count"] == 1
    assert data["open_shift_count"] == 1
    assert len(data["warnings"]) == 1
    assert data["conflict_count"] >= 1
    assert data["conflict_summary"]["warnings"] >= 1
    assert data["conflict_summary"]["errors"] == 0

    cleanup_user(db, setup["employee_user_id"])


def test_generate_schedule_is_idempotent_via_api(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 1,
        },
    )

    first = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    second = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()["shifts"]) == len(second.json()["shifts"]) == 1

    cleanup_user(db, setup["employee_user_id"])


def test_employee_cannot_generate_schedule(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 403

    cleanup_user(db, setup["employee_user_id"])
