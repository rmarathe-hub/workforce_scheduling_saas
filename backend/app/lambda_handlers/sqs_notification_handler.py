"""SQS notification consumer for future AWS Lambda deployment.

This module is a skeleton only. Do not deploy until Lambda packaging/IAM is added.

Future Lambda consumer can call the same notification processing functions used by:
- backend/scripts/notification_worker.py
- backend/scripts/process_notifications_once.py

When wired to an SQS trigger, Lambda deletes successful batch items automatically.
Do not call delete_sqs_message from this handler.
"""

from __future__ import annotations

import logging
from typing import Any

from app.database import SessionLocal
from app.services.notification_processor import NotificationProcessResult, process_sqs_message

logger = logging.getLogger(__name__)


def handle_sqs_event(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda handler for SQS trigger events."""
    records = event.get("Records", [])
    results: list[NotificationProcessResult] = []

    db = SessionLocal()
    try:
        for record in records:
            message = {
                "Body": record.get("body") or record.get("Body", ""),
                "MessageId": record.get("messageId") or record.get("MessageId"),
            }
            results.append(process_sqs_message(db, message))
    finally:
        db.close()

    return {
        "processed": len(results),
        "outcomes": [result.outcome.value for result in results],
    }
