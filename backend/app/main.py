import logging
import uuid

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

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
from app.schemas.health import HealthResponse, ReadinessResponse
from app.services.health_service import build_health_status, build_readiness_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(title=settings.app_name)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIdMiddleware)
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


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse.model_validate(build_health_status())


@app.get("/readiness", response_model=ReadinessResponse)
def readiness_check(response: Response) -> ReadinessResponse:
    payload = build_readiness_status()
    if payload["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse.model_validate(payload)
