"""
Async SQLAlchemy engine and session factory.

Design choice — async engine, not synchronous:
    FastAPI runs on ASGI (async). A synchronous SQLAlchemy call inside an async
    route handler blocks the entire event loop — one slow DB query freezes every
    concurrent request on that worker. `create_async_engine` + `AsyncSession`
    allow DB I/O to happen concurrently with other work without blocking.

Design choice — `expire_on_commit=False`:
    By default, SQLAlchemy marks all objects as "expired" after `session.commit()`,
    forcing a fresh SELECT on the next attribute access. In async SQLAlchemy,
    accessing an expired object outside a session context raises
    `MissingGreenlet` / `DetachedInstanceError`. Setting `expire_on_commit=False`
    keeps objects usable after commit without an extra round-trip to the DB.
    This is the correct default for async FastAPI applications.

Design choice — pool configuration:
    `pool_size=10` — max persistent connections.
    `max_overflow=20` — additional connections allowed under burst load (30 total).
    `pool_timeout=30` — wait up to 30s for a connection before raising an error.
    `pool_recycle=1800` — recycle connections every 30 min to avoid stale connections
    from PostgreSQL's idle timeout or network intermediaries.

Design choice — `get_session` as an async generator with explicit commit/rollback:
    The generator yields the session, then commits on success or rolls back on
    any exception. This means route handlers never need to call `session.commit()`
    or `session.rollback()` manually — the dependency handles it. This pattern
    ensures every request is a clean atomic unit.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

# str() required: pydantic v2 PostgresDsn is not a plain string
engine = create_async_engine(
    str(settings.database_url),
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,
    echo=settings.debug,  # logs all SQL when DEBUG=true — never in production
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # see module docstring
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    Usage in routes (Sprint 4):
        async def my_route(session: AsyncSession = Depends(get_session)):
            ...

    The session is committed on success and rolled back on any exception,
    then closed when the request finishes. Route handlers never call
    session.commit() or session.rollback() directly.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
