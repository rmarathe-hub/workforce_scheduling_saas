#!/usr/bin/env python3
"""Process available SQS notification messages once and exit."""

from __future__ import annotations

import argparse
import logging
import sys
from collections import Counter
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.services.notification_processor import ProcessingOutcome, poll_and_process_messages
from app.services.queue import is_sqs_configured

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [process_notifications_once] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Poll SQS once, process notification jobs, and exit."
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=5,
        help="Long-poll wait time for SQS receive_message (default: 5)",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=10,
        help="Maximum messages to receive in one poll (default: 10)",
    )
    args = parser.parse_args()

    if not is_sqs_configured():
        print(
            "SQS is not configured. Set AWS credentials and SQS_NOTIFICATION_QUEUE_URL "
            "in backend/.env"
        )
        return 1

    db = SessionLocal()
    try:
        results = poll_and_process_messages(
            db,
            wait_time_seconds=args.wait_seconds,
            max_messages=args.max_messages,
        )
    finally:
        db.close()

    counts = Counter(result.outcome for result in results)
    processed = len(results)
    print(f"Processed {processed} message(s)")
    for outcome in ProcessingOutcome:
        if counts[outcome]:
            print(f"  {outcome.value}: {counts[outcome]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
