"""
Database Connection and Session Management.

This module initializes the asynchronous SQLAlchemy database engine and provides
a session generator (`get_db`) that FastAPI routes inject to read and write records
safely within an isolated database transaction.
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

# Retrieve application settings containing the database URL
settings = get_settings()

# Create the asynchronous engine connected to PostgreSQL.
# In production, pool_pre_ping checks that connections are alive before using them,
# preventing stale connection errors when communicating with cloud databases.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

# Async session factory configured to produce independent database sessions
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy database models.
    
    All database tables (such as Trainer, ClientProfile, WorkoutPlan)
    inherit from this class so Alembic and SQLAlchemy can manage them together.
    """
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency generator for FastAPI endpoints to obtain an active database session.
    
    When an API request arrives, this opens a fresh database session. Once the request
    finishes processing, it cleanly commits or rolls back changes and closes the session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
