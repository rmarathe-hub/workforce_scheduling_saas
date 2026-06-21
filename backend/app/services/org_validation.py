import uuid
from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.coverage_requirement import CoverageRequirement
from app.models.employee_profile import EmployeeProfile
from app.models.job_role import JobRole
from app.models.location import Location
from app.models.membership import OrganizationMembership
from app.models.shift import Shift
from app.models.user import User


def get_org_location(db: Session, organization_id: uuid.UUID, location_id: uuid.UUID) -> Location:
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


def get_org_job_role(
    db: Session, organization_id: uuid.UUID, job_role_id: uuid.UUID
) -> JobRole:
    job_role = db.scalar(
        select(JobRole).where(
            JobRole.id == job_role_id,
            JobRole.organization_id == organization_id,
        )
    )
    if job_role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job role not found in this organization",
        )
    return job_role


def get_org_coverage_requirement(
    db: Session, organization_id: uuid.UUID, requirement_id: uuid.UUID
) -> CoverageRequirement:
    requirement = db.scalar(
        select(CoverageRequirement).where(
            CoverageRequirement.id == requirement_id,
            CoverageRequirement.organization_id == organization_id,
        )
    )
    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coverage requirement not found in this organization",
        )
    return requirement


def get_org_shift(db: Session, organization_id: uuid.UUID, shift_id: uuid.UUID) -> Shift:
    shift = db.scalar(
        select(Shift).where(
            Shift.id == shift_id,
            Shift.organization_id == organization_id,
        )
    )
    if shift is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found in this organization",
        )
    return shift


def get_week_end(week_start: date) -> date:
    return week_start + timedelta(days=6)


def get_assignable_employee(
    db: Session,
    organization_id: uuid.UUID,
    assignee_id: uuid.UUID,
    job_role_id: uuid.UUID,
) -> User:
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == assignee_id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee is not a member of this organization",
        )

    profile = db.scalar(
        select(EmployeeProfile)
        .where(
            EmployeeProfile.organization_id == organization_id,
            EmployeeProfile.user_id == assignee_id,
        )
        .options(selectinload(EmployeeProfile.job_roles))
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee does not have an employee profile in this organization",
        )

    if not any(role.id == job_role_id for role in profile.job_roles):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee does not have the required job role",
        )

    user = db.get(User, assignee_id)
    assert user is not None
    return user
