#!/usr/bin/env python3
"""Validate local AWS SQS configuration for notification jobs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.services.queue import JOB_TYPE_SEND_NOTIFICATION

TEST_PAYLOAD = {
    "type": JOB_TYPE_SEND_NOTIFICATION,
    "notification_id": "00000000-0000-0000-0000-000000000001",
    "organization_id": "00000000-0000-0000-0000-000000000002",
    "recipient_user_id": "00000000-0000-0000-0000-000000000003",
}


def _check_env_vars() -> bool:
    print("Checking environment variables...")
    checks = {
        "AWS_ACCESS_KEY_ID": settings.aws_access_key_id,
        "AWS_SECRET_ACCESS_KEY": settings.aws_secret_access_key,
        "AWS_REGION": settings.aws_region,
        "SQS_NOTIFICATION_QUEUE_URL": settings.sqs_notification_queue_url,
    }
    ok = True
    for name, value in checks.items():
        if not value.strip():
            print(f"  FAIL  {name} is missing or empty")
            ok = False
        elif "SECRET" in name or name == "AWS_ACCESS_KEY_ID":
            print(f"  OK    {name} is set")
        else:
            print(f"  OK    {name} = {value}")
    return ok


def main() -> int:
    print("ShiftOps SQS setup validation\n")

    if not _check_env_vars():
        print("\nResult: FAILED — fix missing env vars in backend/.env")
        return 1

    print("\nCreating boto3 SQS client...")
    try:
        import boto3

        client = boto3.client(
            "sqs",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        print("  OK    boto3 client created")
    except (BotoCoreError, ImportError) as exc:
        print(f"  FAIL  Could not create boto3 client: {exc}")
        return 1

    queue_url = settings.sqs_notification_queue_url
    print(f"\nTesting send/receive on queue: {queue_url}")

    try:
        send_response = client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(TEST_PAYLOAD),
        )
        message_id = send_response.get("MessageId")
        print(f"  OK    send_message worked message_id={message_id}")
    except ClientError as exc:
        print(f"  FAIL  send_message: {exc}")
        return 1

    try:
        receive_response = client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
        )
        messages = receive_response.get("Messages", [])
        if not messages:
            print("  FAIL  receive_message returned no messages")
            return 1
        receipt_handle = messages[0]["ReceiptHandle"]
        print("  OK    receive_message worked")
    except ClientError as exc:
        print(f"  FAIL  receive_message: {exc}")
        return 1

    try:
        client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
        print("  OK    delete_message worked")
    except ClientError as exc:
        print(f"  FAIL  delete_message: {exc}")
        return 1

    print("\nResult: ALL PASSED — SQS setup is ready for notification jobs.")
    print(
        "Next: local dev → `python scripts/notification_worker.py`; "
        "production → AWS Lambda consumes the queue (do not run the local worker)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
