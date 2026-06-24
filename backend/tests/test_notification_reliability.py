"""Notification worker reliability tests (Week 5 Day 31)."""

from __future__ import annotations

import uuid

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import NotificationStatus, NotificationType
from app.services.notification_processor import (
    ProcessingOutcome,
    poll_and_process_messages,
    process_notification_payload,
    process_received_messages,
)
from app.services.notification_service import create_notification
from app.services.queue import (
    build_notification_job_payload,
    enqueue_notification_delivery,
    get_sqs_client,
)
from tests.helpers import cleanup_user
from tests.test_schedule_integration import SHIFT_DATE
from tests.test_scheduling import _setup_org_scheduling
from tests.test_shift_swap import _create_give_up_request, published_employee_shift


def test_shift_swap_approval_notifies_requester(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    published_employee_shift: dict[str, str],
) -> None:
    swap = _create_give_up_request(
        client,
        org_id,
        published_employee_shift["employee_headers"],
        published_employee_shift["shift_id"],
    )

    client.patch(
        f"/organizations/{org_id}/shift-swap-requests/{swap['id']}/approve",
        headers=auth_headers,
    )

    response = client.get(
        f"/organizations/{org_id}/notifications/me",
        headers=published_employee_shift["employee_headers"],
    )
    assert response.status_code == 200
    assert any(item["type"] == "SHIFT_SWAP_APPROVED" for item in response.json()["items"])


def test_api_survives_sqs_enqueue_failure(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    mock_sqs: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import queue as queue_module

    def _raise_send_error(*_args, **_kwargs):
        raise ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "denied"}},
            "SendMessage",
        )

    monkeypatch.setattr(queue_module.get_sqs_client(), "send_message", _raise_send_error)

    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.TIME_OFF_APPROVED,
        title="Time off approved",
        message="Enjoy your time off.",
    )
    db.commit()

    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None
    assert enqueue_notification_delivery(notification) is False


def test_processor_marks_failed_with_error_message(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    no_sqs: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.SCHEDULE_PUBLISHED,
        title="Schedule published",
        message="Your schedule is ready.",
    )
    notification.status = NotificationStatus.PENDING
    db.commit()

    def _raise_delivery_error(_notification):
        raise RuntimeError("delivery failed")

    monkeypatch.setattr(
        "app.services.notification_processor._mark_notification_sent",
        _raise_delivery_error,
    )

    result = process_notification_payload(
        db,
        build_notification_job_payload(notification),
    )
    assert result.outcome == ProcessingOutcome.FAILED
    assert result.delete_message is True

    db.refresh(notification)
    assert notification.status == NotificationStatus.FAILED
    assert notification.error_message == "delivery failed"
    assert notification.retry_count == 1


def test_hard_failure_leaves_message_on_queue(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    no_sqs: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.OPEN_SHIFT_CREATED,
        title="Open shifts",
        message="Coverage needed.",
    )
    notification.status = NotificationStatus.PENDING
    db.commit()

    def _raise_delivery_error(_notification):
        raise RuntimeError("delivery failed")

    def _raise_failed_mark(*_args, **_kwargs):
        raise RuntimeError("cannot mark failed")

    monkeypatch.setattr(
        "app.services.notification_processor._mark_notification_sent",
        _raise_delivery_error,
    )
    monkeypatch.setattr(
        "app.services.notification_processor._mark_notification_failed",
        _raise_failed_mark,
    )

    result = process_notification_payload(
        db,
        build_notification_job_payload(notification),
    )
    assert result.outcome == ProcessingOutcome.FAILED
    assert result.delete_message is False


def test_poll_without_sqs_raises_clear_error(db: Session, no_sqs: None) -> None:
    with pytest.raises(RuntimeError, match="SQS is not configured"):
        poll_and_process_messages(db, wait_time_seconds=1)


def test_create_notification_without_sqs_does_not_crash_api(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    no_sqs: None,
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    request = client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=setup["employee_headers"],
        json={"start_date": SHIFT_DATE, "end_date": SHIFT_DATE, "reason": "Trip"},
    ).json()

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request['id']}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 200

    listed = client.get(
        f"/organizations/{org_id}/notifications/me",
        headers=setup["employee_headers"],
    )
    assert listed.status_code == 200
    assert listed.json()["unread_count"] >= 1

    cleanup_user(db, setup["employee_user_id"])


def test_schedule_publish_creates_pending_with_sqs_then_sent_after_worker(
    db: Session,
    org_id: str,
    registered_user: dict[str, str],
    mock_sqs: str,
) -> None:
    org_uuid = uuid.UUID(org_id)
    recipient_id = uuid.UUID(registered_user["id"])
    notification = create_notification(
        db,
        organization_id=org_uuid,
        recipient_user_id=recipient_id,
        notification_type=NotificationType.SCHEDULE_PUBLISHED,
        title="Schedule published",
        message="Week ready.",
    )
    db.commit()
    assert notification.status == NotificationStatus.PENDING

    client = get_sqs_client()
    messages = client.receive_message(
        QueueUrl=mock_sqs,
        MaxNumberOfMessages=5,
        WaitTimeSeconds=0,
    ).get("Messages", [])
    assert len(messages) == 1

    results = process_received_messages(db, messages)
    assert len(results) == 1
    assert results[0].outcome == ProcessingOutcome.SENT

    db.refresh(notification)
    assert notification.status == NotificationStatus.SENT
