"""
Pytest shared fixtures — Sprint 2.

Why asyncio.run() for schema setup:
    asyncpg ties every connection to the event loop that created it.
    pytest-asyncio (0.23+) creates a separate event loop per test function.
    A session-scoped async engine fixture runs on the first test's loop —
    every subsequent test runs on a different loop and asyncpg rejects the
    stale connections with RuntimeError.

    Fix: asyncio.run() creates its own isolated loop for schema setup,
    completely outside pytest-asyncio's loop management. Each test then
    creates its own engine + session on its own loop — no cross-loop
    contamination possible.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.config import settings
from infrastructure.db import models as _models  # noqa: F401  registers all models
from infrastructure.db.base import Base


@pytest.fixture(scope="session", autouse=True)
def setup_test_database() -> Generator[None, None, None]:
    """
    Synchronous session-scoped fixture.
    Runs once before any test, drops+creates all tables.
    Runs once after all tests, drops all tables.

    Deliberately synchronous — asyncio.run() uses its own isolated event
    loop that is created and destroyed independently of pytest-asyncio's
    per-test loops. This is what prevents every asyncpg event loop error.
    """
    if settings.test_database_url is None:
        pytest.skip("TEST_DATABASE_URL not set — skipping integration tests")

    async def _create() -> None:
        engine = create_async_engine(str(settings.test_database_url))
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    async def _drop() -> None:
        engine = create_async_engine(str(settings.test_database_url))
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_create())
    yield
    asyncio.run(_drop())


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Function-scoped session. Each test gets a fresh engine created on
    that test's own event loop — no cross-loop contamination.

    Repositories call flush() but never commit(), so rollback() after
    the test undoes every change and leaves the DB clean for the next test.
    """
    engine = create_async_engine(str(settings.test_database_url), echo=False)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()
    await engine.dispose()
