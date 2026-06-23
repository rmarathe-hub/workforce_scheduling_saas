from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import VERCEL_PREVIEW_ORIGIN_REGEX, settings
from app.routes.analytics import router as analytics_router
from app.routes.audit_log import router as audit_log_router
from app.routes.auth import router as auth_router
from app.routes.availability import router as availability_router
from app.routes.documents import router as documents_router
from app.routes.notifications import router as notifications_router
from app.routes.organization_resources import router as organization_resources_router
from app.routes.organizations import router as organizations_router
from app.routes.scheduling import router as scheduling_router
from app.routes.shift_swap import router as shift_swap_router
from app.routes.time_off import router as time_off_router

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_origin_regex=VERCEL_PREVIEW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(organization_resources_router)
app.include_router(documents_router)
app.include_router(analytics_router)
app.include_router(scheduling_router)
app.include_router(availability_router)
app.include_router(time_off_router)
app.include_router(shift_swap_router)
app.include_router(audit_log_router)
app.include_router(notifications_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
