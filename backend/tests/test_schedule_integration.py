"""End-to-end integration tests for generate → validate → publish (Day 20)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import cleanup_user
from tests.test_scheduling import WEEK_START, _setup_org_scheduling

SHIFT_DATE = "2026-06-02"


def _set_employee_availability(
    client: TestClient,
    org_id: str,
    employee_headers: dict[str, str],
    *,
    day_of_week: int = 1,
    start_time: str = "09:00:00",
    end_time: str = "17:00:00",
) -> None:
    response = client.post(
        f"/organizations/{org_id}/availability",
        headers=employee_headers,
        json={
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time,
        },
    )
    assert response.status_code == 201


def _create_coverage(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    setup: dict[str, str],
    *,
    headcount: int = 1,
    start_time: str = "09:00:00",
    end_time: str = "17:00:00",
) -> None:
    response = client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "week_start": WEEK_START,
            "start_time": start_time,
            "end_time": end_time,
            "headcount": headcount,
        },
    )
    assert response.status_code == 201


def test_generate_validate_publish_flow_employee_sees_shift(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _set_employee_availability(client, org_id, setup["employee_headers"])
    _create_coverage(client, org_id, auth_headers, setup)

    generate_response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 200
    generated = generate_response.json()
    assert generated["assigned_count"] == 1
    assert generated["open_shift_count"] == 0
    assert generated["conflict_summary"]["errors"] == 0
    assert len(generated["shifts"]) == 1
    shift_id = generated["shifts"][0]["id"]

    conflicts_response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/conflicts",
        headers=auth_headers,
    )
    assert conflicts_response.status_code == 200
    assert conflicts_response.json()["summary"]["errors"] == 0

    validate_response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/validate",
        headers=auth_headers,
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True

    schedule_response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    )
    assert schedule_response.json()["schedule_status"] == "draft"

    assert (
        client.get(
            f"/organizations/{org_id}/my-shifts",
            headers=setup["employee_headers"],
            params={"week_start": WEEK_START},
        ).json()
        == []
    )

    publish_response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["published_shift_count"] == 1

    my_shifts = client.get(
        f"/organizations/{org_id}/my-shifts",
        headers=setup["employee_headers"],
        params={"week_start": WEEK_START},
    ).json()
    assert len(my_shifts) == 1
    assert my_shifts[0]["id"] == shift_id
    assert my_shifts[0]["status"] == "PUBLISHED"

    cleanup_user(db, setup["employee_user_id"])


def test_generate_creates_open_shift_and_reports_warning_conflicts(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _set_employee_availability(client, org_id, setup["employee_headers"])
    _create_coverage(client, org_id, auth_headers, setup, headcount=2)

    generate_response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 200
    generated = generate_response.json()
    assert generated["assigned_count"] == 1
    assert generated["open_shift_count"] == 1
    assert generated["conflict_summary"]["errors"] == 0
    assert generated["conflict_summary"]["warnings"] >= 1

    conflicts_response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/conflicts",
        headers=auth_headers,
    )
    conflicts = conflicts_response.json()
    assert conflicts["summary"]["errors"] == 0
    assert conflicts["summary"]["warnings"] >= 1
    assert any(conflict["type"] == "OPEN_SHIFT" for conflict in conflicts["conflicts"])
    assert all(conflict["severity"] == "WARNING" for conflict in conflicts["conflicts"])

    publish_response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["published_shift_count"] == 2

    cleanup_user(db, setup["employee_user_id"])


def test_generate_then_publish_blocked_when_overlap_introduced(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _set_employee_availability(client, org_id, setup["employee_headers"])
    _create_coverage(client, org_id, auth_headers, setup)

    generate_response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    assert generate_response.status_code == 200
    assert generate_response.json()["conflict_summary"]["errors"] == 0

    overlap_shift_id = client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "12:00:00",
            "end_time": "17:00:00",
        },
    ).json()["id"]
    client.patch(
        f"/organizations/{org_id}/shifts/{overlap_shift_id}/assign",
        headers=auth_headers,
        json={"assignee_id": setup["employee_user_id"]},
    )

    validate_response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/validate",
        headers=auth_headers,
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is False
    assert validate_response.json()["summary"]["errors"] >= 1

    publish_response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    assert publish_response.status_code == 400
    assert "blocking conflicts" in publish_response.json()["detail"]["message"]

    cleanup_user(db, setup["employee_user_id"])
