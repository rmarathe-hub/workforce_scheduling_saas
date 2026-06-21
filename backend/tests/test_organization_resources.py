import uuid

from fastapi.testclient import TestClient

from tests.helpers import cleanup_user


def test_owner_creates_location(
    client: TestClient, org_id: str, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"/organizations/{org_id}/locations",
        headers=auth_headers,
        json={"name": "Main", "address": "123 Main St"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Main"
    assert data["organization_id"] == org_id


def test_owner_creates_job_roles(
    client: TestClient, org_id: str, auth_headers: dict[str, str]
) -> None:
    for role_name in ("Cashier", "Cook", "Server"):
        response = client.post(
            f"/organizations/{org_id}/job-roles",
            headers=auth_headers,
            json={"name": role_name},
        )
        assert response.status_code == 201

    list_response = client.get(f"/organizations/{org_id}/job-roles", headers=auth_headers)
    assert len(list_response.json()) == 3


def test_owner_adds_manager_and_employee_with_job_roles(
    client: TestClient, db, org_id: str, auth_headers: dict[str, str]
) -> None:
    location_id = client.post(
        f"/organizations/{org_id}/locations",
        headers=auth_headers,
        json={"name": "Main"},
    ).json()["id"]

    cashier_role_id = client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cashier"},
    ).json()["id"]

    manager_email = f"manager-{uuid.uuid4()}@example.com"
    manager_response = client.post(
        f"/organizations/{org_id}/members",
        headers=auth_headers,
        json={
            "email": manager_email,
            "full_name": "Manager Maya",
            "password": "password123",
            "membership_role": "MANAGER",
            "location_id": location_id,
        },
    )
    assert manager_response.status_code == 201
    manager_user_id = manager_response.json()["user_id"]

    employee_email = f"employee-{uuid.uuid4()}@example.com"
    employee_response = client.post(
        f"/organizations/{org_id}/members",
        headers=auth_headers,
        json={
            "email": employee_email,
            "full_name": "Employee Ali",
            "password": "password123",
            "membership_role": "EMPLOYEE",
            "location_id": location_id,
            "job_role_ids": [cashier_role_id],
            "job_title": "Part-time cashier",
        },
    )
    assert employee_response.status_code == 201
    employee_data = employee_response.json()
    assert employee_data["membership_role"] == "EMPLOYEE"
    assert len(employee_data["job_roles"]) == 1
    assert employee_data["job_roles"][0]["name"] == "Cashier"
    employee_user_id = employee_data["user_id"]

    employees_response = client.get(f"/organizations/{org_id}/employees", headers=auth_headers)
    assert employees_response.status_code == 200
    assert len(employees_response.json()) == 2

    cleanup_user(db, manager_user_id)
    cleanup_user(db, employee_user_id)


def test_employee_cannot_add_members(
    client: TestClient, db, org_id: str, auth_headers: dict[str, str]
) -> None:
    employee_email = f"employee-{uuid.uuid4()}@example.com"
    create_response = client.post(
        f"/organizations/{org_id}/members",
        headers=auth_headers,
        json={
            "email": employee_email,
            "full_name": "Employee Sam",
            "password": "password123",
            "membership_role": "EMPLOYEE",
        },
    )
    employee_user_id = create_response.json()["user_id"]

    login_response = client.post(
        "/auth/login",
        json={"email": employee_email, "password": "password123"},
    )
    employee_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = client.post(
        f"/organizations/{org_id}/members",
        headers=employee_headers,
        json={
            "email": f"new-{uuid.uuid4()}@example.com",
            "full_name": "Blocked User",
            "password": "password123",
            "membership_role": "EMPLOYEE",
        },
    )
    assert response.status_code == 403

    cleanup_user(db, employee_user_id)


def test_cannot_add_member_with_job_role_from_other_org(
    client: TestClient, db, org_id: str, auth_headers: dict[str, str]
) -> None:
    other_email = f"other-owner-{uuid.uuid4()}@example.com"
    other_register = client.post(
        "/auth/register",
        json={
            "email": other_email,
            "password": "password123",
            "full_name": "Other Owner",
            "organization_name": f"Other Org {uuid.uuid4()}",
        },
    )
    other_user_id = other_register.json()["id"]
    other_login = client.post(
        "/auth/login",
        json={"email": other_email, "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    other_org_id = client.get("/organizations/me", headers=other_headers).json()[0]["organization"]["id"]
    foreign_role_id = client.post(
        f"/organizations/{other_org_id}/job-roles",
        headers=other_headers,
        json={"name": "Trainer"},
    ).json()["id"]

    response = client.post(
        f"/organizations/{org_id}/members",
        headers=auth_headers,
        json={
            "email": f"blocked-{uuid.uuid4()}@example.com",
            "full_name": "Blocked User",
            "password": "password123",
            "membership_role": "EMPLOYEE",
            "job_role_ids": [foreign_role_id],
        },
    )
    assert response.status_code == 400

    cleanup_user(db, other_user_id)
