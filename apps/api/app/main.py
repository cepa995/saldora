"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.middleware import RequestContextMiddleware, SecurityHeadersMiddleware
from app.routers import (
    analytics,
    audit_logs,
    auth,
    billing,
    clients,
    compliance,
    exchange_rates,
    export,
    invitations,
    invoices,
    join_requests,
    organizations,
    products,
    reports,
    rules,
    sef,
    team,
    users,
    webhooks,
)
from app.security import limiter

settings = get_settings()

# Initialize Sentry if DSN is configured and SDK is installed
if settings.sentry_dsn:
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
        )
    except ImportError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    import logging

    import redis.asyncio as redis
    from sqlalchemy import text

    from app.database import engine

    logger = logging.getLogger("uvicorn")

    # Startup
    logger.info("Starting saldora.ai API...")

    # 1. Verify database connectivity (migrations are handled by Alembic)
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")

    # 3. Initialize Redis
    redis_client = redis.from_url(settings.redis_url)
    await redis_client.ping()
    logger.info("Redis connection verified")
    app.state.redis = redis_client

    # 4. Verify S3-compatible storage
    from app.services.storage import ensure_bucket_exists

    ensure_bucket_exists()
    logger.info("Storage connection verified")

    logger.info(f"saldora.ai API v{settings.app_version} ready ({settings.environment})")
    yield

    # Shutdown
    logger.info("Shutting down saldora.ai API...")
    await engine.dispose()

    if hasattr(app.state, "redis"):
        await app.state.redis.close()
    logger.info("All connections have been closed!")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered invoice processing API for the Serbian market",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://saldora.ai",
        "https://www.saldora.ai",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
    expose_headers=["Content-Disposition"],
)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Request context middleware (extracts IP + User-Agent for audit logging)
app.add_middleware(RequestContextMiddleware)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(invoices.router, prefix="/api/v1/invoices", tags=["Invoices"])
app.include_router(export.router, prefix="/api/v1/export", tags=["Export"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
app.include_router(audit_logs.router, prefix="/api/v1/audit-logs", tags=["Audit Logs"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(rules.router, prefix="/api/v1/rules", tags=["Automation Rules"])
app.include_router(clients.router, prefix="/api/v1/clients", tags=["Clients"])
app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(organizations.router, prefix="/api/v1/organizations", tags=["Organizations"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(team.router, prefix="/api/v1/team", tags=["Team"])
app.include_router(invitations.router, prefix="/api/v1/invitations", tags=["Invitations"])
app.include_router(join_requests.router, prefix="/api/v1/join-requests", tags=["Join Requests"])
app.include_router(sef.router, prefix="/api/v1/sef", tags=["SEF"])
app.include_router(exchange_rates.router, prefix="/api/v1/exchange-rates", tags=["Exchange Rates"])
app.include_router(compliance.router, prefix="/api/v1/compliance", tags=["ZZPL Compliance"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Product Catalog"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/health/services")
async def service_health() -> dict:
    """Check health of dependent services (Redis, Celery OCR workers)."""
    import asyncio
    import logging

    import celery as celery_lib
    import redis.asyncio as aioredis

    logger = logging.getLogger(__name__)

    # Check Redis
    redis_status = "unavailable"
    try:
        r = aioredis.from_url(settings.celery_broker_url)
        await r.ping()
        await r.aclose()
        redis_status = "healthy"
    except Exception as exc:
        logger.debug("Redis health check failed: %s", exc)

    # Check Celery OCR workers
    ocr_status = "unavailable"
    ocr_workers = 0
    try:
        celery_app = celery_lib.Celery(broker=settings.celery_broker_url)
        response = await asyncio.to_thread(celery_app.control.ping, timeout=1.0)
        ocr_workers = len(response) if response else 0
        if ocr_workers > 0:
            ocr_status = "healthy"
    except Exception as exc:
        logger.debug("Celery health check failed: %s", exc)

    return {
        "redis": {"status": redis_status},
        "ocr_worker": {"status": ocr_status, "workers": ocr_workers},
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
