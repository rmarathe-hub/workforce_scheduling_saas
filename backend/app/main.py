from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.auth import router as auth_router
from app.routes.organization_resources import router as organization_resources_router
from app.routes.organizations import router as organizations_router
from app.routes.scheduling import router as scheduling_router

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(organization_resources_router)
app.include_router(scheduling_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
