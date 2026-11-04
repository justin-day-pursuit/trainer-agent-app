"""
Trainer Database Model.

Represents an independent personal trainer with an account linked to Supabase Auth.
A trainer manages multiple clients, reviews their progression drafts, and approves
weekly programs before they become visible to clients.
"""

from datetime import datetime
from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Trainer(Base):
    """
    SQLAlchemy model representing a personal trainer.
    
    Connected directly to Supabase Auth via `supabase_user_id`.
    """
    __tablename__ = "trainers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    supabase_user_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship to clients managed by this trainer
    clients: Mapped[list["ClientProfile"]] = relationship(  # noqa: F821
        "ClientProfile", back_populates="trainer", cascade="all, delete-orphan"
    )
