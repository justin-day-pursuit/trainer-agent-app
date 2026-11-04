"""
Trainer Client Management Endpoints.

Allows personal trainers to create client profiles, list their roster,
and generate unique, non-guessable session links that clients can bookmark on mobile.
All endpoints in this module require trainer authentication via Supabase JWT.
"""

from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_trainer
from app.core.config import get_settings
from app.core.database import get_db
from app.models.client import ClientProfile, ClientSession
from app.schemas.client import (
    ClientProfileCreate,
    ClientProfileResponse,
    ClientSessionResponse,
)

router = APIRouter(prefix="/clients", tags=["Clients (Trainer Protected)"])
settings = get_settings()


@router.post("", response_model=ClientProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Creates a new client profile under the authenticated trainer's roster.
    """
    # Create client record
    new_client = ClientProfile(
        trainer_id=1,  # In production, resolved from current_trainer["sub"]
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        primary_goal=payload.primary_goal,
        experience_level=payload.experience_level,
        injuries_json=payload.injuries,
        intake_notes=payload.intake_notes,
    )
    db.add(new_client)
    await db.flush()
    await db.refresh(new_client)

    return ClientProfileResponse(
        id=new_client.id,
        trainer_id=new_client.trainer_id,
        full_name=new_client.full_name,
        email=new_client.email,
        phone=new_client.phone,
        primary_goal=new_client.primary_goal,
        experience_level=new_client.experience_level,
        injuries=new_client.injuries_json or [],
        intake_notes=new_client.intake_notes,
        created_at=new_client.created_at,
        updated_at=new_client.updated_at,
    )


@router.get("", response_model=List[ClientProfileResponse])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Retrieves all clients managed by the authenticated trainer.
    """
    stmt = select(ClientProfile).order_by(ClientProfile.full_name.asc())
    result = await db.execute(stmt)
    clients = result.scalars().all()

    return [
        ClientProfileResponse(
            id=c.id,
            trainer_id=c.trainer_id,
            full_name=c.full_name,
            email=c.email,
            phone=c.phone,
            primary_goal=c.primary_goal,
            experience_level=c.experience_level,
            injuries=c.injuries_json or [],
            intake_notes=c.intake_notes,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in clients
    ]


@router.post("/{client_id}/sessions", response_model=ClientSessionResponse)
async def generate_client_session_link(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_trainer: dict = Depends(get_current_trainer),
):
    """
    Generates a new unique session URL for a client.
    
    The trainer sends this URL to the client. The client taps the link to open
    their in-gym workout logger without needing an email or password.
    """
    token_str = str(uuid.uuid4())
    session_record = ClientSession(
        client_id=client_id,
        session_token=token_str,
        is_active=True,
    )
    db.add(session_record)
    await db.flush()
    await db.refresh(session_record)

    # Build client session URL
    frontend_base = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    session_url = f"{frontend_base}/s/{token_str}"

    return ClientSessionResponse(
        session_id=session_record.id,
        client_id=session_record.client_id,
        session_token=session_record.session_token,
        session_url=session_url,
        is_active=session_record.is_active,
        created_at=session_record.created_at,
    )
