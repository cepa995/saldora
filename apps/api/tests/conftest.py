"""
Shared test fixtures.

Key ideas:
    1. Tests use a SEPARATE database so they never touch the development data.
    2. Tables are created once per session (fast). Between tests, all rows are
       deleted so each test starts with a clean slate.
    3. We override FastAPI's `get_db` dependency so the app uses the test DB.

Why NullPool?
    asyncpg connections are bound to the event loop they were created on.
    With a connection pool, a connection created in one async context (e.g.,
    the session-scoped engine fixture) could be reused in a different context
    (the test function), causing "attached to a different loop" errors.
    NullPool creates a fresh connection every time and discards it after use,
    so there is never a stale loop reference.
"""

import os

# Ensure rate limiting is disabled during tests — must be set BEFORE app import
os.environ["TESTING"] = "1"

from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import get_db
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://saldora:saldora_dev@localhost:5433/saldora_test",
)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    """Create a test database engine and tables (once per session)."""
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        from sqlalchemy import text

        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP client that talks to our FastAPI app *in-process*.

    How this works:
    - We create a session factory bound to the test engine.
    - The get_db override creates a NEW session per request, just like
      production. This means each request gets its own connection created
      on the CURRENT event loop — no stale loop references.
    - After the test, all rows are deleted (not rolled back) so the next
      test starts with empty tables.
    """
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()

    # Clean up all data between tests (order respects foreign keys)
    async with test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
        await conn.commit()


@pytest.fixture(autouse=True)
def _mock_emails():
    """Prevent all email sending during tests.

    Auto-applied to every test so no real Resend API calls are made.
    """
    with patch("app.services.email._send_email", return_value=None):
        yield
