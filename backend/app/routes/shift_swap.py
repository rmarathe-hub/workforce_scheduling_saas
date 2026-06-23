import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_min_role
from app.database import get_db
from app.models.enums import MembershipRole, ShiftSwapStatus
from app.models.shift import Shift
from app.models.shift_swap_request import ShiftSwapRequest
from app.models.user import User
from app.schemas.shift_swap import (
    ShiftSwapRequestCreate,
    ShiftSwapRequestResponse,
    shift_swap_request_to_response,
)
from app.services.shift_swap_service import (
    approve_shift_swap_request,
    cancel_shift_swap_request,
    create_shift_swap_request,
    reject_shift_swap_request,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["shift-swaps"])


def _swap_load_options():
    return (
        selectinload(ShiftSwapRequest.requester),
        selectinload(ShiftSwapRequest.target_employee),
        selectinload(ShiftSwapRequest.decided_by),
        selectinload(ShiftSwapRequest.original_shift).selectinload(Shift.location),
        selectinload(ShiftSwapRequest.original_shift).selectinload(Shift.job_role),
        selectinload(ShiftSwapRequest.requested_shift).selectinload(Shift.location),
        selectinload(ShiftSwapRequest.requested_shift).selectinload(Shift.job_role),
    )


def _get_request(
    db: Session, organization_id: uuid.UUID, request_id: uuid.UUID
) -> ShiftSwapRequest:
    request = db.scalar(
        select(ShiftSwapRequest)
        .where(
            ShiftSwapRequest.id == request_id,
            ShiftSwapRequest.organization_id == organization_id,
        )
        .options(*_swap_load_options())
    )
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift swap request not found",
        )
    return request


@router.post(
    "/shift-swap-requests",
    response_model=ShiftSwapRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_swap_request(
    organization_id: uuid.UUID,
    payload: ShiftSwapRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShiftSwapRequestResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)
    request = create_shift_swap_request(db, organization_id, current_user.id, payload)
    return shift_swap_request_to_response(request)


@router.get("/shift-swap-requests/me", response_model=list[ShiftSwapRequestResponse])
def get_my_swap_requests(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ShiftSwapRequestResponse]:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)

    requests = db.scalars(
        select(ShiftSwapRequest)
        .where(
            ShiftSwapRequest.organization_id == organization_id,
            ShiftSwapRequest.requester_id == current_user.id,
        )
        .options(*_swap_load_options())
        .order_by(ShiftSwapRequest.created_at.desc())
    ).all()
    return [shift_swap_request_to_response(request) for request in requests]


@router.get("/shift-swap-requests", response_model=list[ShiftSwapRequestResponse])
def list_swap_requests(
    organization_id: uuid.UUID,
    status_filter: ShiftSwapStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ShiftSwapRequestResponse]:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)

    query = (
        select(ShiftSwapRequest)
        .where(ShiftSwapRequest.organization_id == organization_id)
        .options(*_swap_load_options())
        .order_by(ShiftSwapRequest.created_at.desc())
    )
    if status_filter is not None:
        query = query.where(ShiftSwapRequest.status == status_filter)

    requests = db.scalars(query).all()
    return [shift_swap_request_to_response(request) for request in requests]


@router.patch(
    "/shift-swap-requests/{request_id}/approve",
    response_model=ShiftSwapRequestResponse,
)
def approve_swap_request(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShiftSwapRequestResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    request = _get_request(db, organization_id, request_id)

    if request.requester_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot approve your own swap request",
        )

    request = approve_shift_swap_request(db, request, current_user.id)
    return shift_swap_request_to_response(request)


@router.patch(
    "/shift-swap-requests/{request_id}/reject",
    response_model=ShiftSwapRequestResponse,
)
def reject_swap_request(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShiftSwapRequestResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    request = _get_request(db, organization_id, request_id)
    request = reject_shift_swap_request(db, request, current_user.id)
    return shift_swap_request_to_response(request)


@router.patch(
    "/shift-swap-requests/{request_id}/cancel",
    response_model=ShiftSwapRequestResponse,
)
def cancel_swap_request(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShiftSwapRequestResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)
    request = _get_request(db, organization_id, request_id)
    request = cancel_shift_swap_request(db, request, current_user.id)
    return shift_swap_request_to_response(request)
