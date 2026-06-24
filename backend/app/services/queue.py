"""AWS SQS helpers for async notification delivery jobs."""

from __future__ import annotations

import json
import logging
from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app import config
from app.models.notification import Notification

logger = logging.getLogger(__name__)

JOB_TYPE_SEND_NOTIFICATION = "SEND_NOTIFICATION"


@lru_cache
def get_sqs_client():
    return boto3.client(
        "sqs",
        region_name=config.settings.aws_region,
        aws_access_key_id=config.settings.aws_access_key_id,
        aws_secret_access_key=config.settings.aws_secret_access_key,
    )


def is_sqs_configured() -> bool:
    return bool(
        config.settings.sqs_notification_queue_url.strip()
        and config.settings.aws_access_key_id.strip()
        and config.settings.aws_secret_access_key.strip()
    )


def build_notification_job_payload(notification: Notification) -> dict[str, str]:
    return {
        "type": JOB_TYPE_SEND_NOTIFICATION,
        "notification_id": str(notification.id),
        "organization_id": str(notification.organization_id),
        "recipient_user_id": str(notification.recipient_user_id),
    }


def enqueue_notification_delivery(notification: Notification) -> bool:
    """Enqueue a notification delivery job. Returns False if SQS is unavailable."""
    if not is_sqs_configured():
        logger.warning(
            "SQS not configured; skipping queue enqueue for notification_id=%s",
            notification.id,
        )
        return False

    payload = build_notification_job_payload(notification)
    try:
        client = get_sqs_client()
        client.send_message(
            QueueUrl=config.settings.sqs_notification_queue_url,
            MessageBody=json.dumps(payload),
        )
        logger.info(
            "Enqueued notification delivery notification_id=%s type=%s",
            notification.id,
            payload["type"],
        )
        return True
    except (BotoCoreError, ClientError):
        logger.exception(
            "Failed to enqueue notification delivery notification_id=%s",
            notification.id,
        )
        return False
