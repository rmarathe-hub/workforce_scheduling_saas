"""Extended schedule API tests: status, regenerate, publish edge cases."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_employee_member, cleanup_user
from tests.test_scheduling import WEEK_START, SHIFT_DATE, _setup_org_scheduling

SHIFT_DATE_TUE = "2026-06-02"


def _create_coverage(
    client: TestClient, org_id: str, headers: dict[str, str], setup: dict[str, str]
) -> None:
    client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE_TUE,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 1,
        },
    )


def test_week_schedule_status_empty(
    client: TestClient, org_id: str, auth_headers: dict[str, str]
) -> None:
    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/status",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["schedule_status"] == "empty"


def test_employee_can_read_week_schedule_status(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    employee = add_employee_member(client, org_id, auth_headers)
    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/status",
        headers=employee["headers"],
    )
    assert response.status_code == 200
    cleanup_user(db, employee["user_id"])


def test_regenerate_preserves_published_shifts(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _create_coverage(client, org_id, auth_headers, setup)

    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    published_before = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    ).json()["shifts"]
    published_ids = {shift["id"] for shift in published_before if shift["status"] == "PUBLISHED"}
    assert published_ids

    client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "week_start": WEEK_START,
            "start_time": "12:00:00",
            "end_time": "16:00:00",
            "headcount": 1,
        },
    )
    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )

    after = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    ).json()["shifts"]
    still_published = [shift for shift in after if shift["id"] in published_ids]
    assert all(shift["status"] == "PUBLISHED" for shift in still_published)

    cleanup_user(db, setup["employee_user_id"])


def test_publish_without_draft_shifts_returns_400(
    client: TestClient, org_id: str, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "No draft shifts" in response.json()["detail"]


def test_assign_shift_with_wrong_role_employee_returns_400(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    other_role_id = client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cook"},
    ).json()["id"]

    shift_id = client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": other_role_id,
            "shift_date": SHIFT_DATE_TUE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    ).json()["id"]

    response = client.patch(
        f"/organizations/{org_id}/shifts/{shift_id}/assign",
        headers=auth_headers,
        json={"assignee_id": setup["employee_user_id"]},
    )
    assert response.status_code == 400
    assert "required job role" in response.json()["detail"]

    cleanup_user(db, setup["employee_user_id"])


def test_employee_cannot_validate_week(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    employee = add_employee_member(client, org_id, auth_headers)
    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/validate",
        headers=employee["headers"],
    )
    assert response.status_code == 403
    cleanup_user(db, employee["user_id"])
