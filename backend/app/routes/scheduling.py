import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_min_role
from app.database import get_db
from app.models.coverage_requirement import CoverageRequirement
from app.models.enums import MembershipRole, ShiftStatus
from app.models.shift import Shift
from app.models.user import User
from app.schemas.scheduling import (
    CoverageRequirementCreate,
    CoverageRequirementResponse,
    ShiftAssign,
    ShiftCreate,
    ShiftResponse,
    WeekScheduleResponse,
)
from app.services.org_validation import (
    get_assignable_employee,
    get_org_coverage_requirement,
    get_org_job_role,
    get_org_location,
    get_org_shift,
    get_week_end,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["scheduling"])


def _shift_to_response(shift: Shift) -> ShiftResponse:
    return ShiftResponse(
        id=shift.id,
        organization_id=shift.organization_id,
        coverage_requirement_id=shift.coverage_requirement_id,
        location_id=shift.location_id,
        job_role_id=shift.job_role_id,
        shift_date=shift.shift_date,
        start_time=shift.start_time,
        end_time=shift.end_time,
        assignee_id=shift.assignee_id,
        status=shift.status,
        created_at=shift.created_at,
        location=shift.location,
        job_role=shift.job_role,
        assignee_name=shift.assignee.full_name if shift.assignee else None,
    )


def _load_shift(db: Session, shift_id: uuid.UUID) -> Shift:
    shift = db.scalar(
        select(Shift)
        .where(Shift.id == shift_id)
        .options(
            selectinload(Shift.location),
            selectinload(Shift.job_role),
            selectinload(Shift.assignee),
        )
    )
    assert shift is not None
    return shift


@router.post(
    "/coverage-requirements",
    response_model=CoverageRequirementResponse,
    status_code=201,
)
def create_coverage_requirement(
    organization_id: uuid.UUID,
    payload: CoverageRequirementCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoverageRequirement:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    get_org_location(db, organization_id, payload.location_id)
    get_org_job_role(db, organization_id, payload.job_role_id)

    requirement = CoverageRequirement(
        organization_id=organization_id,
        location_id=payload.location_id,
        job_role_id=payload.job_role_id,
        shift_date=payload.shift_date,
        week_start=payload.week_start,
        start_time=payload.start_time,
        end_time=payload.end_time,
        headcount=payload.headcount,
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)

    requirement = db.scalar(
        select(CoverageRequirement)
        .where(CoverageRequirement.id == requirement.id)
        .options(
            selectinload(CoverageRequirement.location),
            selectinload(CoverageRequirement.job_role),
        )
    )
    assert requirement is not None
    return requirement


@router.get("/schedules/{week_start}", response_model=WeekScheduleResponse)
def get_week_schedule(
    organization_id: uuid.UUID,
    week_start: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeekScheduleResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)
    week_end = get_week_end(week_start)

    requirements = db.scalars(
        select(CoverageRequirement)
        .where(
            CoverageRequirement.organization_id == organization_id,
            CoverageRequirement.week_start == week_start,
        )
        .options(
            selectinload(CoverageRequirement.location),
            selectinload(CoverageRequirement.job_role),
        )
        .order_by(CoverageRequirement.shift_date, CoverageRequirement.start_time)
    ).all()

    shifts = db.scalars(
        select(Shift)
        .where(
            Shift.organization_id == organization_id,
            Shift.shift_date >= week_start,
            Shift.shift_date <= week_end,
        )
        .options(
            selectinload(Shift.location),
            selectinload(Shift.job_role),
            selectinload(Shift.assignee),
        )
        .order_by(Shift.shift_date, Shift.start_time)
    ).all()

    return WeekScheduleResponse(
        week_start=week_start,
        week_end=week_end,
        coverage_requirements=list(requirements),
        shifts=[_shift_to_response(shift) for shift in shifts],
    )


@router.post("/shifts", response_model=ShiftResponse, status_code=201)
def create_shift(
    organization_id: uuid.UUID,
    payload: ShiftCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShiftResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    get_org_location(db, organization_id, payload.location_id)
    get_org_job_role(db, organization_id, payload.job_role_id)

    if payload.coverage_requirement_id is not None:
        get_org_coverage_requirement(db, organization_id, payload.coverage_requirement_id)

    if payload.assignee_id is not None:
        get_assignable_employee(
            db, organization_id, payload.assignee_id, payload.job_role_id
        )

    shift = Shift(
        organization_id=organization_id,
        coverage_requirement_id=payload.coverage_requirement_id,
        location_id=payload.location_id,
        job_role_id=payload.job_role_id,
        shift_date=payload.shift_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        assignee_id=payload.assignee_id,
        status=ShiftStatus.DRAFT,
    )
    db.add(shift)
    db.commit()
    return _shift_to_response(_load_shift(db, shift.id))


@router.patch("/shifts/{shift_id}/assign", response_model=ShiftResponse)
def assign_shift(
    organization_id: uuid.UUID,
    shift_id: uuid.UUID,
    payload: ShiftAssign,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ShiftResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    shift = get_org_shift(db, organization_id, shift_id)
    get_assignable_employee(db, organization_id, payload.assignee_id, shift.job_role_id)

    shift.assignee_id = payload.assignee_id
    db.commit()
    return _shift_to_response(_load_shift(db, shift.id))


@router.get("/my-shifts", response_model=list[ShiftResponse])
def get_my_shifts(
    organization_id: uuid.UUID,
    week_start: date = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ShiftResponse]:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)
    week_end = get_week_end(week_start)

    shifts = db.scalars(
        select(Shift)
        .where(
            Shift.organization_id == organization_id,
            Shift.assignee_id == current_user.id,
            Shift.shift_date >= week_start,
            Shift.shift_date <= week_end,
        )
        .options(
            selectinload(Shift.location),
            selectinload(Shift.job_role),
            selectinload(Shift.assignee),
        )
        .order_by(Shift.shift_date, Shift.start_time)
    ).all()

    return [_shift_to_response(shift) for shift in shifts]
