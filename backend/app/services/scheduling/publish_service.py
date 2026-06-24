"""Publish draft schedules after conflict validation."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import ShiftStatus
from app.models.shift import Shift
from app.services.org_validation import get_week_end
from app.services.scheduling.conflict_detector import Conflict, ConflictSeverity
from app.services.scheduling.conflict_service import get_week_conflicts

logger = logging.getLogger(__name__)


@dataclass
class PublishWeekResult:
    week_start: date
    week_end: date
    published_shift_count: int
    warnings: list[str]


def derive_week_schedule_status(shifts: list[Shift]) -> str:
    if not shifts:
        return "empty"
    if any(shift.status == ShiftStatus.DRAFT for shift in shifts):
        return "draft"
    if all(shift.status == ShiftStatus.PUBLISHED for shift in shifts):
        return "published"
    return "draft"


def publish_week_schedule(
    db: Session,
    organization_id: uuid.UUID,
    week_start: date,
) -> PublishWeekResult:
    week_end = get_week_end(week_start)
    conflicts, summary = get_week_conflicts(db, organization_id, week_start)

    if summary["errors"] > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Cannot publish schedule with blocking conflicts",
                "summary": summary,
                "conflicts": [_conflict_payload(conflict) for conflict in conflicts],
            },
        )

    draft_shifts = db.scalars(
        select(Shift).where(
            Shift.organization_id == organization_id,
            Shift.shift_date >= week_start,
            Shift.shift_date <= week_end,
            Shift.status == ShiftStatus.DRAFT,
        )
    ).all()

    if not draft_shifts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No draft shifts to publish for this week",
        )

    for shift in draft_shifts:
        shift.status = ShiftStatus.PUBLISHED

    db.commit()

    logger.info(
        "Published week schedule organization_id=%s week_start=%s published_shift_count=%s",
        organization_id,
        week_start.isoformat(),
        len(draft_shifts),
    )

    warnings = [
        conflict.message
        for conflict in conflicts
        if conflict.severity in {ConflictSeverity.WARNING, ConflictSeverity.INFO}
    ]

    return PublishWeekResult(
        week_start=week_start,
        week_end=week_end,
        published_shift_count=len(draft_shifts),
        warnings=warnings,
    )


def _conflict_payload(conflict: Conflict) -> dict[str, str | None]:
    return {
        "type": conflict.type.value,
        "severity": conflict.severity.value,
        "message": conflict.message,
        "shift_id": str(conflict.shift_id) if conflict.shift_id else None,
        "employee_id": str(conflict.employee_id) if conflict.employee_id else None,
        "coverage_requirement_id": (
            str(conflict.coverage_requirement_id) if conflict.coverage_requirement_id else None
        ),
    }
