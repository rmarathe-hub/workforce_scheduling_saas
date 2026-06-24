"""Lambda SQS notification handler tests (Week 6 Day 36)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from app.lambda_handlers.sqs_notification_handler import handle_sqs_event
from app.models.enums import NotificationStatus, NotificationType
from app.services.notification_processor import ProcessingOutcome
from app.services.notification_service import create_notification
from app.services.queue import build_notification_job_payload

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _sqs_record(
    *,
    message_id: str,
    body: str,
) -> dict[str, str]:
    return {
        "messageId": message_id,
        "receiptHandle": f"receipt-{message_id}",
        "body": body,
        "eventSource": "aws:sqs",
        "awsRegion": "us-east-1",
    }


def test_handle_empty_event_returns_no_failures() -> None:
    response = handle_sqs_event({"Records": []}, None)
    assert response == {"processed": 0, "outcomes": []}
    assert "batchItemFailures" not in response


def test_handle_fixture_event_marks_notification_sent(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    mock_sqs: str,
) -> None:
    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.SCHEDULE_PUBLISHED,
        title="Schedule published",
        message="Week ready.",
    )
    db.commit()

    event = {
        "Records": [
            _sqs_record(
                message_id="lambda-test-message-1",
                body=json.dumps(build_notification_job_payload(notification)),
            )
        ]
    }

    response = handle_sqs_event(event, None)

    assert response["processed"] == 1
    assert response["outcomes"] == [ProcessingOutcome.SENT.value]
    assert "batchItemFailures" not in response
    db.refresh(notification)
    assert notification.status == NotificationStatus.SENT


def test_invalid_payload_is_removed_from_queue(db: Session) -> None:
    response = handle_sqs_event(
        {
            "Records": [
                _sqs_record(
                    message_id="lambda-invalid-json",
                    body="not-json",
                )
            ]
        },
        None,
    )

    assert response["outcomes"] == [ProcessingOutcome.INVALID.value]
    assert "batchItemFailures" not in response


def test_missing_notification_is_removed_from_queue(db: Session) -> None:
    missing_id = uuid.uuid4()
    response = handle_sqs_event(
        {
            "Records": [
                _sqs_record(
                    message_id="lambda-missing-notification",
                    body=json.dumps(
                        {
                            "type": "SEND_NOTIFICATION",
                            "notification_id": str(missing_id),
                        }
                    ),
                )
            ]
        },
        None,
    )

    assert response["outcomes"] == [ProcessingOutcome.NOT_FOUND.value]
    assert "batchItemFailures" not in response


def test_hard_failure_reports_batch_item_failure(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    mock_sqs: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.TIME_OFF_APPROVED,
        title="Approved",
        message="Enjoy.",
    )
    db.commit()

    def _raise_delivery_error(*_args, **_kwargs):
        raise RuntimeError("delivery failed")

    def _raise_failed_mark(*_args, **_kwargs):
        raise RuntimeError("cannot mark failed")

    monkeypatch.setattr(
        "app.services.notification_processor._mark_notification_sent",
        _raise_delivery_error,
    )
    monkeypatch.setattr(
        "app.services.notification_processor._mark_notification_failed",
        _raise_failed_mark,
    )

    message_id = "lambda-hard-failure"
    response = handle_sqs_event(
        {
            "Records": [
                _sqs_record(
                    message_id=message_id,
                    body=json.dumps(build_notification_job_payload(notification)),
                )
            ]
        },
        None,
    )

    assert response["outcomes"] == [ProcessingOutcome.FAILED.value]
    assert response["batchItemFailures"] == [{"itemIdentifier": message_id}]


def test_batch_mixed_success_and_failure(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    mock_sqs: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.SHIFT_SWAP_REQUESTED,
        title="Swap",
        message="Review swap.",
    )
    db.commit()

    def _raise_delivery_error(*_args, **_kwargs):
        raise RuntimeError("delivery failed")

    def _raise_failed_mark(*_args, **_kwargs):
        raise RuntimeError("cannot mark failed")

    monkeypatch.setattr(
        "app.services.notification_processor._mark_notification_sent",
        _raise_delivery_error,
    )
    monkeypatch.setattr(
        "app.services.notification_processor._mark_notification_failed",
        _raise_failed_mark,
    )

    response = handle_sqs_event(
        {
            "Records": [
                _sqs_record(
                    message_id="lambda-success",
                    body=json.dumps(build_notification_job_payload(notification)),
                ),
                _sqs_record(
                    message_id="lambda-invalid",
                    body="not-json",
                ),
            ]
        },
        None,
    )

    assert response["processed"] == 2
    assert response["outcomes"] == [
        ProcessingOutcome.FAILED.value,
        ProcessingOutcome.INVALID.value,
    ]
    assert response["batchItemFailures"] == [{"itemIdentifier": "lambda-success"}]

def test_sample_fixture_file_has_expected_shape() -> None:
    payload = json.loads((FIXTURES_DIR / "sqs_lambda_event.json").read_text())
    assert payload["Records"]
    record = payload["Records"][0]
    assert record["messageId"]
    assert record["body"]
