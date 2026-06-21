import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.membership import OrganizationMembership
from app.models.organization import Organization
from app.models.user import User


def cleanup_user(db: Session, user_id: str) -> None:
    uid = uuid.UUID(user_id)

    memberships = db.scalars(
        select(OrganizationMembership.organization_id).where(
            OrganizationMembership.user_id == uid
        )
    ).all()
    org_ids = set(memberships)

    db.execute(delete(OrganizationMembership).where(OrganizationMembership.user_id == uid))

    for org_id in org_ids:
        remaining = db.scalar(
            select(func.count())
            .select_from(OrganizationMembership)
            .where(OrganizationMembership.organization_id == org_id)
        )
        if remaining == 0:
            db.execute(delete(Organization).where(Organization.id == org_id))

    db.execute(delete(User).where(User.id == uid))
    db.commit()
