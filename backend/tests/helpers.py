import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.user import User


def login_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_employee_member(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    *,
    email: str | None = None,
    password: str = "password123",
) -> dict[str, str]:
    locations = client.get(f"/organizations/{org_id}/locations", headers=auth_headers).json()
    if locations:
        location_id = locations[0]["id"]
    else:
        location_id = client.post(
            f"/organizations/{org_id}/locations",
            headers=auth_headers,
            json={"name": "Main"},
        ).json()["id"]

    job_roles = client.get(f"/organizations/{org_id}/job-roles", headers=auth_headers).json()
    if job_roles:
        job_role_id = job_roles[0]["id"]
    else:
        job_role_id = client.post(
            f"/organizations/{org_id}/job-roles",
            headers=auth_headers,
            json={"name": "Cashier"},
        ).json()["id"]

    employee_email = email or f"employee-{uuid.uuid4()}@example.com"
    employee_response = client.post(
        f"/organizations/{org_id}/members",
        headers=auth_headers,
        json={
            "email": employee_email,
            "full_name": "Shift Employee",
            "password": password,
            "membership_role": "EMPLOYEE",
            "location_id": location_id,
            "job_role_ids": [job_role_id],
        },
    )
    user_id = employee_response.json()["user_id"]

    return {
        "user_id": user_id,
        "email": employee_email,
        "headers": login_headers(client, employee_email, password),
        "location_id": location_id,
        "job_role_id": job_role_id,
    }


def cleanup_user(db: Session, user_id: str) -> None:
    uid = uuid.UUID(user_id)

    memberships = db.scalars(
        select(OrganizationMembership.organization_id).where(
            OrganizationMembership.user_id == uid
        )
    ).all()
    org_ids = set(memberships)

    db.execute(delete(OrganizationMembership).where(OrganizationMembership.user_id == uid))

    for org_id in org_ids:
        remaining = db.scalar(
            select(func.count())
            .select_from(OrganizationMembership)
            .where(OrganizationMembership.organization_id == org_id)
        )
        if remaining == 0:
            db.execute(delete(Organization).where(Organization.id == org_id))

    db.execute(delete(User).where(User.id == uid))
    db.commit()
