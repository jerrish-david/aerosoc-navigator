from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.institute.application import create_portal


settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.mount("/institute", create_portal(), name="institute")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "status": "running",
        "message": "Use /docs for the API specification.",
    }
