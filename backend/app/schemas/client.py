"""
Pydantic Schemas for Client Data.

Defines input validation and JSON response serialization models
for client onboarding, profile updates, and unique session links.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ClientProfileBase(BaseModel):
    """Base fields shared across client creation and profile display."""
    full_name: str = Field(..., description="Full name of the fitness client")
    email: Optional[EmailStr] = Field(None, description="Client email address")
    phone: Optional[str] = Field(None, description="Client contact number")
    primary_goal: Optional[str] = Field(None, description="Primary fitness goal, e.g. Hypertrophy, Strength")
    experience_level: Optional[str] = Field(None, description="Beginner, Intermediate, Advanced")
    injuries: List[str] = Field(default_factory=list, description="Known injuries or movement inhibitors")
    intake_notes: Optional[str] = Field(None, description="Agent or trainer intake notes")


class ClientProfileCreate(ClientProfileBase):
    """Payload sent by trainer to register a new client profile."""
    pass


class ClientProfileResponse(ClientProfileBase):
    """Complete client profile returned to the trainer dashboard."""
    id: int
    trainer_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClientSessionCreate(BaseModel):
    """Payload to request creation of a unique client session link."""
    client_id: int


class ClientSessionResponse(BaseModel):
    """Returns the generated unique session token and full mobile URL."""
    session_id: int
    client_id: int
    session_token: str
    session_url: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
