"""Health and readiness endpoint tests (Week 5 Day 34)."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import config


def test_health_returns_ok_with_component_checks(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["database"] == "ok"
    assert isinstance(data["s3_configured"], bool)
    assert isinstance(data["sqs_configured"], bool)
    assert data["environment"] == config.settings.environment


def test_health_does_not_expose_secrets(client: TestClient) -> None:
    response = client.get("/health")
    body = response.text.lower()
    assert response.status_code == 200

    assert config.settings.jwt_secret_key.lower() not in body
    assert config.settings.database_url.lower() not in body
    if config.settings.aws_access_key_id:
        assert config.settings.aws_access_key_id.lower() not in body
    if config.settings.aws_secret_access_key:
        assert config.settings.aws_secret_access_key.lower() not in body
    if config.settings.sqs_notification_queue_url:
        assert config.settings.sqs_notification_queue_url.lower() not in body


def test_readiness_returns_ok_when_database_is_up(client: TestClient) -> None:
    response = client.get("/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ready", "database": "ok"}


def test_readiness_returns_503_when_database_is_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail_connect():
        raise RuntimeError("database unreachable")

    mock_engine = MagicMock()
    mock_engine.connect.side_effect = _fail_connect
    monkeypatch.setattr("app.services.health_service.engine", mock_engine)

    response = client.get("/readiness")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": "error"}


def test_health_marks_degraded_when_database_is_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fail_connect():
        raise RuntimeError("database unreachable")

    mock_engine = MagicMock()
    mock_engine.connect.side_effect = _fail_connect
    monkeypatch.setattr("app.services.health_service.engine", mock_engine)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "error"


def test_response_includes_request_id_header(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "test-request-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-request-123"
