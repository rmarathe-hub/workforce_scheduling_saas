"""Smoke tests against a deployed API (Render). Skipped unless E2E_API_BASE_URL is set."""

import uuid

import httpx
import pytest

pytestmark = pytest.mark.e2e


def test_deployed_health(e2e_client: httpx.Client) -> None:
    response = e2e_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["database"] == "ok"
    assert isinstance(data["s3_configured"], bool)
    assert isinstance(data["sqs_configured"], bool)
    assert "environment" in data


def test_deployed_readiness(e2e_client: httpx.Client) -> None:
    response = e2e_client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "ok"


def test_deployed_register_login_and_me(e2e_client: httpx.Client) -> None:
    suffix = uuid.uuid4().hex[:12]
    email = f"e2e-api+{suffix}@example.com"
    password = "password123"
    org_name = f"E2E Org {suffix}"

    register = e2e_client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "E2E Tester",
            "organization_name": org_name,
        },
    )
    assert register.status_code == 201, register.text

    login = e2e_client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = e2e_client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == email

    orgs = e2e_client.get("/organizations/me", headers=headers)
    assert orgs.status_code == 200
    assert len(orgs.json()) >= 1
    assert orgs.json()[0]["organization"]["name"] == org_name


def test_deployed_manager_scheduling_flow(e2e_client: httpx.Client) -> None:
    suffix = uuid.uuid4().hex[:12]
    email = f"e2e-schedule+{suffix}@example.com"
    password = "password123"

    register = e2e_client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "E2E Manager",
            "organization_name": f"E2E Schedule Org {suffix}",
        },
    )
    assert register.status_code == 201

    login = e2e_client.post("/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    org_id = e2e_client.get("/organizations/me", headers=headers).json()[0]["organization"]["id"]

    location_id = e2e_client.post(
        f"/organizations/{org_id}/locations",
        headers=headers,
        json={"name": f"Location {suffix}"},
    ).json()["id"]

    role_id = e2e_client.post(
        f"/organizations/{org_id}/job-roles",
        headers=headers,
        json={"name": "Cashier"},
    ).json()["id"]

    employee_email = f"e2e-employee+{suffix}@example.com"
    employee = e2e_client.post(
        f"/organizations/{org_id}/members",
        headers=headers,
        json={
            "email": employee_email,
            "full_name": "E2E Employee",
            "password": password,
            "membership_role": "EMPLOYEE",
            "location_id": location_id,
            "job_role_ids": [role_id],
        },
    )
    assert employee.status_code == 201
    employee_user_id = employee.json()["user_id"]

    week_start = "2026-06-01"
    shift_date = "2026-06-02"

    coverage = e2e_client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=headers,
        json={
            "location_id": location_id,
            "job_role_id": role_id,
            "shift_date": shift_date,
            "week_start": week_start,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 1,
        },
    )
    assert coverage.status_code == 201

    shift = e2e_client.post(
        f"/organizations/{org_id}/shifts",
        headers=headers,
        json={
            "location_id": location_id,
            "job_role_id": role_id,
            "shift_date": shift_date,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "coverage_requirement_id": coverage.json()["id"],
        },
    )
    assert shift.status_code == 201
    shift_id = shift.json()["id"]

    assigned = e2e_client.patch(
        f"/organizations/{org_id}/shifts/{shift_id}/assign",
        headers=headers,
        json={"assignee_id": employee_user_id},
    )
    assert assigned.status_code == 200

    published = e2e_client.post(
        f"/organizations/{org_id}/schedules/{week_start}/publish",
        headers=headers,
    )
    assert published.status_code == 200, published.text

    schedule = e2e_client.get(
        f"/organizations/{org_id}/schedules/{week_start}",
        headers=headers,
    )
    assert schedule.status_code == 200
    assert len(schedule.json()["shifts"]) >= 1

    employee_login = e2e_client.post(
        "/auth/login",
        json={"email": employee_email, "password": password},
    )
    employee_headers = {"Authorization": f"Bearer {employee_login.json()['access_token']}"}

    my_shifts = e2e_client.get(
        f"/organizations/{org_id}/my-shifts",
        headers=employee_headers,
        params={"week_start": week_start},
    )
    assert my_shifts.status_code == 200
    assert any(s["id"] == shift_id for s in my_shifts.json())

    blocked = e2e_client.post(
        f"/organizations/{org_id}/shifts",
        headers=employee_headers,
        json={
            "location_id": location_id,
            "job_role_id": role_id,
            "shift_date": shift_date,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    )
    assert blocked.status_code == 403


def test_deployed_notifications_endpoint(e2e_client: httpx.Client) -> None:
    suffix = uuid.uuid4().hex[:12]
    email = f"e2e-notify+{suffix}@example.com"
    password = "password123"

    register = e2e_client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "E2E Notify",
            "organization_name": f"Smoke Test Org {suffix}",
        },
    )
    assert register.status_code == 201, register.text

    login = e2e_client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    org_id = e2e_client.get("/organizations/me", headers=headers).json()[0]["organization"]["id"]

    response = e2e_client.get(f"/organizations/{org_id}/notifications/me", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "items" in data
    assert "unread_count" in data
    assert isinstance(data["items"], list)
    assert data["unread_count"] >= 0
