"""Shared notification delivery processing for workers and future Lambda."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app import config
from app.models.enums import NotificationStatus
from app.models.notification import Notification
from app.services.queue import JOB_TYPE_SEND_NOTIFICATION, get_sqs_client, is_sqs_configured

logger = logging.getLogger(__name__)

_VISIBLE_STATUSES = (NotificationStatus.SENT, NotificationStatus.READ)
_MAX_ERROR_MESSAGE_LENGTH = 2000


class ProcessingOutcome(str, Enum):
    SENT = "SENT"
    ALREADY_DELIVERED = "ALREADY_DELIVERED"
    FAILED = "FAILED"
    INVALID = "INVALID"
    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True)
class NotificationProcessResult:
    outcome: ProcessingOutcome
    notification_id: uuid.UUID | None = None
    delete_message: bool = False
    detail: str | None = None


def _mark_notification_sent(notification: Notification) -> None:
    now = datetime.now(timezone.utc)
    notification.status = NotificationStatus.SENT
    notification.sent_at = now


def _mark_notification_failed(notification: Notification, *, error_message: str) -> None:
    notification.status = NotificationStatus.FAILED
    notification.error_message = error_message[:_MAX_ERROR_MESSAGE_LENGTH]
    notification.retry_count += 1


def process_notification_payload(
    db: Session,
    payload: dict[str, Any],
) -> NotificationProcessResult:
    """Deliver one notification from a parsed SQS job payload."""
    if payload.get("type") != JOB_TYPE_SEND_NOTIFICATION:
        detail = f"Unknown job type: {payload.get('type')!r}"
        logger.warning(detail)
        return NotificationProcessResult(
            outcome=ProcessingOutcome.INVALID,
            delete_message=True,
            detail=detail,
        )

    notification_id_raw = payload.get("notification_id")
    if not notification_id_raw:
        detail = "Missing notification_id in payload"
        logger.error(detail)
        return NotificationProcessResult(
            outcome=ProcessingOutcome.INVALID,
            delete_message=True,
            detail=detail,
        )

    try:
        notification_id = uuid.UUID(str(notification_id_raw))
    except ValueError:
        detail = f"Invalid notification_id: {notification_id_raw!r}"
        logger.error(detail)
        return NotificationProcessResult(
            outcome=ProcessingOutcome.INVALID,
            delete_message=True,
            detail=detail,
        )

    notification = db.get(Notification, notification_id)
    if notification is None:
        detail = f"Notification not found: {notification_id}"
        logger.error(detail)
        return NotificationProcessResult(
            outcome=ProcessingOutcome.NOT_FOUND,
            notification_id=notification_id,
            delete_message=True,
            detail=detail,
        )

    if notification.status in _VISIBLE_STATUSES:
        detail = f"Notification already delivered: {notification_id}"
        logger.info(detail)
        return NotificationProcessResult(
            outcome=ProcessingOutcome.ALREADY_DELIVERED,
            notification_id=notification_id,
            delete_message=True,
            detail=detail,
        )

    try:
        _mark_notification_sent(notification)
        db.commit()
        db.refresh(notification)
        logger.info(
            "Marked notification SENT notification_id=%s recipient_user_id=%s",
            notification.id,
            notification.recipient_user_id,
        )
        return NotificationProcessResult(
            outcome=ProcessingOutcome.SENT,
            notification_id=notification_id,
            delete_message=True,
        )
    except Exception as exc:
        db.rollback()
        logger.exception(
            "Failed to deliver notification notification_id=%s",
            notification_id,
        )
        try:
            failed_notification = db.get(Notification, notification_id)
            if failed_notification is not None:
                _mark_notification_failed(failed_notification, error_message=str(exc))
                db.commit()
        except Exception:
            db.rollback()
            logger.exception(
                "Failed to mark notification FAILED notification_id=%s",
                notification_id,
            )
            return NotificationProcessResult(
                outcome=ProcessingOutcome.FAILED,
                notification_id=notification_id,
                delete_message=False,
                detail=str(exc),
            )

        return NotificationProcessResult(
            outcome=ProcessingOutcome.FAILED,
            notification_id=notification_id,
            delete_message=True,
            detail=str(exc),
        )


def process_sqs_message_body(db: Session, body: str) -> NotificationProcessResult:
    """Parse an SQS message body and deliver the referenced notification."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        detail = f"Invalid JSON payload: {body[:200]}"
        logger.error(detail)
        return NotificationProcessResult(
            outcome=ProcessingOutcome.INVALID,
            delete_message=True,
            detail=detail,
        )

    if not isinstance(payload, dict):
        detail = "SQS payload must be a JSON object"
        logger.error(detail)
        return NotificationProcessResult(
            outcome=ProcessingOutcome.INVALID,
            delete_message=True,
            detail=detail,
        )

    return process_notification_payload(db, payload)


def process_sqs_message(db: Session, message: dict[str, Any]) -> NotificationProcessResult:
    """Process one boto3 SQS message dict. Future Lambda handlers can reuse this."""
    body = message.get("Body", "")
    logger.info("Received SQS message message_id=%s", message.get("MessageId"))
    return process_sqs_message_body(db, body)


def process_received_messages(
    db: Session,
    messages: list[dict[str, Any]],
) -> list[NotificationProcessResult]:
    """Process already-received SQS messages without polling the queue."""
    results: list[NotificationProcessResult] = []
    for message in messages:
        result = process_sqs_message(db, message)
        results.append(result)
        if result.delete_message:
            delete_sqs_message(message["ReceiptHandle"])
        else:
            logger.warning(
                "Leaving SQS message on queue notification_id=%s outcome=%s",
                result.notification_id,
                result.outcome.value,
            )
    return results


def delete_sqs_message(receipt_handle: str) -> None:
    client = get_sqs_client()
    client.delete_message(
        QueueUrl=config.settings.sqs_notification_queue_url,
        ReceiptHandle=receipt_handle,
    )
    logger.info("Deleted SQS message")


def poll_and_process_messages(
    db: Session,
    *,
    wait_time_seconds: int,
    max_messages: int = 10,
) -> list[NotificationProcessResult]:
    """Poll SQS once, process available messages, and delete successful ones."""
    if not is_sqs_configured():
        raise RuntimeError(
            "SQS is not configured. Set AWS credentials and SQS_NOTIFICATION_QUEUE_URL."
        )

    client = get_sqs_client()
    queue_url = config.settings.sqs_notification_queue_url
    bounded_wait = max(0, min(wait_time_seconds, 20))
    logger.info(
        "Polling queue wait_time_seconds=%s max_messages=%s queue_url=%s",
        bounded_wait,
        max_messages,
        queue_url,
    )

    response = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=bounded_wait,
    )
    messages = response.get("Messages", [])
    if not messages:
        logger.info("No messages available")
        return []

    return process_received_messages(db, messages)
