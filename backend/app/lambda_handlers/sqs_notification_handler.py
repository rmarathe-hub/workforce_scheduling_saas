"""AWS Lambda SQS consumer for in-app notification delivery."""

from __future__ import annotations

import logging
from typing import Any

from app.database import SessionLocal
from app.services.notification_processor import NotificationProcessResult, process_sqs_message

logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)


def _record_message_id(record: dict[str, Any]) -> str:
    return str(record.get("messageId") or record.get("MessageId") or "")


def _record_body(record: dict[str, Any]) -> str:
    return str(record.get("body") or record.get("Body") or "")


def _process_record(record: dict[str, Any]) -> NotificationProcessResult:
    message_id = _record_message_id(record)
    db = SessionLocal()
    try:
        message = {
            "Body": _record_body(record),
            "MessageId": message_id,
        }
        result = process_sqs_message(db, message)
        logger.info(
            "Processed SQS record message_id=%s outcome=%s notification_id=%s",
            message_id,
            result.outcome.value,
            result.notification_id,
        )
        return result
    finally:
        db.close()


def handle_sqs_event(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for SQS trigger events with partial batch failure support."""
    records = event.get("Records", [])
    results: list[NotificationProcessResult] = []
    batch_item_failures: list[dict[str, str]] = []

    for record in records:
        message_id = _record_message_id(record)
        result = _process_record(record)
        results.append(result)
        if not result.delete_message:
            if message_id:
                batch_item_failures.append({"itemIdentifier": message_id})
            else:
                logger.error(
                    "Cannot report batch item failure without messageId outcome=%s",
                    result.outcome.value,
                )

    response: dict[str, Any] = {
        "processed": len(results),
        "outcomes": [result.outcome.value for result in results],
    }
    if batch_item_failures:
        response["batchItemFailures"] = batch_item_failures
    return response
