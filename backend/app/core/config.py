"""
Application Configuration Module.

This file loads and validates all settings and secrets from environment variables
(such as database credentials, Supabase keys, and AI provider tokens).
It uses Pydantic's BaseSettings to ensure that required variables are present
and properly formatted when the server starts up.
"""

from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central settings class holding all application configuration.
    
    Values can be provided via environment variables or a local `.env` file.
    Sensible defaults are provided for local development where appropriate.
    """

    # General application settings
    app_name: str = "Trainer Progression API"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    port: int = Field(default=8000, alias="PORT")

    # Database configuration for PostgreSQL
    # DATABASE_URL points to the transaction pooler (port 6543) for runtime queries.
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/trainer_progression_db",
        alias="DATABASE_URL",
    )
    # DIRECT_URL points to the session connection (port 5432) for Alembic migrations.
    direct_url: str = Field(
        default="",
        alias="DIRECT_URL",
    )

    # Supabase credentials and JWT verification
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_anon_key: str = Field(default="", alias="SUPABASE_ANON_KEY")
    supabase_jwt_secret: str = Field(default="", alias="SUPABASE_JWT_SECRET")

    # AI Provider API Keys
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # CORS configuration for frontend web app communication
    cors_origins_raw: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ORIGINS",
    )

    @property
    def async_database_url(self) -> str:
        """
        Normalizes DATABASE_URL to use the async psycopg driver (postgresql+psycopg://).
        Strips ?pgbouncer=true which psycopg (v3) rejects as an unrecognized libpq option.
        """
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        if "?pgbouncer=true" in url:
            url = url.replace("?pgbouncer=true", "")
        elif "&pgbouncer=true" in url:
            url = url.replace("&pgbouncer=true", "")
        return url

    @property
    def async_direct_url(self) -> str:
        """
        Normalizes DIRECT_URL to use the async psycopg driver (postgresql+psycopg://)
        for direct session connections (used by Alembic migrations on port 5432).
        """
        url = self.direct_url or self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        if "?pgbouncer=true" in url:
            url = url.replace("?pgbouncer=true", "")
        elif "&pgbouncer=true" in url:
            url = url.replace("&pgbouncer=true", "")
        return url

    @property
    def cors_origins(self) -> List[str]:
        """
        Parses the comma-separated CORS_ORIGINS string into a list of clean URLs
        that FastAPI middleware can use to allow browser cross-origin requests.
        """
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached singleton instance of the Settings object.
    
    Using lru_cache prevents re-reading environment variables or the disk
    on every single incoming API request, speeding up performance.
    """
    return Settings()
