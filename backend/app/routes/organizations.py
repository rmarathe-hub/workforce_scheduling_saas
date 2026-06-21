import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_org_member
from app.database import get_db
from app.models.enums import MembershipRole
from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationMembershipResponse,
    OrganizationResponse,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=list[OrganizationMembershipResponse])
def list_my_organizations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OrganizationMembership]:
    memberships = db.scalars(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == current_user.id)
        .options(selectinload(OrganizationMembership.organization))
        .order_by(OrganizationMembership.created_at)
    ).all()
    return list(memberships)


@router.post("", response_model=OrganizationResponse, status_code=201)
def create_organization(
    payload: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    organization = Organization(name=payload.name, timezone=payload.timezone)
    membership = OrganizationMembership(
        organization=organization,
        user=current_user,
        role=MembershipRole.OWNER,
    )
    db.add(organization)
    db.add(membership)
    db.commit()
    db.refresh(organization)
    return organization


@router.get("/{organization_id}", response_model=OrganizationResponse)
def get_organization(
    organization_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    membership = require_org_member(db, organization_id, current_user)
    return membership.organization
