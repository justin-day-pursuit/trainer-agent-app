"""
Authentication and Authorization Module.

This module provides two distinct security flows for the application:
1. Trainer Authentication: Verifies Supabase JWT tokens passed in the
   Authorization header so personal trainers can manage client data securely.
2. Client Session Link Authentication: Validates unique, non-guessable session tokens
   (UUIDs) so clients can log in-gym workouts and view their progress without
   needing to sign up with an email and password.
"""

import asyncio
from typing import Any, Optional, Tuple
import jwt
from fastapi import Depends, Header, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db

settings = get_settings()
_jwks_client: Optional[jwt.PyJWKClient] = None


def _get_jwks_client() -> jwt.PyJWKClient:
    """Fetches and caches the public keys Supabase signs its tokens with."""
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")
    return _jwks_client


async def _resolve_signing_key(token: str) -> Tuple[Any, str]:
    """
    Picks the key to verify a token with. Supabase projects sign with either a public-key
    pair (ES256) or a shared secret (HS256). Only these two are ever accepted, and each
    is tied to its own kind of key, so a token can't choose a weaker way to be checked.
    """
    algorithm = jwt.get_unverified_header(token).get("alg")
    if algorithm == "ES256":
        signing_key = await asyncio.to_thread(_get_jwks_client().get_signing_key_from_jwt, token)
        return signing_key.key, algorithm
    if algorithm == "HS256" and settings.supabase_jwt_secret:
        return settings.supabase_jwt_secret, algorithm
    raise jwt.InvalidAlgorithmError(f"Unsupported token algorithm: {algorithm}")


async def get_current_trainer(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> dict:
    """
    Validates the Supabase JWT token sent by the trainer's browser.
    
    This function reads the 'Authorization: Bearer <token>' header, decodes the token
    using the Supabase JWT secret, and confirms that the caller is an authenticated trainer.
    If the token is missing or expired, it rejects the request with HTTP 401 Unauthorized.
    """
    if not authorization or not authorization.startswith("Bearer "):
        # In local debug mode, allow a developer fallback header if JWT secret is not yet set
        if settings.debug and not settings.supabase_jwt_secret:
            return {
                "sub": "dev-trainer-uuid",
                "email": "trainer@example.com",
                "role": "trainer",
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]

    try:
        key, algorithm = await _resolve_signing_key(token)
        return jwt.decode(token, key, algorithms=[algorithm], audience="authenticated")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(err)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_client_session(
    token: str = Path(..., description="The unique client session token from the URL"),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates a client's unique session token from the URL path (/s/:token).
    
    This allows a client to access their workout plan and log sets without an account.
    It checks the database to verify that the token exists and is currently active.
    """
    # Import model lazily to prevent circular imports during app startup
    from app.models.client import ClientSession

    stmt = select(ClientSession).where(
        ClientSession.session_token == token,
        ClientSession.is_active == True,  # noqa: E712
    )
    result = await db.execute(stmt)
    session_record = result.scalar_one_or_none()

    if not session_record:
        # For demonstration or local preview if token matches a mock identifier
        if settings.debug and token in ["demo-client-session", "test-token"]:
            return {
                "id": 1,
                "client_id": 1,
                "session_token": token,
                "is_active": True,
            }
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workout session link not found or has been deactivated by your trainer.",
        )

    return session_record
