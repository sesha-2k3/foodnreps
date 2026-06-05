"""
Pytest shared fixtures — Sprint 2 update.

Adds test_engine and db_session for integration tests.

Design choice — session-scoped engine, function-scoped session:
    Creating the test DB schema is expensive (many tables, many enum types).
    The engine and schema creation is session-scoped: it runs once for the
    entire test session. Individual test sessions are function-scoped:
    each test gets a fresh transaction that rolls back after the test,
    leaving the DB in a clean state for the next test.

Design choice — transaction rollback not table truncation:
    Rolling back a transaction after each test is faster than truncating
    tables, does not require knowing which tables have data, and handles
    FK constraints automatically (child rows disappear with the parent
    when the transaction is rolled back).

Setup required before running integration tests:
    docker exec food_n_reps_db psql -U food_n_reps -c "CREATE DATABASE food_n_reps_test;"
"""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings
from infrastructure.db.base import Base
from infrastructure.db import models as _models  # noqa: F401  registers all models on Base


# ── Session-scoped: create schema once per test run ───────────────────────────

@pytest.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Creates all tables in the test database at session start,
    drops them all at session end.

    Using drop_all + create_all (not Alembic) keeps integration tests
    independent of migration history. Tests verify that the ORM models
    are correct, not that migrations are correct (that is verified by
    running `make upgrade` against the real DB).
    """
    if settings.test_database_url is None:
        pytest.skip("TEST_DATABASE_URL not set — skipping integration tests")

    engine = create_async_engine(str(settings.test_database_url), echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)   # clean slate
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ── Function-scoped: rolled-back transaction per test ─────────────────────────

@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a database session for one test. Every change made during the
    test is rolled back when the test finishes, leaving the DB clean.

    The session is backed by a real connection with an open transaction.
    flush() works normally (changes are visible within the session).
    commit() inside a test would break isolation — tests should never call it.
    """
    async with test_engine.connect() as connection:
        await connection.begin()
        session_factory = async_sessionmaker(
            connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with session_factory() as session:
            yield session
        await connection.rollback()


# ── Sprint 4: HTTP test client (add when routes are built) ────────────────────
#
# @pytest.fixture
# async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
#     from httpx import AsyncClient, ASGITransport
#     from main import app
#     from presentation.api.dependencies import get_db
#     app.dependency_overrides[get_db] = lambda: db_session
#     async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
#         yield client
#     app.dependency_overrides.clear()
