import uuid
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ShiftStatus
from app.schemas.job_role import JobRoleResponse
from app.schemas.location import LocationResponse


class CoverageRequirementCreate(BaseModel):
    location_id: uuid.UUID
    job_role_id: uuid.UUID
    shift_date: date
    week_start: date
    start_time: time
    end_time: time
    headcount: int = Field(default=1, ge=1, le=50)

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time: time, info) -> time:
        start_time = info.data.get("start_time")
        if start_time is not None and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class CoverageRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    location_id: uuid.UUID
    job_role_id: uuid.UUID
    shift_date: date
    week_start: date
    start_time: time
    end_time: time
    headcount: int
    created_at: datetime
    location: LocationResponse | None = None
    job_role: JobRoleResponse | None = None


class ShiftCreate(BaseModel):
    location_id: uuid.UUID
    job_role_id: uuid.UUID
    shift_date: date
    start_time: time
    end_time: time
    coverage_requirement_id: uuid.UUID | None = None
    assignee_id: uuid.UUID | None = None

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end_time: time, info) -> time:
        start_time = info.data.get("start_time")
        if start_time is not None and end_time <= start_time:
            raise ValueError("end_time must be after start_time")
        return end_time


class ShiftAssign(BaseModel):
    assignee_id: uuid.UUID


class ShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    coverage_requirement_id: uuid.UUID | None
    location_id: uuid.UUID
    job_role_id: uuid.UUID
    shift_date: date
    start_time: time
    end_time: time
    assignee_id: uuid.UUID | None
    status: ShiftStatus
    created_at: datetime
    location: LocationResponse | None = None
    job_role: JobRoleResponse | None = None
    assignee_name: str | None = None


class WeekScheduleResponse(BaseModel):
    week_start: date
    week_end: date
    schedule_status: str
    coverage_requirements: list[CoverageRequirementResponse]
    shifts: list[ShiftResponse]


class ConflictResponse(BaseModel):
    type: str
    severity: str
    message: str
    shift_id: uuid.UUID | None = None
    employee_id: uuid.UUID | None = None
    coverage_requirement_id: uuid.UUID | None = None


class ConflictSummaryResponse(BaseModel):
    total: int
    errors: int
    warnings: int
    info: int


class WeekConflictsResponse(BaseModel):
    week_start: date
    week_end: date
    summary: ConflictSummaryResponse
    conflicts: list[ConflictResponse]


class ValidateWeekResponse(BaseModel):
    week_start: date
    week_end: date
    valid: bool
    summary: ConflictSummaryResponse
    conflicts: list[ConflictResponse]


class ValidateShiftResponse(BaseModel):
    shift_id: uuid.UUID
    valid: bool
    conflicts: list[ConflictResponse]


class GenerateWeekScheduleResponse(BaseModel):
    week_start: date
    week_end: date
    assigned_count: int
    open_shift_count: int
    conflict_count: int
    conflict_summary: ConflictSummaryResponse
    warnings: list[str]
    shifts: list[ShiftResponse]


class PublishWeekScheduleResponse(BaseModel):
    week_start: date
    week_end: date
    status: str
    published_shift_count: int
    warnings: list[str]


class WeekScheduleStatusResponse(BaseModel):
    week_start: date
    week_end: date
    schedule_status: str
    draft_shift_count: int
    published_shift_count: int
