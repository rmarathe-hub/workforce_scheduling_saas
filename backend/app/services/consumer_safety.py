"""Guards against running local SQS consumers alongside production Lambda."""

from __future__ import annotations

import sys

from app import config
from app.services.queue import is_sqs_configured

_PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})


def is_production_consumer_context() -> bool:
    """True when local scripts would compete with the deployed Lambda consumer."""
    return (
        config.settings.environment.strip().lower() in _PRODUCTION_ENVIRONMENTS
        and is_sqs_configured()
    )


def assert_local_consumer_allowed(*, force: bool = False) -> None:
    """Exit unless it is safe to poll the configured SQS queue from this machine."""
    if force or not is_production_consumer_context():
        return

    print(
        "Refusing to start a local SQS consumer: ENVIRONMENT is production and "
        "SQS_NOTIFICATION_QUEUE_URL is configured.\n"
        "Production uses AWS Lambda (shiftops-notification-consumer). Running "
        "notification_worker.py or process_notifications_once.py here would compete "
        "with Lambda and can duplicate deliveries.\n"
        "Use local/dev ENVIRONMENT with a dev queue, or pass --force only for "
        "emergency debugging when Lambda is disabled.",
        file=sys.stderr,
    )
    raise SystemExit(2)
