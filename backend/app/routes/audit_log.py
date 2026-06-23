import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_min_role
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.enums import MembershipRole
from app.models.user import User
from app.schemas.audit_log import AuditLogListResponse, audit_log_to_response

router = APIRouter(prefix="/organizations/{organization_id}", tags=["audit-logs"])

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


@router.get("/audit-logs", response_model=AuditLogListResponse)
def list_audit_logs(
    organization_id: uuid.UUID,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)

    total = db.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(AuditLog.organization_id == organization_id)
    )
    assert total is not None

    entries = db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == organization_id)
        .options(selectinload(AuditLog.actor))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()

    return AuditLogListResponse(
        items=[audit_log_to_response(entry) for entry in entries],
        total=total,
        limit=limit,
        offset=offset,
    )
