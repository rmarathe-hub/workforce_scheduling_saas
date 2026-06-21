import uuid
from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class AvailabilityWindowCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time: time, info) -> time:
        start_time = info.data.get("start_time")
        if start_time is not None and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class AvailabilityWindowUpdate(BaseModel):
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time: time | None, info) -> time | None:
        if end_time is None:
            return end_time
        start_time = info.data.get("start_time")
        if start_time is not None and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class AvailabilityWindowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    employee_id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    created_at: datetime
    day_name: str | None = None


def availability_window_to_response(window) -> AvailabilityWindowResponse:
    return AvailabilityWindowResponse(
        id=window.id,
        organization_id=window.organization_id,
        employee_id=window.employee_id,
        day_of_week=window.day_of_week,
        start_time=window.start_time,
        end_time=window.end_time,
        created_at=window.created_at,
        day_name=DAY_NAMES[window.day_of_week],
    )
