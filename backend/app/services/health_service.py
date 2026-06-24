"""Health and readiness checks for production observability."""

from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy import text

from app import config
from app.database import engine
from app.services.queue import is_sqs_configured
from app.services.s3_service import is_s3_configured

logger = logging.getLogger(__name__)

DatabaseStatus = Literal["ok", "error"]


def check_database() -> DatabaseStatus:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.exception("Database health check failed")
        return "error"


def build_health_status() -> dict[str, str | bool]:
    database = check_database()
    return {
        "status": "ok" if database == "ok" else "degraded",
        "database": database,
        "s3_configured": is_s3_configured(),
        "sqs_configured": is_sqs_configured(),
        "environment": config.settings.environment,
    }


def build_readiness_status() -> dict[str, str]:
    database = check_database()
    return {
        "status": "ready" if database == "ok" else "not_ready",
        "database": database,
    }
