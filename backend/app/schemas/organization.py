import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MembershipRole


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(default="America/New_York", min_length=1, max_length=64)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    timezone: str
    created_at: datetime


class OrganizationMembershipResponse(BaseModel):
    organization: OrganizationResponse
    role: MembershipRole
