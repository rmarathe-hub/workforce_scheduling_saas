import os

# Use a dedicated test database when configured (never hardcode production URLs).
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

import uuid
from collections.abc import Generator

import boto3
import httpx
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from tests.helpers import cleanup_user


@pytest.fixture
def mock_s3(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("S3_BUCKET_NAME", "shiftops-test-bucket")

    from app.config import Settings

    test_settings = Settings()
    monkeypatch.setattr("app.config.settings", test_settings)
    monkeypatch.setattr("app.services.s3_service.settings", test_settings)

    from app.services import s3_service

    s3_service.get_s3_client.cache_clear()

    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="shiftops-test-bucket")
        yield
        s3_service.get_s3_client.cache_clear()


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


@pytest.fixture
def e2e_api_base_url() -> str:
    base_url = os.getenv("E2E_API_BASE_URL", "").rstrip("/")
    if not base_url:
        pytest.skip("Set E2E_API_BASE_URL to run deployed API smoke tests")
    return base_url


@pytest.fixture
def e2e_client(e2e_api_base_url: str) -> Generator[httpx.Client, None, None]:
    with httpx.Client(base_url=e2e_api_base_url, timeout=60.0) as client:
        yield client
