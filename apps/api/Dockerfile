# FastAPI Backend Dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 api
WORKDIR /app

# Install Python dependencies
# Copy pyproject.toml and install deps (skip fakturaai-ml — not needed in API container)
COPY apps/api/pyproject.toml /app/
RUN pip install \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.32.0" \
    "python-multipart>=0.0.12" \
    "python-jose[cryptography]>=3.3.0" \
    "passlib[argon2]>=1.7.4" \
    "sqlalchemy>=2.0.0" \
    "alembic>=1.14.0" \
    "asyncpg>=0.30.0" \
    "redis>=5.0.0" \
    "celery>=5.4.0" \
    "httpx>=0.28.0" \
    "pydantic>=2.10.0" \
    "pydantic-settings>=2.6.0" \
    "boto3>=1.35.0" \
    "pillow>=11.0.0" \
    "sentry-sdk[fastapi]>=2.19.0" \
    "email-validator>=2.0.0"

# Copy application code
COPY apps/api/app /app/app

# Switch to non-root user
USER api

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
