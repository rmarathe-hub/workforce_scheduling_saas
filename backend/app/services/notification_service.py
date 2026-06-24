"""Create and manage in-app user notifications."""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import MembershipRole, NotificationChannel, NotificationStatus, NotificationType
from app.models.membership import OrganizationMembership
from app.models.notification import Notification
from app.models.user import User
from app.services.queue import JOB_TYPE_SEND_NOTIFICATION, enqueue_notification_delivery

logger = logging.getLogger(__name__)

_VISIBLE_STATUSES = (NotificationStatus.SENT, NotificationStatus.READ)


def _mark_notification_sent(notification: Notification) -> None:
    now = datetime.now(timezone.utc)
    notification.status = NotificationStatus.SENT
    notification.sent_at = now


def create_notification(
    db: Session,
    *,
    organization_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    channel: NotificationChannel = NotificationChannel.IN_APP,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> Notification:
    notification = Notification(
        organization_id=organization_id,
        recipient_user_id=recipient_user_id,
        type=notification_type,
        title=title,
        message=message,
        status=NotificationStatus.PENDING,
        channel=channel,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(notification)
    db.flush()

    if channel == NotificationChannel.IN_APP:
        if not enqueue_notification_delivery(notification):
            logger.warning(
                "Falling back to immediate in-app delivery notification_id=%s "
                "(SQS not configured or enqueue failed)",
                notification.id,
            )
            _mark_notification_sent(notification)

    return notification


def deliver_notification_from_queue(
    db: Session,
    notification_id: uuid.UUID,
) -> Notification | None:
    """Backward-compatible wrapper around the shared notification processor."""
    from app.services.notification_processor import (
        ProcessingOutcome,
        process_notification_payload,
    )

    result = process_notification_payload(
        db,
        {
            "type": JOB_TYPE_SEND_NOTIFICATION,
            "notification_id": str(notification_id),
        },
    )
    if result.notification_id is None:
        return None
    if result.outcome == ProcessingOutcome.NOT_FOUND:
        return None
    return db.get(Notification, result.notification_id)


def _get_org_manager_user_ids(db: Session, organization_id: uuid.UUID) -> list[uuid.UUID]:
    rows = db.scalars(
        select(OrganizationMembership.user_id).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role.in_(
                [MembershipRole.OWNER, MembershipRole.MANAGER]
            ),
        )
    ).all()
    return list(rows)


def notify_managers(
    db: Session,
    *,
    organization_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> list[Notification]:
    notifications: list[Notification] = []
    for user_id in _get_org_manager_user_ids(db, organization_id):
        notifications.append(
            create_notification(
                db,
                organization_id=organization_id,
                recipient_user_id=user_id,
                notification_type=notification_type,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )
    return notifications


def notify_schedule_published(
    db: Session,
    *,
    organization_id: uuid.UUID,
    week_start: date,
    assignee_ids: set[uuid.UUID],
) -> list[Notification]:
    notifications: list[Notification] = []
    week_label = week_start.isoformat()
    for assignee_id in assignee_ids:
        notifications.append(
            create_notification(
                db,
                organization_id=organization_id,
                recipient_user_id=assignee_id,
                notification_type=NotificationType.SCHEDULE_PUBLISHED,
                title="Schedule published",
                message=f"Your schedule for the week of {week_label} has been published.",
                entity_type="schedule",
                entity_id=organization_id,
            )
        )
    return notifications


def notify_open_shifts_created(
    db: Session,
    *,
    organization_id: uuid.UUID,
    week_start: date,
    open_shift_count: int,
) -> list[Notification]:
    if open_shift_count <= 0:
        return []
    return notify_managers(
        db,
        organization_id=organization_id,
        notification_type=NotificationType.OPEN_SHIFT_CREATED,
        title="Open shifts need coverage",
        message=(
            f"{open_shift_count} open shift{'s' if open_shift_count != 1 else ''} "
            f"were created for the week of {week_start.isoformat()}."
        ),
        entity_type="schedule",
        entity_id=organization_id,
    )


def get_user_notifications(
    db: Session,
    organization_id: uuid.UUID,
    user: User,
) -> tuple[list[Notification], int]:
    notifications = list(
        db.scalars(
            select(Notification)
            .where(
                Notification.organization_id == organization_id,
                Notification.recipient_user_id == user.id,
                Notification.status.in_(_VISIBLE_STATUSES),
            )
            .order_by(Notification.created_at.desc())
        ).all()
    )

    unread_count = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.organization_id == organization_id,
            Notification.recipient_user_id == user.id,
            Notification.read_at.is_(None),
            Notification.status == NotificationStatus.SENT,
        )
    )
    assert unread_count is not None
    return notifications, unread_count


def mark_notification_read(
    db: Session,
    organization_id: uuid.UUID,
    user: User,
    notification_id: uuid.UUID,
) -> Notification:
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.organization_id == organization_id,
            Notification.recipient_user_id == user.id,
        )
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        notification.status = NotificationStatus.READ
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_notifications_read(
    db: Session,
    organization_id: uuid.UUID,
    user: User,
) -> int:
    now = datetime.now(timezone.utc)
    notifications = db.scalars(
        select(Notification).where(
            Notification.organization_id == organization_id,
            Notification.recipient_user_id == user.id,
            Notification.read_at.is_(None),
        )
    ).all()
    for notification in notifications:
        notification.read_at = now
        notification.status = NotificationStatus.READ
    db.commit()
    return len(notifications)
