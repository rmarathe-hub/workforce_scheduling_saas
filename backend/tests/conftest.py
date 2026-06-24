import os
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND_ROOT / ".env")

# Prefer a dedicated test DB when configured (see backend/.env.example).
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

if not os.getenv("DATABASE_URL"):
    raise RuntimeError(
        "DATABASE_URL or TEST_DATABASE_URL must be set for pytest. "
        "Copy backend/.env.example to backend/.env and add your Supabase connection string."
    )

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


@pytest.fixture(autouse=True)
def disable_sqs_in_tests(monkeypatch: pytest.MonkeyPatch):
    """Keep API notification tests synchronous unless a test opts into mock_sqs."""
    monkeypatch.setenv("SQS_NOTIFICATION_QUEUE_URL", "")
    from app.config import Settings
    from app.services import queue as queue_module

    test_settings = Settings()
    monkeypatch.setattr("app.config.settings", test_settings)
    queue_module.get_sqs_client.cache_clear()


@pytest.fixture
def no_sqs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SQS_NOTIFICATION_QUEUE_URL", "")
    from app.config import Settings
    from app.services import queue as queue_module

    test_settings = Settings()
    monkeypatch.setattr("app.config.settings", test_settings)
    queue_module.get_sqs_client.cache_clear()
    yield
    queue_module.get_sqs_client.cache_clear()


@pytest.fixture
def mock_sqs(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    from app.config import Settings
    from app.services import queue as queue_module

    queue_module.get_sqs_client.cache_clear()

    with mock_aws():
        client = boto3.client("sqs", region_name="us-east-1")
        queue_url = client.create_queue(QueueName="shiftops-notifications-queue")["QueueUrl"]
        monkeypatch.setenv("SQS_NOTIFICATION_QUEUE_URL", queue_url)

        test_settings = Settings()
        monkeypatch.setattr("app.config.settings", test_settings)
        queue_module.get_sqs_client.cache_clear()
        yield queue_url
        queue_module.get_sqs_client.cache_clear()


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
