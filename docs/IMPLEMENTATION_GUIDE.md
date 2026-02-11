# FakturaAI Implementation Guide

A step-by-step guide to building FakturaAI from the ground up, feature by feature, with best practices for each phase.

The [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) explains **what** each piece is. This guide explains **when** and **how** to build them, and **why** in that order.

---

## Table of Contents

- [Implementation Philosophy](#implementation-philosophy)
- [Phase 0: Foundation](#phase-0-foundation)
- [Phase 1: Authentication](#phase-1-authentication)
- [Phase 2: Storage & Upload](#phase-2-storage--upload)
- [Phase 3: Invoice Processing Pipeline](#phase-3-invoice-processing-pipeline)
- [Phase 4: Invoice CRUD](#phase-4-invoice-crud)
- [Phase 5: Export](#phase-5-export)
- [Phase 6: Integrations](#phase-6-integrations)
- [Phase 7: Frontend Integration](#phase-7-frontend-integration)
- [Phase 8: Testing](#phase-8-testing)
- [Phase 9: Production Deployment](#phase-9-production-deployment)
- [Development Workflow Best Practices](#development-workflow-best-practices)

---

## Implementation Philosophy

### Build Order Principle

Every phase depends on the one before it. Don't skip ahead.

```
Phase 0: Foundation          ← Nothing works without this
  │
Phase 1: Authentication      ← Can't protect anything without users
  │
Phase 2: Storage & Upload    ← Can't process invoices without storing them
  │
Phase 3: Processing Pipeline ← Can't extract data without OCR running end-to-end
  │
Phase 4: Invoice CRUD        ← Can't review/edit without CRUD
  │
Phase 5: Export              ← Can't export without data to export
  │
Phase 6: Integrations       ← APR/Stripe are enhancements, not core
  │
Phase 7: Frontend            ← Build UI once backend is stable
  │
Phase 8: Testing             ← Test as you go, but dedicated test phase here
  │
Phase 9: Production          ← Deploy when it works end-to-end
```

### Best Practices (Apply to Every Phase)

1. **Verify each phase works before moving on.** Write a quick test (even a curl command) before starting the next phase.
2. **Commit at the end of each step**, not just each phase. Small, atomic commits.
3. **One `.env` file, many environments.** Never hard-code connection strings, secrets, or URLs.
4. **Errors are data.** Always return structured error responses, never raw tracebacks.
5. **Log at boundaries.** Log when a request arrives, when an external call is made, and when something fails. Don't log inside tight loops.

---

## Phase 0: Foundation

**Goal:** The API starts, connects to PostgreSQL and Redis, creates tables, and shuts down cleanly.

This is the most important phase. Every feature depends on a working database connection and clean startup/shutdown.

### Step 0.1: Database Module

Create the async database engine and session factory.

**Create `apps/api/app/database.py`:**

```python
"""Async database engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

settings = get_settings()

# The engine manages a pool of database connections.
# pool_size=20 means 20 persistent connections ready to go.
# max_overflow=10 means 10 more can be created temporarily during spikes.
# When a spike ends, overflow connections are closed.
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,  # Log SQL queries in debug mode
)

# A session factory. Each call to async_session() creates a new session
# bound to one connection from the pool.
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (avoids lazy-load issues)
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.

    Usage in a router:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    The session is automatically closed when the request ends,
    even if an exception occurs.
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
```

**Why this matters:**
- Every endpoint that touches the database will use `Depends(get_db)`.
- The connection pool prevents opening/closing connections per request (expensive).
- `expire_on_commit=False` avoids a common async SQLAlchemy pitfall where accessing attributes after commit triggers a lazy load, which doesn't work in async.

### Step 0.2: Base Model

Create the SQLAlchemy declarative base and mixins.

**Create `apps/api/app/models/__init__.py`:**

```python
"""Database models package."""

from app.models.base import Base

__all__ = ["Base"]
```

**Create `apps/api/app/models/base.py`:**

```python
"""SQLAlchemy base model and mixins."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class UUIDMixin:
    """Adds a UUID primary key."""
    id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )


class TimestampMixin:
    """Adds created_at and updated_at columns."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
```

**Why mixins?**
Every table needs `id`, `created_at`, `updated_at`. Writing them once and mixing them in keeps models focused on their own fields. When you create a model, you just do:

```python
class Invoice(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invoices"
    # Only invoice-specific fields here
```

### Step 0.3: Core Models

Create the models you'll need immediately: Organization, User, Invoice, Document.

**Create `apps/api/app/models/organization.py`:**

```python
"""Organization model."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Organization(Base, UUIDMixin, TimestampMixin):
    """
    An organization (company/team) that owns invoices.

    Every user belongs to exactly one organization.
    Every invoice belongs to exactly one organization.
    This is the core multi-tenancy boundary.
    """
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(50), default="free")

    # Relationships
    members: Mapped[list["User"]] = relationship(back_populates="organization")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="organization")
```

**Create `apps/api/app/models/user.py`:**

```python
"""User model."""

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    """Application user."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="member")  # admin, member
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Foreign keys
    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="members")
```

**Create `apps/api/app/models/invoice.py`:**

```python
"""Invoice model."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin, TimestampMixin


class Invoice(Base, UUIDMixin, TimestampMixin):
    """
    An invoice processed through OCR.

    Lifecycle:
      processing → review → verified → exported
                 → error (at any point)
    """
    __tablename__ = "invoices"

    # Ownership
    organization_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default="processing", index=True
    )  # processing, review, verified, exported, error

    # Core fields (populated by OCR)
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    invoice_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)

    # Parties (stored as JSON for schema flexibility)
    seller: Mapped[dict | None] = mapped_column(JSON)
    buyer: Mapped[dict | None] = mapped_column(JSON)

    # Amounts (Numeric for exact decimal math - NEVER use Float for money)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    tax_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    tax_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RSD")

    # Line items
    line_items: Mapped[list | None] = mapped_column(JSON)

    # Document reference
    document_path: Mapped[str | None] = mapped_column(String(500))
    document_content_type: Mapped[str | None] = mapped_column(String(100))

    # OCR metadata
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    field_confidences: Mapped[dict | None] = mapped_column(JSON)
    warnings: Mapped[list | None] = mapped_column(JSON)
    ocr_engine: Mapped[str | None] = mapped_column(String(50))
    processing_time_ms: Mapped[int | None] = mapped_column()
    raw_ocr_text: Mapped[str | None] = mapped_column(Text)

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="invoices")
```

**Update `apps/api/app/models/__init__.py`:**

```python
"""Database models package."""

from app.models.base import Base
from app.models.invoice import Invoice
from app.models.organization import Organization
from app.models.user import User

__all__ = ["Base", "Invoice", "Organization", "User"]
```

### Step 0.4: Implement the Lifespan

Now wire it all together in `main.py`. The lifespan is where you:
1. **Startup:** Create database tables, verify Redis, log that the app is ready.
2. **Shutdown:** Close the connection pool, close Redis.

**Update `apps/api/app/main.py` lifespan:**

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    import logging
    from app.database import engine
    from app.models import Base

    logger = logging.getLogger("uvicorn")

    # ── STARTUP ──────────────────────────────────────────────────
    logger.info("Starting FakturaAI API...")

    # 1. Create database tables (dev only - use Alembic in production)
    if settings.environment == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")

    # 2. Verify database connectivity
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")

    # 3. Initialize Redis (optional - for when you add caching)
    # redis_client = redis.from_url(settings.redis_url)
    # await redis_client.ping()
    # logger.info("Redis connection verified")
    # app.state.redis = redis_client

    logger.info(f"FakturaAI API v{settings.app_version} ready ({settings.environment})")

    yield

    # ── SHUTDOWN ─────────────────────────────────────────────────
    logger.info("Shutting down FakturaAI API...")
    await engine.dispose()
    # if hasattr(app.state, "redis"):
    #     await app.state.redis.close()
    logger.info("All connections closed")
```

**How lifespan fits in the grand scheme:**

```
Docker/uvicorn starts the process
  │
  ▼
FastAPI calls lifespan() ← YOU ARE HERE
  │
  ├── Creates connection pool to PostgreSQL
  ├── Creates tables if dev mode
  ├── Verifies connectivity
  ├── (Later: connects to Redis, warms ML models)
  │
  ▼
yield ← App is now ready to serve requests
  │
  ├── Every request uses Depends(get_db) to get a session from the pool
  ├── Sessions are created/destroyed per-request, pool persists
  │
  ▼
App receives shutdown signal (Ctrl+C, docker stop, deploy)
  │
  ├── engine.dispose() closes all pool connections
  ├── Redis connection closed
  │
  ▼
Process exits cleanly
```

**Why this matters:** Without proper lifespan management:
- The first request would be slow (creating connections on-demand)
- Shutdown would leak connections (PostgreSQL has a max connection limit)
- You'd have no way to verify infrastructure is actually reachable at startup

### Step 0.5: Verify Phase 0

At this point, you should be able to:

```bash
# 1. Make sure Docker services are running
docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio

# 2. Start the API
cd apps/api
source ../../.venv/bin/activate
DATABASE_URL="postgresql+asyncpg://fakturaai:fakturaai_dev@localhost:5433/fakturaai" \
uvicorn app.main:app --reload

# 3. You should see in the logs:
#   INFO: Starting FakturaAI API...
#   INFO: Database tables created/verified
#   INFO: Database connection verified
#   INFO: FakturaAI API v0.1.0 ready (development)

# 4. Verify
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0"}

# 5. Check the database has tables
docker exec -it fakturaai-postgres psql -U fakturaai -d fakturaai -c '\dt'
# Should show: organizations, users, invoices
```

### Step 0.6: Alembic Migrations

In development, `Base.metadata.create_all()` is fine. In production, you need migrations (versioned, incremental schema changes).

```bash
cd apps/api
pip install alembic

# Initialize Alembic
alembic init alembic

# Edit alembic/env.py to use your async engine and models
# Edit alembic.ini to use DATABASE_URL from settings
```

**Edit `alembic/env.py`** (key parts):

```python
from app.config import get_settings
from app.models import Base  # Import all models

settings = get_settings()
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", ""))
target_metadata = Base.metadata
```

**Common Alembic commands:**

```bash
# Generate a migration from model changes
alembic revision --autogenerate -m "create initial tables"

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# See current migration state
alembic current
```

**Best practice:** After setting up Alembic, remove `Base.metadata.create_all()` from the lifespan and replace it with:

```python
# In CI/CD or startup script:
alembic upgrade head
```

---

## Phase 1: Authentication

**Goal:** Users can register, login, and receive JWT tokens. Routes can be protected with `Depends(get_current_user)`.

### Why Authentication Before Everything Else?

Every subsequent feature needs to answer: "Who is making this request? Which organization do they belong to?" Without auth, you can't:
- Know which organization an invoice belongs to
- Restrict users from seeing other organizations' data
- Track who uploaded/modified/verified what

### Step 1.1: Password Hashing Utility

**Create `apps/api/app/auth.py`:**

```python
"""Authentication utilities - JWT tokens and password hashing."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.hash import argon2

from app.config import get_settings

settings = get_settings()


# ── Password Hashing ──────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return argon2.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return argon2.verify(plain_password, hashed_password)


# ── JWT Tokens ────────────────────────────────────────────────

def create_access_token(user_id: str, organization_id: str) -> str:
    """Create a JWT access token."""
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": user_id,                  # Subject (who the token is for)
        "org": organization_id,          # Organization (multi-tenancy)
        "exp": expires,                  # Expiration time
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_refresh_token(user_id: str) -> str:
    """Create a JWT refresh token (longer-lived)."""
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": user_id,
        "exp": expires,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
```

**Why Argon2 instead of bcrypt?** Argon2 won the Password Hashing Competition. It's resistant to GPU cracking (memory-hard), configurable, and the current recommendation.

### Step 1.2: Auth Dependencies

**Create `apps/api/app/dependencies.py`:**

```python
"""FastAPI dependencies for injection."""

from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_token
from app.database import get_db
from app.models.user import User

# This tells FastAPI to look for a Bearer token in the Authorization header.
# tokenUrl is for the Swagger UI login form.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extract the current user from the JWT token.

    This is the main auth dependency. Add it to any endpoint that
    requires authentication:

        @router.get("/invoices")
        async def list_invoices(user: User = Depends(get_current_user)):
            # user is guaranteed to be authenticated here
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Fetch user from database
    result = await db.execute(
        select(User).where(User.id == UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user
```

**How this dependency chain works:**

```
Request arrives with header: Authorization: Bearer eyJ...
  │
  ▼
oauth2_scheme extracts "eyJ..." from the header
  │
  ▼
get_current_user receives the token
  ├── Decodes JWT → gets user_id
  ├── Queries database → gets User object
  └── Returns User to the endpoint
  │
  ▼
Your endpoint receives a fully authenticated User object
```

### Step 1.3: Implement Register and Login

Now update `apps/api/app/routers/auth.py` to replace the 501 stubs with real implementations:

```python
"""Authentication router - login, register, token refresh."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import TokenResponse, UserCreate, UserResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> User:
    # 1. Check email uniqueness
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # 2. Create organization
    org = Organization(
        name=user_data.organization_name or f"{user_data.email.split('@')[0]}'s organization"
    )
    db.add(org)
    await db.flush()  # Assigns org.id without committing

    # 3. Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        organization_id=org.id,
        role="admin",  # First user in org is admin
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)  # Reload to get server-generated fields (id, created_at)

    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # 1. Find user
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # 2. Verify password (constant-time comparison to prevent timing attacks)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # 3. Generate tokens
    access_token = create_access_token(str(user.id), str(user.organization_id))
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )
```

### Step 1.4: Verify Phase 1

```bash
# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","organization_name":"Test Corp"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=test@example.com&password=testpass123"
# Returns: {"access_token":"eyJ...","refresh_token":"eyJ...","token_type":"bearer","expires_in":3600}

# Test protected endpoint
TOKEN="eyJ..."  # Copy from login response
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/invoices
```

---

## Phase 2: Storage & Upload

**Goal:** Users can upload a file, it gets stored in MinIO/S3, a database record is created, and a Celery task is queued.

### Step 2.1: Storage Service

Create an abstraction over S3/MinIO so the rest of the app doesn't care which one is being used.

**Create `apps/api/app/services/__init__.py`:**

```python
```

**Create `apps/api/app/services/storage.py`:**

```python
"""S3-compatible storage service."""

import logging
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Lazy-initialized client
_s3_client = None


def get_s3_client():
    """Get or create the S3 client (lazy singleton)."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
        )
    return _s3_client


async def upload_document(
    invoice_id: UUID,
    content: bytes,
    content_type: str,
    filename: str,
) -> str:
    """
    Upload a document to S3.

    Returns the S3 key (path) for later retrieval.
    """
    # Organize files by invoice ID
    extension = _get_extension(content_type)
    key = f"invoices/{invoice_id}/original{extension}"

    client = get_s3_client()
    client.put_object(
        Bucket=settings.storage_bucket,
        Key=key,
        Body=content,
        ContentType=content_type,
        Metadata={"original-filename": filename},
    )

    logger.info(f"Uploaded {len(content)} bytes to {key}")
    return key


def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for downloading a document."""
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def _get_extension(content_type: str) -> str:
    """Map MIME type to file extension."""
    return {
        "application/pdf": ".pdf",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/tiff": ".tiff",
        "image/webp": ".webp",
    }.get(content_type, ".bin")
```

### Step 2.2: Implement Upload Endpoint

Now update `apps/api/app/routers/invoices.py` upload endpoint:

```python
@router.post("/upload", response_model=ProcessingStatus, status_code=status.HTTP_202_ACCEPTED)
async def upload_invoice(
    file: Annotated[UploadFile, File(description="Invoice document")],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    priority: str = Query(default="normal", regex="^(normal|high)$"),
    callback_url: str | None = None,
) -> ProcessingStatus:
    # Validation (already done) ...
    content = await file.read()
    # ... size/type checks ...

    # 1. Create invoice record FIRST (so we have an ID)
    invoice = Invoice(
        organization_id=user.organization_id,
        status="processing",
    )
    db.add(invoice)
    await db.flush()  # Get invoice.id

    # 2. Upload file to S3
    document_path = await upload_document(
        invoice_id=invoice.id,
        content=content,
        content_type=file.content_type,
        filename=file.filename,
    )

    # 3. Update invoice with document path
    invoice.document_path = document_path
    invoice.document_content_type = file.content_type
    await db.commit()
    await db.refresh(invoice)

    # 4. Queue Celery task
    from ocr_worker.tasks import process_invoice
    process_invoice.delay(
        invoice_id=str(invoice.id),
        document_path=document_path,
        callback_url=callback_url,
        priority=priority,
    )

    # 5. Return immediately with job tracking info
    return ProcessingStatus(
        id=invoice.id,
        status="queued",
        progress=0,
        created_at=invoice.created_at,
    )
```

**Why create the DB record before uploading to S3?**

If the S3 upload fails, you just delete the invoice record (or leave it in "error" status). But if you upload to S3 first and then the DB insert fails, you have an orphaned file in S3 with no record pointing to it. DB record first = easier cleanup.

### Step 2.3: Verify Phase 2

```bash
# Upload a file
TOKEN="eyJ..."
curl -X POST http://localhost:8000/api/v1/invoices/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-invoice.pdf"
# Returns: {"id":"uuid...","status":"queued","progress":0,...}

# Check MinIO console at http://localhost:9011
# You should see: fakturaai-documents/invoices/{uuid}/original.pdf
```

---

## Phase 3: Invoice Processing Pipeline

**Goal:** The Celery worker picks up queued tasks, runs OCR, saves results back to the database. The API can return processing status.

### Step 3.1: Connect the Worker to the Database

The worker currently has stub functions (`_save_extraction_result`, `_update_invoice_status`). Implement them.

**The challenge:** The worker runs in a separate process (potentially a separate machine). It needs its own database connection, not a shared one with the API.

**Update `workers/ocr_worker/tasks.py` helper functions:**

```python
def _save_extraction_result(invoice_id: str, result: dict) -> None:
    """Save extraction result to database (sync, runs in worker)."""
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import Session

    # Worker uses SYNC engine (Celery tasks are sync)
    engine = create_engine(
        os.getenv("DATABASE_URL", "").replace("+asyncpg", "+psycopg2"),
    )

    with Session(engine) as session:
        session.execute(
            update(Invoice)
            .where(Invoice.id == invoice_id)
            .values(
                status="review",
                invoice_number=result.get("invoice", {}).get("invoice_number"),
                confidence_score=result.get("overall_confidence"),
                field_confidences=result.get("field_confidences"),
                warnings=[w.get("message") for w in result.get("warnings", [])],
                ocr_engine=result.get("ocr_engine"),
                processing_time_ms=result.get("processing_time_ms"),
                raw_ocr_text=result.get("invoice", {}).get("raw_text"),
                # ... map all other fields ...
            )
        )
        session.commit()
```

**Important:** The worker uses a **synchronous** database connection (`psycopg2`, not `asyncpg`) because Celery tasks are synchronous. This means:
- API → `asyncpg` (async, non-blocking)
- Worker → `psycopg2` (sync, blocking, one task at a time anyway)

### Step 3.2: Implement Status Polling

**Update `apps/api/app/routers/invoices.py`:**

```python
@router.get("/{invoice_id}/status", response_model=ProcessingStatus)
async def get_processing_status(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProcessingStatus:
    # 1. Get invoice (with access control)
    result = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == user.organization_id,
        )
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # 2. If still processing, check Celery task state
    progress = 0
    if invoice.status == "processing":
        from celery.result import AsyncResult
        task_result = AsyncResult(str(invoice_id))
        if task_result.state == "PROCESSING":
            progress = task_result.info.get("progress", 0)

    return ProcessingStatus(
        id=invoice.id,
        status=_map_status(invoice.status),
        progress=progress if invoice.status == "processing" else 100,
        created_at=invoice.created_at,
    )
```

### Step 3.3: Verify Phase 3

This is the first end-to-end test of the core feature:

```bash
# 1. Start the worker
cd workers/ocr_worker
OCR_PRIMARY_ENGINE=easyocr OCR_USE_GPU=false \
celery -A celery_app worker --loglevel=info

# 2. Upload an invoice (from another terminal)
curl -X POST http://localhost:8000/api/v1/invoices/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test-invoice.pdf"
# Returns: {"id":"abc-123","status":"queued",...}

# 3. Poll status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/invoices/abc-123/status
# First call: {"status":"processing","progress":20,...}
# Later:      {"status":"completed","progress":100,...}

# 4. Get full invoice details
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/invoices/abc-123
# Returns: Full invoice with extracted data
```

---

## Phase 4: Invoice CRUD

**Goal:** Users can list, view, edit, delete, and verify invoices.

### Step 4.1: List Invoices

The list endpoint is the most complex because it supports filtering, sorting, and pagination.

```python
@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    sort: str = "created_at",
    order: str = Query(default="desc", regex="^(asc|desc)$"),
):
    # Base query - ALWAYS filter by organization (multi-tenancy!)
    query = select(Invoice).where(
        Invoice.organization_id == user.organization_id
    )

    # Apply filters
    if status:
        query = query.where(Invoice.status == status)
    if date_from:
        query = query.where(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.where(Invoice.invoice_date <= date_to)
    if search:
        query = query.where(
            Invoice.invoice_number.ilike(f"%{search}%")
            | Invoice.raw_ocr_text.ilike(f"%{search}%")
        )

    # Count total (before pagination)
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    # Sort and paginate
    sort_column = getattr(Invoice, sort, Invoice.created_at)
    sort_direction = desc(sort_column) if order == "desc" else asc(sort_column)
    query = query.order_by(sort_direction).offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    invoices = result.scalars().all()

    return InvoiceListResponse(
        data=invoices,
        pagination={
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page,
        },
    )
```

**Critical:** The `.where(Invoice.organization_id == user.organization_id)` filter is your **multi-tenancy boundary**. Every query that touches invoices MUST have this filter. Without it, users can see other organizations' invoices.

### Step 4.2: Get, Update, Delete, Verify

Each follows the same pattern:

```python
# 1. Find invoice by ID
# 2. Check organization_id matches current user (ACCESS CONTROL)
# 3. Do the operation
# 4. Return result
```

The update endpoint has a special concern - **audit logging:**

```python
@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    update_data: InvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    invoice = await _get_invoice_or_404(db, invoice_id, user.organization_id)

    # Track what changed (for ML feedback loop)
    changes = {}
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, new_value in update_dict.items():
        old_value = getattr(invoice, field, None)
        if old_value != new_value:
            changes[field] = {"old": str(old_value), "new": str(new_value)}
            setattr(invoice, field, new_value)

    # Log changes (useful for training the OCR model later)
    if changes:
        logger.info(f"Invoice {invoice_id} updated by {user.id}: {changes}")

    await db.commit()
    await db.refresh(invoice)
    return invoice
```

---

## Phase 5: Export

**Goal:** Export verified invoices to XLSX, CSV, or JSON for accounting software.

### Step 5.1: Export Service

**Create `apps/api/app/services/export.py`:**

```python
"""Export generation service."""

import csv
import io
import json
from uuid import UUID

from openpyxl import Workbook  # pip install openpyxl (add to pyproject.toml)

from app.models.invoice import Invoice


def generate_xlsx(invoices: list[Invoice], template: str = "default") -> bytes:
    """Generate XLSX export from invoices."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Fakture"

    # Headers
    headers = ["Broj fakture", "Datum", "Prodavac PIB", "Prodavac",
               "Kupac PIB", "Kupac", "Osnovica", "PDV", "Ukupno", "Valuta"]
    ws.append(headers)

    # Data rows
    for inv in invoices:
        ws.append([
            inv.invoice_number,
            inv.invoice_date.isoformat() if inv.invoice_date else "",
            inv.seller.get("pib", "") if inv.seller else "",
            inv.seller.get("name", "") if inv.seller else "",
            inv.buyer.get("pib", "") if inv.buyer else "",
            inv.buyer.get("name", "") if inv.buyer else "",
            float(inv.subtotal) if inv.subtotal else 0,
            float(inv.tax_amount) if inv.tax_amount else 0,
            float(inv.total_amount) if inv.total_amount else 0,
            inv.currency,
        ])

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
```

### Step 5.2: Upload Export File and Return Presigned URL

The endpoint generates the file, uploads it to S3, and returns a time-limited download URL:

```python
@router.post("", response_model=ExportResponse)
async def create_export(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 1. Fetch invoices (with access control!)
    result = await db.execute(
        select(Invoice).where(
            Invoice.id.in_(request.invoice_ids),
            Invoice.organization_id == user.organization_id,
            Invoice.status == "verified",
        )
    )
    invoices = result.scalars().all()

    # 2. Generate file
    if request.format == "xlsx":
        content = generate_xlsx(invoices, request.template_id)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif request.format == "csv":
        content = generate_csv(invoices)
        content_type = "text/csv"
    else:
        content = generate_json(invoices)
        content_type = "application/json"

    # 3. Upload to S3
    export_id = uuid4()
    key = f"exports/{user.organization_id}/{export_id}.{request.format}"
    get_s3_client().put_object(
        Bucket=settings.storage_bucket, Key=key,
        Body=content, ContentType=content_type,
    )

    # 4. Return presigned download URL (expires in 1 hour)
    download_url = get_presigned_url(key, expires_in=3600)

    return ExportResponse(
        id=export_id,
        download_url=download_url,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        file_size=len(content),
        invoice_count=len(invoices),
        format=request.format,
    )
```

---

## Phase 6: Integrations

**Goal:** Connect to external services (APR for company verification, Stripe for payments).

### Step 6.1: APR Company Verification

The APR (Serbian Business Registry) API lets you verify that a PIB belongs to a real, active company.

**Create `apps/api/app/services/apr.py`:**

```python
"""APR (Serbian Business Registry) integration."""

import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def verify_company(pib: str) -> dict | None:
    """
    Look up a company by PIB in the APR registry.

    Returns company data or None if not found.
    """
    # TODO: Add Redis caching (APR data rarely changes)
    # cache_key = f"apr:pib:{pib}"
    # cached = await redis.get(cache_key)
    # if cached: return json.loads(cached)

    async with httpx.AsyncClient(timeout=settings.apr_api_timeout) as client:
        try:
            response = await client.get(
                f"{settings.apr_api_url}/companies",
                params={"pib": pib},
            )
            response.raise_for_status()
            data = response.json()

            # Cache the result
            # await redis.setex(cache_key, settings.apr_cache_ttl, json.dumps(data))

            return data
        except httpx.HTTPError as e:
            logger.warning(f"APR lookup failed for PIB {pib}: {e}")
            return None
```

### Step 6.2: Stripe Webhooks

Implement the Stripe webhook handler in `routers/webhooks.py`:

```python
import stripe

@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()

    # Verify the webhook signature (prevents spoofing)
    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(400, "Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    # Handle events
    if event["type"] == "customer.subscription.created":
        # Update organization plan
        pass
    elif event["type"] == "customer.subscription.deleted":
        # Downgrade to free
        pass
    elif event["type"] == "invoice.payment_failed":
        # Send notification
        pass

    return {"status": "received"}
```

---

## Phase 7: Frontend Integration

**Goal:** Connect the Next.js frontend to the real backend API.

### Step 7.1: API Client

**Create `apps/web/src/lib/api.ts`:**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private async fetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      ...options.headers as Record<string, string>,
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    // Don't set Content-Type for FormData (browser sets it with boundary)
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_URL}${path}`, { ...options, headers });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth
  register(data: { email: string; password: string; organization_name?: string }) {
    return this.fetch('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  login(email: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    return this.fetch<{ access_token: string; refresh_token: string }>(
      '/api/v1/auth/login',
      { method: 'POST', body: formData, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    );
  }

  // Invoices
  uploadInvoice(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    return this.fetch('/api/v1/invoices/upload', { method: 'POST', body: formData });
  }

  getInvoiceStatus(id: string) {
    return this.fetch(`/api/v1/invoices/${id}/status`);
  }

  listInvoices(params?: Record<string, string>) {
    const query = new URLSearchParams(params).toString();
    return this.fetch(`/api/v1/invoices?${query}`);
  }
}

export const api = new ApiClient();
```

### Step 7.2: Build Pages

Build the frontend pages in this order:

1. **Login/Register pages** (`/login`, `/register`)
2. **Dashboard** (`/dashboard`) - invoice list with filters
3. **Upload page** (already exists, connect to real API)
4. **Invoice detail/review page** (`/invoices/[id]`) - show extracted data, allow corrections
5. **Export page** (`/export`) - select invoices, choose format

### Step 7.3: State Management

For auth state (token persistence), use a simple approach:

```typescript
// Store token in localStorage after login
const { access_token } = await api.login(email, password);
localStorage.setItem('token', access_token);
api.setToken(access_token);

// On app load, restore token
const token = localStorage.getItem('token');
if (token) api.setToken(token);
```

---

## Phase 8: Testing

**Goal:** Confidence that the system works correctly and doesn't break when you change things.

### Test Strategy

| Layer | Tool | What to Test |
|-------|------|-------------|
| Unit | pytest | Individual functions (hash_password, PIB validation, field extraction) |
| Integration | pytest + httpx | API endpoints with a real test database |
| ML | pytest | Pipeline with sample invoices (golden test set) |
| Frontend | Playwright/Cypress | Critical user flows (upload → review → export) |

### Step 8.1: Backend Test Setup

**Create `apps/api/tests/conftest.py`:**

```python
"""Shared test fixtures."""

import asyncio
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = "postgresql+asyncpg://fakturaai:fakturaai_dev@localhost:5433/fakturaai_test"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session = async_sessionmaker(test_engine, class_=AsyncSession)()
    yield session
    await session.rollback()
    await session.close()


@pytest.fixture
async def client(db_session):
    """Test client with overridden database dependency."""
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
    app.dependency_overrides.clear()
```

**Create `apps/api/tests/test_auth.py`:**

```python
"""Authentication endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_register(client):
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepass123",
        "organization_name": "Test Corp",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    # Register once
    await client.post("/api/v1/auth/register", json={
        "email": "dupe@example.com", "password": "pass12345678"
    })
    # Try again
    response = await client.post("/api/v1/auth/register", json={
        "email": "dupe@example.com", "password": "pass12345678"
    })
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client):
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com", "password": "pass12345678"
    })
    # Login
    response = await client.post("/api/v1/auth/login", data={
        "username": "login@example.com", "password": "pass12345678"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Step 8.2: Run Tests

```bash
cd apps/api
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

---

## Phase 9: Production Deployment

**Goal:** The application runs reliably on real infrastructure.

### Step 9.1: Infrastructure Checklist

| Component | Local Dev | Production |
|-----------|----------|------------|
| PostgreSQL | Docker container | Managed service (e.g., Supabase, Neon, AWS RDS) |
| Redis | Docker container | Managed service (e.g., Upstash, AWS ElastiCache) |
| Object Storage | MinIO container | Cloudflare R2 or AWS S3 |
| API | uvicorn (1 process) | Docker + load balancer (Gunicorn + Uvicorn workers) |
| Frontend | `npm run dev` | Vercel, or Docker + nginx |
| OCR Worker | Docker container (CPU) | Docker with GPU (NVIDIA) |
| Monitoring | stdout logs | Sentry + structured logging |

### Step 9.2: Production Docker Configuration

The development Docker Compose mounts source code and uses `--reload`. Production is different:

```yaml
# infra/docker/docker-compose.prod.yml

services:
  api:
    build:
      context: ../..
      dockerfile: apps/api/Dockerfile
    environment:
      ENVIRONMENT: production
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      # ... all from secrets manager
    command: >
      gunicorn app.main:app
      --worker-class uvicorn.workers.UvicornWorker
      --workers 4
      --bind 0.0.0.0:8000
      --access-logfile -
      --error-logfile -
    # NO volume mounts (use built image)
    # NO --reload
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "1.0"
```

**Key differences from dev:**
- `gunicorn` with multiple Uvicorn workers (not raw uvicorn with --reload)
- No volume mounts (code is baked into the image)
- Resource limits
- Environment from secrets manager, not `.env` file
- No Swagger docs (`/docs` and `/redoc` are disabled in production)

### Step 9.3: CI/CD Pipeline

A typical GitHub Actions pipeline:

```yaml
# .github/workflows/deploy.yml

name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e "apps/api[dev]"
      - run: pytest apps/api/tests/ -v
      - uses: actions/setup-node@v4
        with: { node-version: "22" }
      - run: cd apps/web && npm ci && npm run lint && npm run build

  deploy-api:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t fakturaai-api -f apps/api/Dockerfile .
      - run: docker push $REGISTRY/fakturaai-api:${{ github.sha }}
      # Deploy to your platform (Fly.io, Railway, AWS ECS, etc.)

  deploy-web:
    needs: test
    runs-on: ubuntu-latest
    steps:
      # If using Vercel: push to main triggers auto-deploy
      # If using Docker: build and push like the API
```

### Step 9.4: Production Checklist

Before going live, verify:

- [ ] **Secrets:** `JWT_SECRET_KEY` is a random 32+ character string (`openssl rand -hex 32`)
- [ ] **Secrets:** All passwords and API keys come from environment variables, not code
- [ ] **Database:** Migrations are applied (`alembic upgrade head`), not `create_all()`
- [ ] **Database:** Connection pool is sized correctly (`DATABASE_POOL_SIZE`)
- [ ] **CORS:** `allow_origins` lists only your actual domains (not `*`)
- [ ] **Swagger:** Docs are disabled (`ENVIRONMENT=production`)
- [ ] **HTTPS:** All traffic is encrypted (your load balancer/proxy handles this)
- [ ] **Sentry:** Error tracking is enabled (`SENTRY_DSN` is set)
- [ ] **Rate limiting:** Upload endpoints are rate-limited
- [ ] **File size:** Max upload size is enforced (20MB)
- [ ] **Backups:** Database has automated backups
- [ ] **Monitoring:** Health check endpoint is monitored
- [ ] **Logging:** Structured JSON logging for aggregation

---

## Development Workflow Best Practices

### Pre-Commit Hooks (Linting & Formatting)

Every commit is automatically linted before it lands. This is enforced via **Husky** (git hooks) + **lint-staged** (run linters only on staged files).

**What happens when you `git commit`:**

```
git commit -m "add user model"
  │
  ▼
Husky triggers .husky/pre-commit
  │
  ▼
lint-staged runs (only on staged files, fast!)
  │
  ├── *.py files → ruff check --fix → ruff format
  │   (auto-fixes import order, unused imports, formatting)
  │
  ├── apps/web/**/*.{ts,tsx,js,jsx} → eslint --fix
  │   (auto-fixes React/Next.js linting issues)
  │
  ▼
If all linters pass → commit proceeds
If any linter fails  → commit is blocked, fix the issues first
```

**Configuration lives in:**

| File | Purpose |
|------|---------|
| `package.json` → `lint-staged` | Defines which linters run on which file patterns |
| `.husky/pre-commit` | The git hook that triggers lint-staged |
| `scripts/lint-python.sh` | Wrapper that runs ruff from the Python venv |
| `scripts/lint-web.sh` | Wrapper that runs eslint from the web workspace |

**Convenience commands:**

```bash
# Lint everything (without committing)
npm run lint

# Lint + auto-fix everything
npm run lint:fix

# Format all Python code
npm run format

# Lint just the backend
npm run lint:api

# Lint just the frontend
npm run lint:web
```

**Bypassing hooks (use sparingly):**

```bash
# Skip pre-commit hook (e.g., WIP commits on your branch)
git commit --no-verify -m "wip: rough draft"
```

**Troubleshooting:**

- **"ruff not found"** → Make sure you've activated the venv: `source .venv/bin/activate` and installed dev deps: `pip install -e "apps/api[dev]"`
- **"eslint config not found"** → Run `npm install` from the project root
- **Hook not running** → Run `npx husky` to reinstall hooks (or `npm run prepare`)

### Feature Branch Workflow

```
main ──────────────────────────────────────────
  │                          │
  └── feature/auth ──────────┘
       │
       ├── commit: "add User and Organization models"
       ├── commit: "implement password hashing with Argon2"
       ├── commit: "implement register and login endpoints"
       ├── commit: "add auth middleware and dependencies"
       └── commit: "add auth tests"
```

1. **Create a branch** per phase (or per feature within a phase)
2. **Commit often** with descriptive messages
3. **Test before merging** - every commit should leave the app in a working state
4. **PR with description** - what changed, why, how to test

### Typical Development Session

```bash
# 1. Start infrastructure (once, keep running)
docker compose -f infra/docker/docker-compose.yml up -d postgres redis minio

# 2. Activate Python environment
source .venv/bin/activate

# 3. Start the API (auto-reloads on file changes)
cd apps/api
uvicorn app.main:app --reload

# 4. In another terminal, start the frontend
cd apps/web
npm run dev

# 5. Make changes → see them immediately
#    - Python changes: uvicorn auto-reloads
#    - Frontend changes: Next.js hot reloads
#    - Schema changes: restart uvicorn

# 6. Test your changes
curl http://localhost:8000/api/v1/...
# Or use the Swagger UI at http://localhost:8000/docs

# 7. Run tests before committing
cd apps/api && pytest tests/ -v

# 8. Commit
git add -A && git commit -m "implement feature X"
```

### When to Restart What

| Change | Restart needed? |
|--------|----------------|
| Edit a Python file (routers, schemas, services) | No - uvicorn auto-reloads |
| Edit `config.py` or add new settings | Yes - restart uvicorn (settings are cached with `@lru_cache`) |
| Edit `pyproject.toml` (add dependency) | Yes - `pip install -e ".[dev]"` then restart |
| Change a database model | Restart + run migration (or restart if using `create_all`) |
| Edit a React component | No - Next.js hot reloads |
| Edit `next.config.ts` | Yes - restart `npm run dev` |
| Change `docker-compose.yml` | `docker compose up -d` (recreates changed services) |
| Change `.env` | Restart the service that reads it |

### Debugging Checklist

When something doesn't work:

1. **Check the logs** - `uvicorn` terminal for API errors, browser console for frontend errors
2. **Check the database** - `docker exec -it fakturaai-postgres psql -U fakturaai -d fakturaai -c "SELECT * FROM invoices LIMIT 5;"`
3. **Check Redis** - `docker exec -it fakturaai-redis redis-cli PING`
4. **Check MinIO** - Open http://localhost:9011, verify files are there
5. **Check Swagger** - Open http://localhost:8000/docs, try the endpoint manually
6. **Check Celery** - Open http://localhost:5555 (Flower), check task status
