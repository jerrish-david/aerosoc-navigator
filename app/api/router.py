from fastapi import APIRouter

from app.api.routes.alerts import router as alerts_router
from app.api.routes.cases import router as cases_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.documents import router as documents_router
from app.api.routes.health import router as health_router


api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
api_router.include_router(cases_router, prefix="/cases", tags=["cases"])
api_router.include_router(documents_router, prefix="/documents", tags=["documents"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
