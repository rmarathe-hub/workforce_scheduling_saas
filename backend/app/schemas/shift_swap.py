import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ShiftSwapRequestType, ShiftSwapStatus


class ShiftSwapRequestCreate(BaseModel):
    request_type: ShiftSwapRequestType
    original_shift_id: uuid.UUID
    requested_shift_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_swap_fields(self) -> "ShiftSwapRequestCreate":
        if self.request_type == ShiftSwapRequestType.GIVE_UP:
            if self.requested_shift_id is not None:
                raise ValueError("requested_shift_id must be omitted for give-up requests")
        elif self.request_type == ShiftSwapRequestType.SWAP:
            if self.requested_shift_id is None:
                raise ValueError("requested_shift_id is required for swap requests")
        return self


class ShiftSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    shift_date: date
    start_time: time
    end_time: time
    assignee_id: uuid.UUID | None
    status: str
    location_name: str | None = None
    job_role_name: str | None = None


class ShiftSwapRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    requester_id: uuid.UUID
    target_employee_id: uuid.UUID | None
    original_shift_id: uuid.UUID
    requested_shift_id: uuid.UUID | None
    request_type: ShiftSwapRequestType
    status: ShiftSwapStatus
    reason: str | None
    decided_by_id: uuid.UUID | None
    created_at: datetime
    decided_at: datetime | None
    requester_name: str | None = None
    target_employee_name: str | None = None
    decided_by_name: str | None = None
    original_shift: ShiftSummary | None = None
    requested_shift: ShiftSummary | None = None


def _shift_summary(shift) -> ShiftSummary | None:
    if shift is None:
        return None
    return ShiftSummary(
        id=shift.id,
        shift_date=shift.shift_date,
        start_time=shift.start_time,
        end_time=shift.end_time,
        assignee_id=shift.assignee_id,
        status=shift.status.value,
        location_name=shift.location.name if shift.location else None,
        job_role_name=shift.job_role.name if shift.job_role else None,
    )


def shift_swap_request_to_response(request) -> ShiftSwapRequestResponse:
    return ShiftSwapRequestResponse(
        id=request.id,
        organization_id=request.organization_id,
        requester_id=request.requester_id,
        target_employee_id=request.target_employee_id,
        original_shift_id=request.original_shift_id,
        requested_shift_id=request.requested_shift_id,
        request_type=request.request_type,
        status=request.status,
        reason=request.reason,
        decided_by_id=request.decided_by_id,
        created_at=request.created_at,
        decided_at=request.decided_at,
        requester_name=request.requester.full_name if request.requester else None,
        target_employee_name=(
            request.target_employee.full_name if request.target_employee else None
        ),
        decided_by_name=request.decided_by.full_name if request.decided_by else None,
        original_shift=_shift_summary(request.original_shift),
        requested_shift=_shift_summary(request.requested_shift),
    )
