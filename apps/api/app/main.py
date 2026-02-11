"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, export, invoices, webhooks

settings = get_settings()

# Initialize Sentry if DSN is configured
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    import logging

    import redis.asyncio as redis
    from sqlalchemy import text

    from app.database import engine
    from app.models import Base

    logger = logging.getLogger("uvicorn")

    # Startup
    logger.info("Starting faktura.ai API...")

    # 1. Create database tables (dev only)
    if settings.environment == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")

    # 2. Verify database connectivity
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")

    # 3. Initialize Redis
    redis_client = redis.from_url(settings.redis_url)
    await redis_client.ping()
    logger.info("Redis connection verified")
    app.state.redis = redis_client

    logger.info(f"faktura.ai API v{settings.app_version} ready ({settings.environment})")
    yield

    # Shutdown
    logger.info("Shutting down faktura.ai API...")
    await engine.dispose()

    if hasattr(app.state, "redis"):
        await app.state.redis.close()
    logger.info("All connections have been closed!")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered invoice processing API for the Serbian market",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://fakturaai.rs",
        "https://www.fakturaai.rs",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["Invoices"])
app.include_router(export.router, prefix="/api/v1/export", tags=["Export"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
