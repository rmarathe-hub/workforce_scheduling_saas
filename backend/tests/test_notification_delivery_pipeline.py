"""End-to-end notification delivery: enqueue → Lambda handler → SENT."""

from __future__ import annotations

import json
import uuid

from sqlalchemy.orm import Session

from app.lambda_handlers.sqs_notification_handler import handle_sqs_event
from app.models.enums import NotificationStatus, NotificationType
from app.services.notification_service import create_notification
from app.services.queue import build_notification_job_payload, get_sqs_client


def test_enqueue_then_lambda_handler_delivers_notification(
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
        message="Your schedule is ready.",
    )
    db.commit()
    assert notification.status == NotificationStatus.PENDING

    client = get_sqs_client()
    messages = client.receive_message(
        QueueUrl=mock_sqs,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=0,
    ).get("Messages", [])
    assert len(messages) == 1

    response = handle_sqs_event(
        {
            "Records": [
                {
                    "messageId": messages[0]["MessageId"],
                    "body": messages[0]["Body"],
                    "eventSource": "aws:sqs",
                }
            ]
        },
        None,
    )

    assert response["outcomes"] == ["SENT"]
    assert "batchItemFailures" not in response
    db.refresh(notification)
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None

    payload = json.loads(messages[0]["Body"])
    assert payload == build_notification_job_payload(notification)
