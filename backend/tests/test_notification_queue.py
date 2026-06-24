"""SQS notification queue tests (Week 5 Day 30)."""

from __future__ import annotations

import json
import uuid

import boto3
import pytest
from sqlalchemy.orm import Session

from app.models.enums import NotificationChannel, NotificationStatus, NotificationType
from app.services.notification_processor import (
    ProcessingOutcome,
    process_notification_payload,
    process_sqs_message_body,
    poll_and_process_messages,
)
from app.services.notification_service import create_notification
from app.services.queue import (
    JOB_TYPE_SEND_NOTIFICATION,
    build_notification_job_payload,
    enqueue_notification_delivery,
    get_sqs_client,
    is_sqs_configured,
)


def test_build_notification_job_payload_format(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    no_sqs: None,
) -> None:
    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.SCHEDULE_PUBLISHED,
        title="Schedule published",
        message="Your schedule is ready.",
    )
    db.commit()

    payload = build_notification_job_payload(notification)
    assert payload == {
        "type": JOB_TYPE_SEND_NOTIFICATION,
        "notification_id": str(notification.id),
        "organization_id": str(org_uuid),
        "recipient_user_id": str(recipient_id),
    }


def test_enqueue_notification_delivery_sends_message(
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
        notification_type=NotificationType.TIME_OFF_APPROVED,
        title="Time off approved",
        message="Enjoy your time off.",
    )
    db.commit()

    assert is_sqs_configured() is True
    assert notification.status == NotificationStatus.PENDING

    client = get_sqs_client()
    messages = client.receive_message(
        QueueUrl=mock_sqs,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=1,
    ).get("Messages", [])
    assert len(messages) == 1

    payload = json.loads(messages[0]["Body"])
    assert payload["type"] == JOB_TYPE_SEND_NOTIFICATION
    assert payload["notification_id"] == str(notification.id)


def test_worker_marks_notification_sent(
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
        notification_type=NotificationType.SHIFT_SWAP_REQUESTED,
        title="Swap requested",
        message="A shift swap needs review.",
    )
    db.commit()
    assert notification.status == NotificationStatus.PENDING

    result = process_notification_payload(
        db,
        build_notification_job_payload(notification),
    )
    assert result.outcome == ProcessingOutcome.SENT
    assert result.delete_message is True
    db.refresh(notification)
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None


def test_invalid_sqs_message_is_safe_to_delete(db: Session) -> None:
    result = process_sqs_message_body(db, "not-json")
    assert result.outcome == ProcessingOutcome.INVALID
    assert result.delete_message is True


def test_unknown_job_type_is_safe_to_delete(db: Session) -> None:
    result = process_notification_payload(db, {"type": "UNKNOWN", "notification_id": str(uuid.uuid4())})
    assert result.outcome == ProcessingOutcome.INVALID
    assert result.delete_message is True


def test_missing_notification_marks_not_found(db: Session) -> None:
    missing_id = uuid.uuid4()
    result = process_notification_payload(
        db,
        {
            "type": JOB_TYPE_SEND_NOTIFICATION,
            "notification_id": str(missing_id),
        },
    )
    assert result.outcome == ProcessingOutcome.NOT_FOUND
    assert result.delete_message is True
    assert result.notification_id == missing_id


def test_poll_and_process_messages_drains_queue(
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
        notification_type=NotificationType.TIME_OFF_REJECTED,
        title="Time off rejected",
        message="Request denied.",
    )
    db.commit()
    assert notification.status == NotificationStatus.PENDING

    results = poll_and_process_messages(db, wait_time_seconds=1, max_messages=5)
    assert len(results) == 1
    assert results[0].outcome == ProcessingOutcome.SENT

    db.refresh(notification)
    assert notification.status == NotificationStatus.SENT

    second_poll = poll_and_process_messages(db, wait_time_seconds=1, max_messages=5)
    assert second_poll == []


def test_create_notification_falls_back_without_sqs(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    no_sqs: None,
) -> None:
    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.DOCUMENT_UPLOADED,
        title="Document uploaded",
        message="A new document was uploaded.",
    )
    db.commit()

    assert is_sqs_configured() is False
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None


def test_enqueue_notification_delivery_returns_false_without_sqs(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    no_sqs: None,
) -> None:
    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.OPEN_SHIFT_CREATED,
        title="Open shifts",
        message="Coverage needed.",
        channel=NotificationChannel.EMAIL,
    )
    db.commit()

    assert enqueue_notification_delivery(notification) is False
