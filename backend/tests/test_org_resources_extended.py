"""Extended organization resource validation tests."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_employee_member, cleanup_user, register_user_with_org


def test_duplicate_job_role_name_returns_400(
    client: TestClient, org_id: str, auth_headers: dict[str, str]
) -> None:
    client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cashier"},
    )
    response = client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cashier"},
    )
    assert response.status_code == 400


def test_add_existing_user_to_org_without_password(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    existing = register_user_with_org(client)
    response = client.post(
        f"/organizations/{org_id}/members",
        headers=auth_headers,
        json={
            "email": existing["email"],
            "full_name": "Existing User",
            "membership_role": "MANAGER",
        },
    )
    assert response.status_code == 201
    cleanup_user(db, existing["user_id"])


def test_add_member_with_foreign_job_role_returns_400(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    other_org = register_user_with_org(client)
    foreign_role_id = client.post(
        f"/organizations/{other_org['org_id']}/job-roles",
        headers=other_org["headers"],
        json={"name": "Foreign Role"},
    ).json()["id"]
    location_id = client.post(
        f"/organizations/{org_id}/locations",
        headers=auth_headers,
        json={"name": "Main"},
    ).json()["id"]

    response = client.post(
        f"/organizations/{org_id}/members",
        headers=auth_headers,
        json={
            "email": f"new-{uuid.uuid4()}@example.com",
            "full_name": "New Employee",
            "password": "password123",
            "membership_role": "EMPLOYEE",
            "location_id": location_id,
            "job_role_ids": [foreign_role_id],
        },
    )
    assert response.status_code == 400
    cleanup_user(db, other_org["user_id"])
