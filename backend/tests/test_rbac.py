"""Day 8 — RBAC hardening tests for existing Week 1 endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient

from tests.helpers import add_employee_member, cleanup_user, login_headers

WEEK_START = "2026-06-01"
SHIFT_DATE = "2026-06-02"


@pytest.fixture
def employee_in_org(
    client: TestClient, db, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    employee = add_employee_member(client, org_id, auth_headers)
    yield employee
    cleanup_user(db, employee["user_id"])


def test_unauthenticated_schedule_request_returns_401(client: TestClient, org_id: str) -> None:
    response = client.get(f"/organizations/{org_id}/schedules/{WEEK_START}")
    assert response.status_code == 401


def test_invalid_token_schedule_request_returns_401(client: TestClient, org_id: str) -> None:
    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert response.status_code == 401


def test_unauthenticated_create_shift_returns_401(client: TestClient, org_id: str) -> None:
    response = client.post(
        f"/organizations/{org_id}/shifts",
        json={
            "location_id": str(uuid.uuid4()),
            "job_role_id": str(uuid.uuid4()),
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    )
    assert response.status_code == 401


def test_employee_cannot_create_coverage_requirement(
    client: TestClient, org_id: str, auth_headers: dict[str, str], employee_in_org: dict[str, str]
) -> None:
    location_id = client.post(
        f"/organizations/{org_id}/locations",
        headers=auth_headers,
        json={"name": "Main"},
    ).json()["id"]
    role_id = client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cashier"},
    ).json()["id"]

    response = client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=employee_in_org["headers"],
        json={
            "location_id": location_id,
            "job_role_id": role_id,
            "shift_date": SHIFT_DATE,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 1,
        },
    )
    assert response.status_code == 403


def test_employee_cannot_create_location(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    response = client.post(
        f"/organizations/{org_id}/locations",
        headers=employee_in_org["headers"],
        json={"name": "Blocked"},
    )
    assert response.status_code == 403


def test_employee_cannot_create_job_role(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    response = client.post(
        f"/organizations/{org_id}/job-roles",
        headers=employee_in_org["headers"],
        json={"name": "Blocked"},
    )
    assert response.status_code == 403


def test_employee_cannot_assign_shift(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    location_id = client.post(
        f"/organizations/{org_id}/locations",
        headers=auth_headers,
        json={"name": "Main"},
    ).json()["id"]
    role_id = client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cashier"},
    ).json()["id"]
    shift_id = client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": location_id,
            "job_role_id": role_id,
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    ).json()["id"]

    response = client.patch(
        f"/organizations/{org_id}/shifts/{shift_id}/assign",
        headers=employee_in_org["headers"],
        json={"assignee_id": employee_in_org["user_id"]},
    )
    assert response.status_code == 403


def test_employee_can_read_org_resources(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    client.post(
        f"/organizations/{org_id}/locations",
        headers=auth_headers,
        json={"name": "Main"},
    )
    client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cashier"},
    )

    assert client.get(f"/organizations/{org_id}/locations", headers=employee_in_org["headers"]).status_code == 200
    assert client.get(f"/organizations/{org_id}/job-roles", headers=employee_in_org["headers"]).status_code == 200
    assert client.get(f"/organizations/{org_id}/employees", headers=employee_in_org["headers"]).status_code == 200
    assert (
        client.get(f"/organizations/{org_id}/schedules/{WEEK_START}", headers=employee_in_org["headers"]).status_code
        == 200
    )


def test_non_member_cannot_access_org_schedule(
    client: TestClient, db, org_id: str, auth_headers: dict[str, str]
) -> None:
    other_email = f"other-{uuid.uuid4()}@example.com"
    register = client.post(
        "/auth/register",
        json={
            "email": other_email,
            "password": "password123",
            "full_name": "Other User",
            "organization_name": f"Other Org {uuid.uuid4()}",
        },
    )
    other_user_id = register.json()["id"]
    other_headers = login_headers(client, other_email, "password123")

    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=other_headers,
    )
    assert response.status_code == 403

    cleanup_user(db, other_user_id)


def test_non_member_cannot_create_location_in_foreign_org(
    client: TestClient, db, org_id: str
) -> None:
    other_email = f"other-{uuid.uuid4()}@example.com"
    register = client.post(
        "/auth/register",
        json={
            "email": other_email,
            "password": "password123",
            "full_name": "Other User",
            "organization_name": f"Other Org {uuid.uuid4()}",
        },
    )
    other_user_id = register.json()["id"]
    other_headers = login_headers(client, other_email, "password123")

    response = client.post(
        f"/organizations/{org_id}/locations",
        headers=other_headers,
        json={"name": "Intruder Location"},
    )
    assert response.status_code == 403

    cleanup_user(db, other_user_id)
