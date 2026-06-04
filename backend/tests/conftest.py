"""
Pytest shared fixtures and configuration.

Sprint 0: Async test setup only.
Sprint 2: Add test_engine, test_session, test_client fixtures
          once ORM models and migrations exist.

Design choice — asyncio_mode = "auto" (set in pyproject.toml):
    All async test functions run automatically without needing
    @pytest.mark.asyncio on each one. Set in pyproject.toml so it applies
    to the entire test suite consistently.

Design choice — test database isolation strategy (Sprint 2):
    Each test gets a transaction that is rolled back after the test completes.
    This means:
    - No test data leaks between tests
    - No need to truncate tables between tests
    - Tests run faster (no schema create/drop per test)
    The technique: wrap each test in a SAVEPOINT, roll back to it after.
"""

import pytest


# ── Sprint 2: add these fixtures once ORM models exist ────────────────────────
#
# from sqlalchemy.ext.asyncio import (
#     AsyncConnection,
#     AsyncEngine,
#     AsyncSession,
#     async_sessionmaker,
#     create_async_engine,
# )
# from httpx import AsyncClient, ASGITransport
# from core.config import settings
# from infrastructure.db.models import Base
# from main import app
# from presentation.api.dependencies import get_db
#
#
# @pytest.fixture(scope="session")
# async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
#     """
#     Session-scoped test engine pointing at the test database.
#     Creates all tables before the session, drops them after.
#     """
#     engine = create_async_engine(str(settings.test_database_url))
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     yield engine
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)
#     await engine.dispose()
#
#
# @pytest.fixture
# async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
#     """
#     Function-scoped DB session wrapped in a rolled-back transaction.
#     Every test starts clean; no teardown truncation needed.
#     """
#     async with test_engine.connect() as conn:
#         await conn.begin()
#         session = AsyncSession(bind=conn, expire_on_commit=False)
#         yield session
#         await session.close()
#         await conn.rollback()
#
#
# @pytest.fixture
# async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
#     """
#     FastAPI TestClient with the real DB session overridden by the test session.
#     Allows route integration tests to run against a transaction-isolated DB.
#     """
#     app.dependency_overrides[get_db] = lambda: db_session
#     async with AsyncClient(
#         transport=ASGITransport(app=app),
#         base_url="http://test",
#     ) as client:
#         yield client
#     app.dependency_overrides.clear()


# ── Sprint 1: domain unit test helpers ────────────────────────────────────────
# No fixtures needed — domain entities are plain dataclasses.
# Tests instantiate them directly without any fixtures.
