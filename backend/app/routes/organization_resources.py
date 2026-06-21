import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.auth.password import hash_password
from app.auth.permissions import require_min_role
from app.database import get_db
from app.models.employee_profile import EmployeeProfile
from app.models.enums import MembershipRole
from app.models.job_role import JobRole
from app.models.location import Location
from app.models.membership import OrganizationMembership
from app.models.user import User
from app.schemas.employee import EmployeeResponse, MemberCreate
from app.schemas.job_role import JobRoleCreate, JobRoleResponse
from app.schemas.location import LocationCreate, LocationResponse

router = APIRouter(prefix="/organizations/{organization_id}", tags=["organization-resources"])


def _get_org_location(
    db: Session, organization_id: uuid.UUID, location_id: uuid.UUID
) -> Location:
    location = db.scalar(
        select(Location).where(
            Location.id == location_id,
            Location.organization_id == organization_id,
        )
    )
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found in this organization",
        )
    return location


def _get_org_job_roles(
    db: Session, organization_id: uuid.UUID, job_role_ids: list[uuid.UUID]
) -> list[JobRole]:
    if not job_role_ids:
        return []

    roles = db.scalars(
        select(JobRole).where(
            JobRole.organization_id == organization_id,
            JobRole.id.in_(job_role_ids),
        )
    ).all()
    if len(roles) != len(set(job_role_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more job roles are invalid for this organization",
        )
    return list(roles)


@router.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(
    organization_id: uuid.UUID,
    payload: LocationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Location:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)

    location = Location(
        organization_id=organization_id,
        name=payload.name,
        address=payload.address,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


@router.get("/locations", response_model=list[LocationResponse])
def list_locations(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Location]:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)

    return list(
        db.scalars(
            select(Location)
            .where(Location.organization_id == organization_id)
            .order_by(Location.name)
        ).all()
    )


@router.post("/job-roles", response_model=JobRoleResponse, status_code=status.HTTP_201_CREATED)
def create_job_role(
    organization_id: uuid.UUID,
    payload: JobRoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JobRole:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)

    existing = db.scalar(
        select(JobRole).where(
            JobRole.organization_id == organization_id,
            JobRole.name == payload.name,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job role already exists in this organization",
        )

    job_role = JobRole(organization_id=organization_id, name=payload.name)
    db.add(job_role)
    db.commit()
    db.refresh(job_role)
    return job_role


@router.get("/job-roles", response_model=list[JobRoleResponse])
def list_job_roles(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobRole]:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)

    return list(
        db.scalars(
            select(JobRole)
            .where(JobRole.organization_id == organization_id)
            .order_by(JobRole.name)
        ).all()
    )


@router.post("/members", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def add_member(
    organization_id: uuid.UUID,
    payload: MemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmployeeResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)

    if payload.location_id is not None:
        _get_org_location(db, organization_id, payload.location_id)

    job_roles = _get_org_job_roles(db, organization_id, payload.job_role_ids)

    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None:
        if payload.password is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required for new users",
            )
        user = User(
            email=payload.email,
            full_name=payload.full_name,
            hashed_password=hash_password(payload.password),
        )
        db.add(user)
        db.flush()
    else:
        existing_membership = db.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user.id,
            )
        )
        if existing_membership is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization",
            )

    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user.id,
        role=payload.membership_role,
    )
    profile = EmployeeProfile(
        organization_id=organization_id,
        user_id=user.id,
        location_id=payload.location_id,
        job_title=payload.job_title,
        job_roles=job_roles,
    )
    db.add(membership)
    db.add(profile)
    db.commit()

    profile = db.scalar(
        select(EmployeeProfile)
        .where(EmployeeProfile.id == profile.id)
        .options(
            selectinload(EmployeeProfile.location),
            selectinload(EmployeeProfile.job_roles),
        )
    )
    assert profile is not None

    return EmployeeResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        membership_role=membership.role,
        location=profile.location,
        job_title=profile.job_title,
        job_roles=profile.job_roles,
    )


@router.get("/employees", response_model=list[EmployeeResponse])
def list_employees(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EmployeeResponse]:
    require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)

    profiles = db.scalars(
        select(EmployeeProfile)
        .where(EmployeeProfile.organization_id == organization_id)
        .options(
            selectinload(EmployeeProfile.user),
            selectinload(EmployeeProfile.location),
            selectinload(EmployeeProfile.job_roles),
        )
        .order_by(EmployeeProfile.created_at)
    ).all()

    membership_by_user = {
        membership.user_id: membership
        for membership in db.scalars(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id
            )
        ).all()
    }

    employees: list[EmployeeResponse] = []
    for profile in profiles:
        membership = membership_by_user.get(profile.user_id)
        if membership is None:
            continue
        employees.append(
            EmployeeResponse(
                user_id=profile.user_id,
                email=profile.user.email,
                full_name=profile.user.full_name,
                membership_role=membership.role,
                location=profile.location,
                job_title=profile.job_title,
                job_roles=profile.job_roles,
            )
        )
    return employees
