import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from tests.helpers import cleanup_user


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def registered_user(client: TestClient, db: Session) -> Generator[dict[str, str], None, None]:
    email = f"test-{uuid.uuid4()}@example.com"
    password = "password123"
    org_name = f"Test Org {uuid.uuid4()}"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Test User",
            "organization_name": org_name,
        },
    )
    assert response.status_code == 201
    user_id = response.json()["id"]

    yield {"email": email, "password": password, "id": user_id, "organization_name": org_name}

    cleanup_user(db, user_id)


@pytest.fixture
def auth_headers(client: TestClient, registered_user: dict[str, str]) -> dict[str, str]:
    login_response = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def org_id(client: TestClient, auth_headers: dict[str, str]) -> str:
    response = client.get("/organizations/me", headers=auth_headers)
    return response.json()[0]["organization"]["id"]
