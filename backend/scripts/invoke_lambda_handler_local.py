#!/usr/bin/env python3
"""Invoke the SQS notification Lambda handler locally with a JSON event file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.lambda_handlers.sqs_notification_handler import handle_sqs_event


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "event_file",
        nargs="?",
        default=str(BACKEND_ROOT / "tests/fixtures/sqs_lambda_event.json"),
        help="Path to an AWS SQS Lambda event JSON payload",
    )
    args = parser.parse_args()

    event_path = Path(args.event_file)
    event = json.loads(event_path.read_text())
    response = handle_sqs_event(event, None)
    print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
