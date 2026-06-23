import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AuditAction


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    actor_user_id: uuid.UUID
    action: AuditAction
    entity_type: str
    entity_id: uuid.UUID
    metadata: dict[str, Any] | None = None
    created_at: datetime
    actor_name: str | None = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int


def audit_log_to_response(entry) -> AuditLogResponse:
    return AuditLogResponse(
        id=entry.id,
        organization_id=entry.organization_id,
        actor_user_id=entry.actor_user_id,
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        metadata=entry.metadata_json,
        created_at=entry.created_at,
        actor_name=entry.actor.full_name if entry.actor else None,
    )
