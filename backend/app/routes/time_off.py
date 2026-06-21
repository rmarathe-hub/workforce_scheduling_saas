import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_min_role
from app.database import get_db
from app.models.enums import MembershipRole, TimeOffStatus
from app.models.time_off_request import TimeOffRequest
from app.models.user import User
from app.schemas.time_off import (
    TimeOffRequestCreate,
    TimeOffRequestResponse,
    time_off_request_to_response,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["time-off"])


def _get_request(
    db: Session, organization_id: uuid.UUID, request_id: uuid.UUID
) -> TimeOffRequest:
    request = db.scalar(
        select(TimeOffRequest)
        .where(
            TimeOffRequest.id == request_id,
            TimeOffRequest.organization_id == organization_id,
        )
        .options(
            selectinload(TimeOffRequest.employee),
            selectinload(TimeOffRequest.reviewed_by),
        )
    )
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Time-off request not found")
    return request


def _load_request(db: Session, request_id: uuid.UUID) -> TimeOffRequest:
    request = db.scalar(
        select(TimeOffRequest)
        .where(TimeOffRequest.id == request_id)
        .options(
            selectinload(TimeOffRequest.employee),
            selectinload(TimeOffRequest.reviewed_by),
        )
    )
    assert request is not None
    return request


@router.post(
    "/time-off-requests",
    response_model=TimeOffRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_time_off_request(
    organization_id: uuid.UUID,
    payload: TimeOffRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TimeOffRequestResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)

    request = TimeOffRequest(
        organization_id=organization_id,
        employee_id=current_user.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        status=TimeOffStatus.PENDING,
    )
    db.add(request)
    db.commit()
    return time_off_request_to_response(_load_request(db, request.id))


@router.get("/time-off-requests/me", response_model=list[TimeOffRequestResponse])
def get_my_time_off_requests(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TimeOffRequestResponse]:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)

    requests = db.scalars(
        select(TimeOffRequest)
        .where(
            TimeOffRequest.organization_id == organization_id,
            TimeOffRequest.employee_id == current_user.id,
        )
        .options(
            selectinload(TimeOffRequest.employee),
            selectinload(TimeOffRequest.reviewed_by),
        )
        .order_by(TimeOffRequest.created_at.desc())
    ).all()
    return [time_off_request_to_response(request) for request in requests]


@router.get("/time-off-requests", response_model=list[TimeOffRequestResponse])
def list_time_off_requests(
    organization_id: uuid.UUID,
    status_filter: TimeOffStatus | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TimeOffRequestResponse]:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)

    query = (
        select(TimeOffRequest)
        .where(TimeOffRequest.organization_id == organization_id)
        .options(
            selectinload(TimeOffRequest.employee),
            selectinload(TimeOffRequest.reviewed_by),
        )
        .order_by(TimeOffRequest.created_at.desc())
    )
    if status_filter is not None:
        query = query.where(TimeOffRequest.status == status_filter)

    requests = db.scalars(query).all()
    return [time_off_request_to_response(request) for request in requests]


@router.patch(
    "/time-off-requests/{request_id}/approve",
    response_model=TimeOffRequestResponse,
)
def approve_time_off_request(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TimeOffRequestResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    request = _get_request(db, organization_id, request_id)

    if request.status != TimeOffStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be approved",
        )

    request.status = TimeOffStatus.APPROVED
    request.reviewed_by_id = current_user.id
    db.commit()
    return time_off_request_to_response(_load_request(db, request.id))


@router.patch(
    "/time-off-requests/{request_id}/reject",
    response_model=TimeOffRequestResponse,
)
def reject_time_off_request(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TimeOffRequestResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    request = _get_request(db, organization_id, request_id)

    if request.status != TimeOffStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be rejected",
        )

    request.status = TimeOffStatus.REJECTED
    request.reviewed_by_id = current_user.id
    db.commit()
    return time_off_request_to_response(_load_request(db, request.id))


@router.patch(
    "/time-off-requests/{request_id}/cancel",
    response_model=TimeOffRequestResponse,
)
def cancel_time_off_request(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TimeOffRequestResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)
    request = _get_request(db, organization_id, request_id)

    if request.employee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    if request.status != TimeOffStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be cancelled",
        )

    request.status = TimeOffStatus.CANCELLED
    db.commit()
    return time_off_request_to_response(_load_request(db, request.id))
