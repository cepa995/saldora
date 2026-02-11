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
    # Startup
    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Warm up ML models (optional)
    yield
    # Shutdown
    # TODO: Close database connections
    # TODO: Close Redis connections


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
