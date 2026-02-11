"""
Async database engine and session management.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

# Initialize settings
settings = get_settings()

# The engine manages a pool of database connections
# pool_size=20 means 20 persistent connections are ready to go.
# max_overflow = 10 means 10 more can be created temmporarily during spikes
# When a spike ends, overflow connections are closed.
engine = create_async_engine(
    url=settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,  # Log SQL queries in debug mode
)

# A session factory. Each call to async_session() creates a new session
# bound to one connection from the pool.
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit (avoid lazy-load issues)
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session

    Usage in a router:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    The session is automatically closed when the request ends,
    even if an exception occurs
    :return: Asynchronous Session object
    :rtype: AsyncGenerator[AsyncSession, None]
    """
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
