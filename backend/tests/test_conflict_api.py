"""Integration tests for conflict API endpoints (Day 12)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import cleanup_user
from tests.test_scheduling import WEEK_START, _setup_org_scheduling

SHIFT_DATE = "2026-06-02"


def test_get_conflicts_detects_overlap(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    for start, end in (("09:00:00", "13:00:00"), ("12:00:00", "17:00:00")):
        client.post(
            f"/organizations/{org_id}/shifts",
            headers=auth_headers,
            json={
                "location_id": setup["location_id"],
                "job_role_id": setup["job_role_id"],
                "shift_date": SHIFT_DATE,
                "start_time": start,
                "end_time": end,
                "assignee_id": setup["employee_user_id"],
            },
        )

    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/conflicts",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["errors"] >= 1
    assert any(conflict["type"] == "OVERLAP" for conflict in data["conflicts"])

    cleanup_user(db, setup["employee_user_id"])


def test_get_conflicts_detects_availability_violation(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    client.post(
        f"/organizations/{org_id}/availability",
        headers=setup["employee_headers"],
        json={"day_of_week": 1, "start_time": "09:00:00", "end_time": "12:00:00"},
    )

    client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "18:00:00",
            "end_time": "22:00:00",
            "assignee_id": setup["employee_user_id"],
        },
    )

    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/conflicts",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert any(conflict["type"] == "AVAILABILITY" for conflict in response.json()["conflicts"])

    cleanup_user(db, setup["employee_user_id"])


def test_get_conflicts_detects_approved_time_off(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    request_id = client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=setup["employee_headers"],
        json={"start_date": SHIFT_DATE, "end_date": SHIFT_DATE, "reason": "Away"},
    ).json()["id"]

    client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=auth_headers,
    )

    client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "assignee_id": setup["employee_user_id"],
        },
    )

    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/conflicts",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert any(conflict["type"] == "TIME_OFF" for conflict in response.json()["conflicts"])

    cleanup_user(db, setup["employee_user_id"])


def test_validate_week_returns_invalid_when_errors_exist(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    for start, end in (("09:00:00", "13:00:00"), ("12:00:00", "17:00:00")):
        client.post(
            f"/organizations/{org_id}/shifts",
            headers=auth_headers,
            json={
                "location_id": setup["location_id"],
                "job_role_id": setup["job_role_id"],
                "shift_date": SHIFT_DATE,
                "start_time": start,
                "end_time": end,
                "assignee_id": setup["employee_user_id"],
            },
        )

    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/validate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False
    assert data["summary"]["errors"] >= 1

    cleanup_user(db, setup["employee_user_id"])


def test_validate_week_returns_valid_for_clean_schedule(
    client: TestClient, org_id: str, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/validate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["summary"]["total"] == 0


def test_validate_shift_returns_conflicts_for_that_shift(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    shift_id = client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    ).json()["id"]

    response = client.post(
        f"/organizations/{org_id}/shifts/{shift_id}/validate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["shift_id"] == shift_id
    assert data["valid"] is True
    assert len(data["conflicts"]) >= 1
    assert all(conflict["type"] == "OPEN_SHIFT" for conflict in data["conflicts"])

    cleanup_user(db, setup["employee_user_id"])


def test_employee_cannot_access_conflict_endpoints(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    get_response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/conflicts",
        headers=setup["employee_headers"],
    )
    assert get_response.status_code == 403

    post_response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/validate",
        headers=setup["employee_headers"],
    )
    assert post_response.status_code == 403

    cleanup_user(db, setup["employee_user_id"])
