"""Integration tests for POST /schedules/{week_start}/publish (Day 18)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import cleanup_user
from tests.test_scheduling import WEEK_START, _setup_org_scheduling

SHIFT_DATE = "2026-06-02"


def _create_assigned_shift(
    client: TestClient, org_id: str, auth_headers: dict[str, str], setup: dict[str, str]
) -> str:
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

    client.patch(
        f"/organizations/{org_id}/shifts/{shift_id}/assign",
        headers=auth_headers,
        json={"assignee_id": setup["employee_user_id"]},
    )
    return shift_id


def test_publish_week_schedule_succeeds_for_clean_schedule(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _create_assigned_shift(client, org_id, auth_headers, setup)

    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "published"
    assert data["published_shift_count"] == 1
    assert data["week_start"] == WEEK_START

    status_response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/status",
        headers=auth_headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()["schedule_status"] == "published"

    cleanup_user(db, setup["employee_user_id"])


def test_publish_blocked_when_error_conflicts_exist(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    for start, end in (("09:00:00", "13:00:00"), ("12:00:00", "17:00:00")):
        shift_id = client.post(
            f"/organizations/{org_id}/shifts",
            headers=auth_headers,
            json={
                "location_id": setup["location_id"],
                "job_role_id": setup["job_role_id"],
                "shift_date": SHIFT_DATE,
                "start_time": start,
                "end_time": end,
            },
        ).json()["id"]
        client.patch(
            f"/organizations/{org_id}/shifts/{shift_id}/assign",
            headers=auth_headers,
            json={"assignee_id": setup["employee_user_id"]},
        )

    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "blocking conflicts" in response.json()["detail"]["message"]

    cleanup_user(db, setup["employee_user_id"])


def test_publish_allows_warnings_only(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    )

    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["published_shift_count"] == 1
    assert len(response.json()["warnings"]) >= 1

    cleanup_user(db, setup["employee_user_id"])


def test_employee_sees_shift_only_after_publish(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    shift_id = _create_assigned_shift(client, org_id, auth_headers, setup)

    assert (
        client.get(
            f"/organizations/{org_id}/my-shifts",
            headers=setup["employee_headers"],
            params={"week_start": WEEK_START},
        ).json()
        == []
    )

    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )

    my_shifts = client.get(
        f"/organizations/{org_id}/my-shifts",
        headers=setup["employee_headers"],
        params={"week_start": WEEK_START},
    ).json()
    assert len(my_shifts) == 1
    assert my_shifts[0]["id"] == shift_id
    assert my_shifts[0]["status"] == "PUBLISHED"

    cleanup_user(db, setup["employee_user_id"])


def test_employee_cannot_publish_schedule(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 403

    cleanup_user(db, setup["employee_user_id"])
