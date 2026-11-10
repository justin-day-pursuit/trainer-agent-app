# ==============================================================================
# Multi-stage Dockerfile for FastAPI Backend (Optimized for Render)
# ==============================================================================

FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy package metadata together because pyproject.toml references README.md.
# Keep application code and environment files out of this dependency-only layer.
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Final stage
FROM python:3.10-slim AS runner

WORKDIR /app

# Create non-privileged user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed python packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy backend source code
COPY app/ app/
COPY alembic.ini .
COPY alembic/ alembic/

USER appuser

EXPOSE 8000

# Render supplies PORT dynamically at runtime; local development defaults to port 8000.
# On Render's free tier, pre-deploy commands are disallowed by the platform.
# To ensure database tables and revisions stay current without manual intervention,
# Alembic runs migrations first; once complete, uvicorn starts the FastAPI application.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
