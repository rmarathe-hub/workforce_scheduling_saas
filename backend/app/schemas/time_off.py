import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TimeOffStatus


class TimeOffRequestCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("end_date")
    @classmethod
    def end_on_or_after_start(cls, end_date: date, info) -> date:
        start_date = info.data.get("start_date")
        if start_date is not None and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        return end_date


class TimeOffRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    employee_id: uuid.UUID
    start_date: date
    end_date: date
    reason: str | None
    status: TimeOffStatus
    reviewed_by_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    employee_name: str | None = None
    reviewed_by_name: str | None = None


def time_off_request_to_response(request) -> TimeOffRequestResponse:
    return TimeOffRequestResponse(
        id=request.id,
        organization_id=request.organization_id,
        employee_id=request.employee_id,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason,
        status=request.status,
        reviewed_by_id=request.reviewed_by_id,
        created_at=request.created_at,
        updated_at=request.updated_at,
        employee_name=request.employee.full_name if request.employee else None,
        reviewed_by_name=request.reviewed_by.full_name if request.reviewed_by else None,
    )
