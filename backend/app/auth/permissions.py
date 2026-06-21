import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.enums import MembershipRole
from app.models.membership import OrganizationMembership
from app.models.user import User

ROLE_RANK: dict[MembershipRole, int] = {
    MembershipRole.OWNER: 3,
    MembershipRole.MANAGER: 2,
    MembershipRole.EMPLOYEE: 1,
}


def get_membership(
    db: Session, organization_id: uuid.UUID, user_id: uuid.UUID
) -> OrganizationMembership | None:
    return db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
        )
    )


def require_org_member(
    db: Session, organization_id: uuid.UUID, user: User
) -> OrganizationMembership:
    membership = get_membership(db, organization_id, user.id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )
    return membership


def require_min_role(
    db: Session,
    organization_id: uuid.UUID,
    user: User,
    min_role: MembershipRole,
) -> OrganizationMembership:
    membership = require_org_member(db, organization_id, user)
    if ROLE_RANK[membership.role] < ROLE_RANK[min_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return membership
