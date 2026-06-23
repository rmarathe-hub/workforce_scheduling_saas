import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationChannel, NotificationStatus, NotificationType


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    recipient_user_id: uuid.UUID
    type: NotificationType
    title: str
    message: str
    status: NotificationStatus
    channel: NotificationChannel
    entity_type: str | None
    entity_id: uuid.UUID | None
    created_at: datetime
    sent_at: datetime | None
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    unread_count: int
