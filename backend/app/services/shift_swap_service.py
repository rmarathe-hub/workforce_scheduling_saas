"""Shift swap business logic and approval with conflict checks."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import AuditAction, ShiftStatus, ShiftSwapRequestType, ShiftSwapStatus
from app.models.shift import Shift
from app.models.shift_swap_request import ShiftSwapRequest
from app.schemas.shift_swap import ShiftSwapRequestCreate
from app.services.audit_service import log_audit_action
from app.services.org_validation import get_org_shift
from app.services.scheduling.conflict_service import get_week_conflicts


def _week_start_for_shift(shift: Shift) -> date:
    return shift.shift_date - timedelta(days=shift.shift_date.weekday())


def _load_swap_request(db: Session, request_id: uuid.UUID) -> ShiftSwapRequest:
    request = db.scalar(
        select(ShiftSwapRequest)
        .where(ShiftSwapRequest.id == request_id)
        .options(
            selectinload(ShiftSwapRequest.requester),
            selectinload(ShiftSwapRequest.target_employee),
            selectinload(ShiftSwapRequest.decided_by),
            selectinload(ShiftSwapRequest.original_shift).selectinload(Shift.location),
            selectinload(ShiftSwapRequest.original_shift).selectinload(Shift.job_role),
            selectinload(ShiftSwapRequest.requested_shift).selectinload(Shift.location),
            selectinload(ShiftSwapRequest.requested_shift).selectinload(Shift.job_role),
        )
    )
    assert request is not None
    return request


def _validate_shift_for_request(
    db: Session,
    organization_id: uuid.UUID,
    shift_id: uuid.UUID,
    *,
    expected_assignee_id: uuid.UUID | None = None,
) -> Shift:
    shift = get_org_shift(db, organization_id, shift_id)
    if shift.status != ShiftStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shift swap requests are only allowed for published shifts",
        )
    if expected_assignee_id is not None and shift.assignee_id != expected_assignee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You can only request swaps for shifts assigned to you",
        )
    return shift


def _ensure_no_pending_duplicate(
    db: Session,
    organization_id: uuid.UUID,
    original_shift_id: uuid.UUID,
) -> None:
    existing = db.scalar(
        select(ShiftSwapRequest).where(
            ShiftSwapRequest.organization_id == organization_id,
            ShiftSwapRequest.original_shift_id == original_shift_id,
            ShiftSwapRequest.status == ShiftSwapStatus.PENDING,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending swap request already exists for this shift",
        )


def create_shift_swap_request(
    db: Session,
    organization_id: uuid.UUID,
    requester_id: uuid.UUID,
    payload: ShiftSwapRequestCreate,
) -> ShiftSwapRequest:
    original_shift = _validate_shift_for_request(
        db,
        organization_id,
        payload.original_shift_id,
        expected_assignee_id=requester_id,
    )
    _ensure_no_pending_duplicate(db, organization_id, payload.original_shift_id)

    target_employee_id: uuid.UUID | None = None
    requested_shift: Shift | None = None

    if payload.request_type == ShiftSwapRequestType.SWAP:
        assert payload.requested_shift_id is not None
        if payload.requested_shift_id == payload.original_shift_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot swap a shift with itself",
            )

        requested_shift = _validate_shift_for_request(
            db, organization_id, payload.requested_shift_id
        )
        if requested_shift.assignee_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Swap target shift must be assigned to another employee",
            )
        if requested_shift.assignee_id == requester_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Swap target must be another employee's shift",
            )
        target_employee_id = requested_shift.assignee_id

    request = ShiftSwapRequest(
        organization_id=organization_id,
        requester_id=requester_id,
        target_employee_id=target_employee_id,
        original_shift_id=payload.original_shift_id,
        requested_shift_id=payload.requested_shift_id,
        request_type=payload.request_type,
        status=ShiftSwapStatus.PENDING,
        reason=payload.reason,
    )
    db.add(request)
    db.flush()
    log_audit_action(
        db,
        organization_id=organization_id,
        actor_user_id=requester_id,
        action=AuditAction.SHIFT_SWAP_REQUESTED,
        entity_type="shift_swap_request",
        entity_id=request.id,
        metadata={
            "request_type": payload.request_type.value,
            "original_shift_id": str(payload.original_shift_id),
            "requested_shift_id": (
                str(payload.requested_shift_id) if payload.requested_shift_id else None
            ),
        },
    )
    db.commit()
    return _load_swap_request(db, request.id)


def _conflicts_have_errors(
    db: Session, organization_id: uuid.UUID, week_start: date
) -> bool:
    _, summary = get_week_conflicts(db, organization_id, week_start)
    return summary["errors"] > 0


def _apply_approved_swap(db: Session, request: ShiftSwapRequest) -> list[Shift]:
    original_shift = get_org_shift(db, request.organization_id, request.original_shift_id)
    affected_shifts = [original_shift]

    if request.request_type == ShiftSwapRequestType.GIVE_UP:
        original_shift.assignee_id = None
    else:
        if request.requested_shift_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Swap request is missing a target shift",
            )
        requested_shift = get_org_shift(
            db, request.organization_id, request.requested_shift_id
        )
        affected_shifts.append(requested_shift)

        requester_id = request.requester_id
        target_id = requested_shift.assignee_id
        if target_id is None or target_id != request.target_employee_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Swap target shift assignment has changed",
            )
        if original_shift.assignee_id != requester_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Original shift assignment has changed",
            )

        original_shift.assignee_id = target_id
        requested_shift.assignee_id = requester_id

    db.flush()

    week_starts = {_week_start_for_shift(shift) for shift in affected_shifts}
    for week_start in week_starts:
        if _conflicts_have_errors(db, request.organization_id, week_start):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approving this swap would create scheduling conflicts",
            )

    return affected_shifts


def approve_shift_swap_request(
    db: Session,
    request: ShiftSwapRequest,
    decided_by_id: uuid.UUID,
) -> ShiftSwapRequest:
    if request.status != ShiftSwapStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be approved",
        )

    _apply_approved_swap(db, request)
    request.status = ShiftSwapStatus.APPROVED
    request.decided_by_id = decided_by_id
    request.decided_at = datetime.now(timezone.utc)
    log_audit_action(
        db,
        organization_id=request.organization_id,
        actor_user_id=decided_by_id,
        action=AuditAction.SHIFT_SWAP_APPROVED,
        entity_type="shift_swap_request",
        entity_id=request.id,
        metadata={"request_type": request.request_type.value},
    )
    db.commit()
    return _load_swap_request(db, request.id)


def reject_shift_swap_request(
    db: Session,
    request: ShiftSwapRequest,
    decided_by_id: uuid.UUID,
) -> ShiftSwapRequest:
    if request.status != ShiftSwapStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be rejected",
        )

    request.status = ShiftSwapStatus.REJECTED
    request.decided_by_id = decided_by_id
    request.decided_at = datetime.now(timezone.utc)
    log_audit_action(
        db,
        organization_id=request.organization_id,
        actor_user_id=decided_by_id,
        action=AuditAction.SHIFT_SWAP_REJECTED,
        entity_type="shift_swap_request",
        entity_id=request.id,
        metadata={"request_type": request.request_type.value},
    )
    db.commit()
    return _load_swap_request(db, request.id)


def cancel_shift_swap_request(
    db: Session,
    request: ShiftSwapRequest,
    requester_id: uuid.UUID,
) -> ShiftSwapRequest:
    if request.requester_id != requester_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    if request.status != ShiftSwapStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be cancelled",
        )

    request.status = ShiftSwapStatus.CANCELLED
    db.commit()
    return _load_swap_request(db, request.id)
