"""
Health Check Endpoint.

Used by container orchestrators (Render, Docker, Kubernetes) and monitoring probes
to confirm that the FastAPI service is running and responsive.
"""

from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", summary="Service Health Check")
async def health_check():
    """
    Returns a 200 OK status with the active environment name to confirm API health.
    """
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }
