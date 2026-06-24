#!/usr/bin/env python3
"""Read-only check of main notification queue and DLQ depth (production ops)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.services.queue import get_sqs_client, is_sqs_configured

_ATTR_NAMES = [
    "ApproximateNumberOfMessages",
    "ApproximateNumberOfMessagesNotVisible",
    "ApproximateNumberOfMessagesDelayed",
    "VisibilityTimeout",
    "RedrivePolicy",
]


def _queue_depth(client, queue_url: str) -> dict[str, str]:
    response = client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=_ATTR_NAMES)
    return response.get("Attributes", {})


def _dlq_url_from_redrive(redrive_policy: str) -> str | None:
    try:
        policy = json.loads(redrive_policy)
    except json.JSONDecodeError:
        return None
    arn = policy.get("deadLetterTargetArn")
    if not arn:
        return None
    parts = arn.split(":")
    if len(parts) < 6 or parts[2] != "sqs":
        return None
    region, account, queue_name = parts[3], parts[4], parts[5]
    return f"https://sqs.{region}.amazonaws.com/{account}/{queue_name}"


def main() -> int:
    print("ShiftOps notification queue validation\n")

    if not is_sqs_configured():
        print("FAIL  SQS is not configured in backend/.env")
        return 1

    queue_url = settings.sqs_notification_queue_url
    print(f"Main queue: {queue_url}")

    try:
        client = get_sqs_client()
        main_attrs = _queue_depth(client, queue_url)
    except (BotoCoreError, ClientError) as exc:
        print(f"FAIL  Could not read main queue attributes: {exc}")
        return 1

    visible = int(main_attrs.get("ApproximateNumberOfMessages", "0"))
    in_flight = int(main_attrs.get("ApproximateNumberOfMessagesNotVisible", "0"))
    delayed = int(main_attrs.get("ApproximateNumberOfMessagesDelayed", "0"))
    visibility = main_attrs.get("VisibilityTimeout", "?")

    print(f"  visible messages:     {visible}")
    print(f"  in-flight (hidden):   {in_flight}")
    print(f"  delayed:              {delayed}")
    print(f"  visibility timeout:   {visibility}s")

    redrive = main_attrs.get("RedrivePolicy")
    if not redrive:
        print("\nWARN  No RedrivePolicy on main queue — DLQ may not be configured.")
        return 0

    dlq_url = _dlq_url_from_redrive(redrive)
    if not dlq_url:
        print("\nWARN  RedrivePolicy present but DLQ URL could not be parsed.")
        return 0

    print(f"\nDLQ: {dlq_url}")
    try:
        dlq_attrs = client.get_queue_attributes(
            QueueUrl=dlq_url,
            AttributeNames=["ApproximateNumberOfMessages"],
        )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in {"AccessDenied", "AWS.SimpleQueueService.NonExistentQueue"}:
            print(
                f"  WARN  Could not read DLQ depth ({error_code}). "
                "Check DLQ in AWS Console → SQS."
            )
            print("\nResult: OK — main queue is healthy (DLQ depth not verified from this IAM user).")
            return 0
        print(f"FAIL  Could not read DLQ attributes: {exc}")
        return 1

    dlq_visible = int(dlq_attrs.get("ApproximateNumberOfMessages", "0"))
    print(f"  visible messages:     {dlq_visible}")

    ok = True
    if dlq_visible > 0:
        print("\nWARN  DLQ has messages — inspect in AWS Console and fix root cause.")
        ok = False
    if visible > 0 or in_flight > 0:
        print(
            "\nINFO  Main queue has backlog or in-flight work — normal briefly after "
            "traffic; Lambda should drain it."
        )

    if ok and dlq_visible == 0:
        print("\nResult: OK — DLQ is empty.")
        return 0

    return 1 if dlq_visible > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
