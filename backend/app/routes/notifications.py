import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_org_member
from app.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import (
    get_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["notifications"])


@router.get("/notifications/me", response_model=NotificationListResponse)
def list_my_notifications(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    require_org_member(db, organization_id, current_user)
    notifications, unread_count = get_user_notifications(db, organization_id, current_user)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in notifications],
        unread_count=unread_count,
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def read_notification(
    organization_id: uuid.UUID,
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    require_org_member(db, organization_id, current_user)
    notification = mark_notification_read(db, organization_id, current_user, notification_id)
    return NotificationResponse.model_validate(notification)


@router.post("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
def read_all_notifications(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    require_org_member(db, organization_id, current_user)
    mark_all_notifications_read(db, organization_id, current_user)
