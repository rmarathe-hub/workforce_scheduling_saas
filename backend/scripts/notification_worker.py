#!/usr/bin/env python3
"""Poll SQS and deliver in-app notifications."""

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal
from app.services.consumer_safety import assert_local_consumer_allowed
from app.services.notification_processor import poll_and_process_messages
from app.services.queue import is_sqs_configured

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [notification_worker] %(message)s",
)
logger = logging.getLogger(__name__)

_running = True
POLL_WAIT_SECONDS = 20
MAX_MESSAGES = 10


def _handle_shutdown(signum: int, _frame) -> None:
    global _running
    logger.info("Received signal %s, shutting down...", signum)
    _running = False


def run_worker_loop() -> int:
    if not is_sqs_configured():
        print(
            "SQS is not configured. Set AWS credentials and SQS_NOTIFICATION_QUEUE_URL "
            "in backend/.env"
        )
        return 1

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    logger.info("Starting notification worker (continuous polling)")

    while _running:
        db = SessionLocal()
        try:
            results = poll_and_process_messages(
                db,
                wait_time_seconds=POLL_WAIT_SECONDS,
                max_messages=MAX_MESSAGES,
            )
            if results:
                logger.info("Processed %s message(s) in batch", len(results))
        except Exception:
            logger.exception("Batch processing failed; continuing to poll")
        finally:
            db.close()

    logger.info("Notification worker stopped")
    return 0


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Poll SQS continuously and deliver in-app notifications (local/dev)."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow running when ENVIRONMENT=production (emergency only)",
    )
    args = parser.parse_args()
    assert_local_consumer_allowed(force=args.force)
    return run_worker_loop()


if __name__ == "__main__":
    raise SystemExit(main())
