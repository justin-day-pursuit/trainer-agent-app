"""
Database models export package.

Aggregates all SQLAlchemy declarative models so that Alembic migrations
and FastAPI database queries can import them from a single namespace.
"""

from app.core.database import Base
from app.models.trainer import Trainer
from app.models.client import ClientProfile, ClientSession
from app.models.workout import WorkoutPlan, WorkoutLog
from app.models.trace import AgentTrace

__all__ = [
    "Base",
    "Trainer",
    "ClientProfile",
    "ClientSession",
    "WorkoutPlan",
    "WorkoutLog",
    "AgentTrace",
]
