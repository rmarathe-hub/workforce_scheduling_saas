import uuid
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.permissions import require_min_role
from app.database import get_db
from app.models.enums import MembershipRole
from app.models.user import User
from app.schemas.analytics import DashboardAnalyticsResponse
from app.services.analytics_service import get_dashboard_analytics

router = APIRouter(prefix="/organizations/{organization_id}", tags=["analytics"])


@router.get("/analytics/dashboard", response_model=DashboardAnalyticsResponse)
def get_manager_dashboard(
    organization_id: uuid.UUID,
    week_start: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardAnalyticsResponse:
    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    return get_dashboard_analytics(db, organization_id, week_start)
