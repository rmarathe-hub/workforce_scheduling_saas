"""Extended auth validation and error-path tests."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from tests.helpers import cleanup_user, login_headers, register_user_with_org


def test_register_duplicate_email_returns_400(client: TestClient, db: Session) -> None:
    email = f"dup-{uuid.uuid4()}@example.com"
    first = register_user_with_org(client, email=email)
    second = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": "Another",
            "organization_name": f"Org {uuid.uuid4()}",
        },
    )
    assert second.status_code == 400
    cleanup_user(db, first["user_id"])


def test_register_invalid_email_returns_422(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "not-an-email",
            "password": "password123",
            "full_name": "User",
            "organization_name": "Org",
        },
    )
    assert response.status_code == 422


def test_register_short_password_returns_422(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": f"short-{uuid.uuid4()}@example.com",
            "password": "short",
            "full_name": "User",
            "organization_name": "Org",
        },
    )
    assert response.status_code == 422


def test_register_missing_organization_name_returns_422(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": f"missing-{uuid.uuid4()}@example.com",
            "password": "password123",
            "full_name": "User",
            "organization_name": "",
        },
    )
    assert response.status_code == 422


def test_login_invalid_email_format_returns_422(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"email": "bad-email", "password": "password123"},
    )
    assert response.status_code == 422


def test_me_with_malformed_bearer_header_returns_401(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "NotBearer token"})
    assert response.status_code == 401


def test_protected_org_endpoint_without_bearer_prefix_returns_401(
    client: TestClient, org_id: str
) -> None:
    response = client.get(
        f"/organizations/{org_id}/locations",
        headers={"Authorization": "token-without-bearer"},
    )
    assert response.status_code == 401


def test_inactive_user_cannot_access_protected_route(
    client: TestClient, db: Session
) -> None:
    user = register_user_with_org(client)
    db_user = db.get(User, uuid.UUID(user["user_id"]))
    assert db_user is not None
    db_user.is_active = False
    db.commit()

    response = client.get("/auth/me", headers=user["headers"])
    assert response.status_code == 403

    cleanup_user(db, user["user_id"])
