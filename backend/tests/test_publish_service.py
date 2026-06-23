"""Unit tests for publish_service status derivation and publish rules."""

import uuid
from datetime import date, time

import pytest
from fastapi import HTTPException

from app.models.enums import ShiftStatus
from app.models.shift import Shift
from app.services.scheduling.publish_service import derive_week_schedule_status, publish_week_schedule


def _shift(status: ShiftStatus) -> Shift:
    return Shift(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        job_role_id=uuid.uuid4(),
        shift_date=date(2026, 6, 2),
        start_time=time(9, 0),
        end_time=time(17, 0),
        status=status,
    )


def test_derive_week_schedule_status_empty() -> None:
    assert derive_week_schedule_status([]) == "empty"


def test_derive_week_schedule_status_draft() -> None:
    assert derive_week_schedule_status([_shift(ShiftStatus.DRAFT)]) == "draft"


def test_derive_week_schedule_status_published() -> None:
    assert derive_week_schedule_status([_shift(ShiftStatus.PUBLISHED)]) == "published"


def test_derive_week_schedule_status_mixed_defaults_to_draft() -> None:
    shifts = [_shift(ShiftStatus.PUBLISHED), _shift(ShiftStatus.DRAFT)]
    assert derive_week_schedule_status(shifts) == "draft"


def test_publish_week_schedule_raises_when_no_draft_shifts(
    db, org_id: str
) -> None:
    from tests.test_scheduling import WEEK_START

    with pytest.raises(HTTPException) as exc_info:
        publish_week_schedule(db, uuid.UUID(org_id), date.fromisoformat(WEEK_START))
    assert exc_info.value.status_code == 400
    assert "No draft shifts" in str(exc_info.value.detail)
