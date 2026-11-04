"""
FastAPI Application Entry Point.

This file creates and configures the FastAPI web server.
It sets up:
1. Lifespan event handlers (for opening and closing database connection pools).
2. Cross-Origin Resource Sharing (CORS) middleware to allow browser requests from Next.js.
3. API v1 route mounting.
4. Top-level health check endpoint.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown lifecycle events.
    
    On startup: Verifies settings and prepares database engine.
    On shutdown: Closes active database connection pools cleanly.
    """
    # Startup actions
    yield
    # Shutdown actions
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    description=(
        "FastAPI backend and multi-agent progression engine for the "
        "Trainer Progression App. Powers frictionless client workout logging, "
        "deterministic progression drafting, and trainer administrative monitoring."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS)
# Allows the Next.js frontend (on Vercel or localhost:3000) to communicate with this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route providing basic service metadata
@app.get("/", tags=["System"])
async def root():
    """Returns basic service information."""
    return {
        "service": settings.app_name,
        "status": "online",
        "documentation": "/docs",
        "api_v1": "/api/v1",
    }


# Health check endpoint for uptime monitors
@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint for container probes."""
    return {
        "status": "ok",
        "environment": settings.environment,
    }


# Mount API v1 router under /api/v1 prefix
app.include_router(api_router, prefix="/api/v1")
