import uuid
from datetime import date

from fastapi.testclient import TestClient

from tests.helpers import cleanup_user

WEEK_START = "2026-06-01"
SHIFT_DATE = "2026-06-02"


def _setup_org_scheduling(
    client: TestClient, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    location_id = client.post(
        f"/organizations/{org_id}/locations",
        headers=auth_headers,
        json={"name": "Main"},
    ).json()["id"]

    job_role_id = client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cashier"},
    ).json()["id"]

    employee_email = f"employee-{uuid.uuid4()}@example.com"
    employee_response = client.post(
        f"/organizations/{org_id}/members",
        headers=auth_headers,
        json={
            "email": employee_email,
            "full_name": "Shift Employee",
            "password": "password123",
            "membership_role": "EMPLOYEE",
            "location_id": location_id,
            "job_role_ids": [job_role_id],
        },
    )
    employee_user_id = employee_response.json()["user_id"]

    employee_login = client.post(
        "/auth/login",
        json={"email": employee_email, "password": "password123"},
    )
    employee_headers = {
        "Authorization": f"Bearer {employee_login.json()['access_token']}"
    }

    return {
        "location_id": location_id,
        "job_role_id": job_role_id,
        "employee_user_id": employee_user_id,
        "employee_email": employee_email,
        "employee_headers": employee_headers,
    }


def test_create_coverage_requirement(
    client: TestClient, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    response = client.post(
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

    assert response.status_code == 201
    data = response.json()
    assert data["headcount"] == 2
    assert data["week_start"] == WEEK_START


def test_manager_creates_shift_and_assigns_employee(
    client: TestClient, db, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    requirement_id = client.post(
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
    ).json()["id"]

    shift_response = client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "coverage_requirement_id": requirement_id,
        },
    )
    assert shift_response.status_code == 201
    shift_id = shift_response.json()["id"]
    assert shift_response.json()["assignee_id"] is None

    assign_response = client.patch(
        f"/organizations/{org_id}/shifts/{shift_id}/assign",
        headers=auth_headers,
        json={"assignee_id": setup["employee_user_id"]},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["assignee_id"] == setup["employee_user_id"]

    cleanup_user(db, setup["employee_user_id"])


def test_week_schedule_returns_requirements_and_shifts(
    client: TestClient, db, org_id: str, auth_headers: dict[str, str]
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

    schedule_response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    )
    assert schedule_response.status_code == 200
    schedule = schedule_response.json()
    assert schedule["week_start"] == WEEK_START
    assert len(schedule["coverage_requirements"]) == 1
    assert len(schedule["shifts"]) == 1

    cleanup_user(db, setup["employee_user_id"])


def test_employee_sees_assigned_shifts_in_my_shifts(
    client: TestClient, db, org_id: str, auth_headers: dict[str, str]
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

    client.patch(
        f"/organizations/{org_id}/shifts/{shift_id}/assign",
        headers=auth_headers,
        json={"assignee_id": setup["employee_user_id"]},
    )

    my_shifts_response = client.get(
        f"/organizations/{org_id}/my-shifts",
        headers=setup["employee_headers"],
        params={"week_start": WEEK_START},
    )
    assert my_shifts_response.status_code == 200
    my_shifts = my_shifts_response.json()
    assert len(my_shifts) == 1
    assert my_shifts[0]["id"] == shift_id

    cleanup_user(db, setup["employee_user_id"])


def test_employee_cannot_create_shift(
    client: TestClient, db, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    response = client.post(
        f"/organizations/{org_id}/shifts",
        headers=setup["employee_headers"],
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    )
    assert response.status_code == 403

    cleanup_user(db, setup["employee_user_id"])
