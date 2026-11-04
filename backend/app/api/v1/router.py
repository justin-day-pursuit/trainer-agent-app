"""
Aggregated API v1 Router.

Mounts health, client, session, workout, and trainer endpoints under
the /api/v1 namespace.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    clients,
    health,
    sessions,
    trainer,
    workouts,
)

api_router = APIRouter()

# Mount endpoints
api_router.include_router(health.router)
api_router.include_router(clients.router)
api_router.include_router(sessions.router)
api_router.include_router(workouts.router)
api_router.include_router(trainer.router)
