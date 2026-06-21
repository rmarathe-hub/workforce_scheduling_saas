import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_min_role
from app.database import get_db
from app.models.availability_window import AvailabilityWindow
from app.models.enums import MembershipRole
from app.models.membership import OrganizationMembership
from app.models.user import User
from app.schemas.availability import (
    AvailabilityWindowCreate,
    AvailabilityWindowResponse,
    AvailabilityWindowUpdate,
    availability_window_to_response,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["availability"])


def _get_window(
    db: Session, organization_id: uuid.UUID, window_id: uuid.UUID
) -> AvailabilityWindow:
    window = db.scalar(
        select(AvailabilityWindow).where(
            AvailabilityWindow.id == window_id,
            AvailabilityWindow.organization_id == organization_id,
        )
    )
    if window is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Availability not found")
    return window


def _ensure_employee_in_org(
    db: Session, organization_id: uuid.UUID, employee_id: uuid.UUID
) -> OrganizationMembership:
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == employee_id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in this organization",
        )
    return membership


@router.post(
    "/availability",
    response_model=AvailabilityWindowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability(
    organization_id: uuid.UUID,
    payload: AvailabilityWindowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AvailabilityWindowResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)

    window = AvailabilityWindow(
        organization_id=organization_id,
        employee_id=current_user.id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(window)
    db.commit()
    db.refresh(window)
    return availability_window_to_response(window)


@router.get("/availability/me", response_model=list[AvailabilityWindowResponse])
def get_my_availability(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AvailabilityWindowResponse]:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)

    windows = db.scalars(
        select(AvailabilityWindow)
        .where(
            AvailabilityWindow.organization_id == organization_id,
            AvailabilityWindow.employee_id == current_user.id,
        )
        .order_by(AvailabilityWindow.day_of_week, AvailabilityWindow.start_time)
    ).all()
    return [availability_window_to_response(window) for window in windows]


@router.get(
    "/employees/{employee_id}/availability",
    response_model=list[AvailabilityWindowResponse],
)
def get_employee_availability(
    organization_id: uuid.UUID,
    employee_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AvailabilityWindowResponse]:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    _ensure_employee_in_org(db, organization_id, employee_id)

    windows = db.scalars(
        select(AvailabilityWindow)
        .where(
            AvailabilityWindow.organization_id == organization_id,
            AvailabilityWindow.employee_id == employee_id,
        )
        .order_by(AvailabilityWindow.day_of_week, AvailabilityWindow.start_time)
    ).all()
    return [availability_window_to_response(window) for window in windows]


@router.patch("/availability/{window_id}", response_model=AvailabilityWindowResponse)
def update_availability(
    organization_id: uuid.UUID,
    window_id: uuid.UUID,
    payload: AvailabilityWindowUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AvailabilityWindowResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)
    window = _get_window(db, organization_id, window_id)

    if window.employee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    if payload.day_of_week is not None:
        window.day_of_week = payload.day_of_week
    if payload.start_time is not None:
        window.start_time = payload.start_time
    if payload.end_time is not None:
        window.end_time = payload.end_time

    if window.end_time <= window.start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_time must be after start_time",
        )

    db.commit()
    db.refresh(window)
    return availability_window_to_response(window)


@router.delete("/availability/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_availability(
    organization_id: uuid.UUID,
    window_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)
    window = _get_window(db, organization_id, window_id)

    if window.employee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    db.delete(window)
    db.commit()
