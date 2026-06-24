"""Local consumer safety guards (production Lambda must be sole consumer)."""

from __future__ import annotations

import pytest

from app.services.consumer_safety import assert_local_consumer_allowed, is_production_consumer_context


def test_production_context_detected(
    monkeypatch: pytest.MonkeyPatch,
    mock_sqs: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app import config

    config.settings = config.Settings()

    assert is_production_consumer_context() is True


def test_development_context_allows_local_consumer(
    monkeypatch: pytest.MonkeyPatch,
    mock_sqs: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    from app import config

    config.settings = config.Settings()

    assert is_production_consumer_context() is False


def test_production_blocks_without_force(
    monkeypatch: pytest.MonkeyPatch,
    mock_sqs: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app import config

    config.settings = config.Settings()

    with pytest.raises(SystemExit) as exc:
        assert_local_consumer_allowed(force=False)
    assert exc.value.code == 2


def test_production_allows_with_force(
    monkeypatch: pytest.MonkeyPatch,
    mock_sqs: str,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app import config

    config.settings = config.Settings()

    assert_local_consumer_allowed(force=True)
