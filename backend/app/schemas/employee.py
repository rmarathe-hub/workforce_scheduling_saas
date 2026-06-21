import uuid

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import MembershipRole
from app.schemas.job_role import JobRoleResponse
from app.schemas.location import LocationResponse


class MemberCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    membership_role: MembershipRole
    location_id: uuid.UUID | None = None
    job_role_ids: list[uuid.UUID] = Field(default_factory=list)
    job_title: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_membership_role(self) -> "MemberCreate":
        if self.membership_role == MembershipRole.OWNER:
            raise ValueError("Cannot assign OWNER role via member invite")
        return self


class EmployeeResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    membership_role: MembershipRole
    location: LocationResponse | None
    job_title: str | None
    job_roles: list[JobRoleResponse]
