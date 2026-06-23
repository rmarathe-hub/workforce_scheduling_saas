"""Notification API tests (Week 5 Day 29)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import cleanup_user
from tests.test_schedule_integration import (
    SHIFT_DATE,
    WEEK_START,
    _create_coverage,
    _set_employee_availability,
)
from tests.test_scheduling import _setup_org_scheduling


def test_schedule_publish_creates_employee_notification(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _set_employee_availability(client, org_id, setup["employee_headers"])
    _create_coverage(client, org_id, auth_headers, setup, headcount=1)

    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )

    response = client.get(
        f"/organizations/{org_id}/notifications/me",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["unread_count"] >= 1
    assert any(item["type"] == "SCHEDULE_PUBLISHED" for item in data["items"])

    cleanup_user(db, setup["employee_user_id"])


def test_time_off_approval_notifies_employee(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    request = client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=setup["employee_headers"],
        json={"start_date": SHIFT_DATE, "end_date": SHIFT_DATE, "reason": "Trip"},
    ).json()

    client.patch(
        f"/organizations/{org_id}/time-off-requests/{request['id']}/approve",
        headers=auth_headers,
    )

    response = client.get(
        f"/organizations/{org_id}/notifications/me",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 200
    assert any(item["type"] == "TIME_OFF_APPROVED" for item in response.json()["items"])

    cleanup_user(db, setup["employee_user_id"])


def test_shift_swap_request_notifies_manager(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _set_employee_availability(client, org_id, setup["employee_headers"])
    _create_coverage(client, org_id, auth_headers, setup, headcount=1)
    client.post(f"/organizations/{org_id}/schedules/{WEEK_START}/generate", headers=auth_headers)
    client.post(f"/organizations/{org_id}/schedules/{WEEK_START}/publish", headers=auth_headers)

    shift_id = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    ).json()["shifts"][0]["id"]

    client.post(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=setup["employee_headers"],
        json={"request_type": "GIVE_UP", "original_shift_id": shift_id},
    )

    response = client.get(
        f"/organizations/{org_id}/notifications/me",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert any(item["type"] == "SHIFT_SWAP_REQUESTED" for item in response.json()["items"])

    cleanup_user(db, setup["employee_user_id"])


def test_mark_notification_read(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=setup["employee_headers"],
        json={"start_date": SHIFT_DATE, "end_date": SHIFT_DATE, "reason": "Trip"},
    )
    request_id = client.get(
        f"/organizations/{org_id}/time-off-requests",
        headers=auth_headers,
    ).json()[0]["id"]
    client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=auth_headers,
    )

    listed = client.get(
        f"/organizations/{org_id}/notifications/me",
        headers=setup["employee_headers"],
    ).json()
    notification_id = listed["items"][0]["id"]
    assert listed["unread_count"] >= 1

    read = client.post(
        f"/organizations/{org_id}/notifications/{notification_id}/read",
        headers=setup["employee_headers"],
    )
    assert read.status_code == 200
    assert read.json()["status"] == "READ"

    after = client.get(
        f"/organizations/{org_id}/notifications/me",
        headers=setup["employee_headers"],
    ).json()
    assert after["unread_count"] == listed["unread_count"] - 1

    cleanup_user(db, setup["employee_user_id"])


def test_mark_all_notifications_read(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=setup["employee_headers"],
        json={"start_date": SHIFT_DATE, "end_date": SHIFT_DATE, "reason": "Trip"},
    )
    request_id = client.get(
        f"/organizations/{org_id}/time-off-requests",
        headers=auth_headers,
    ).json()[0]["id"]
    client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=auth_headers,
    )

    response = client.post(
        f"/organizations/{org_id}/notifications/read-all",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 204

    listed = client.get(
        f"/organizations/{org_id}/notifications/me",
        headers=setup["employee_headers"],
    ).json()
    assert listed["unread_count"] == 0

    cleanup_user(db, setup["employee_user_id"])
