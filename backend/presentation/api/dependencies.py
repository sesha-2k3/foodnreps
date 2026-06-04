"""
FastAPI dependency injection wiring.

Design choice — central dependencies file:
    All `Depends()` functions live here. Routes import from this module,
    not from the service or repository modules directly. This means:
    - Route files have one import point for all dependencies
    - Swapping implementations (e.g., mock service in tests) changes one file
    - The dependency graph is readable in one place

Sprint 0: DB session dependency only.
Sprint 3: Service dependencies (get_workout_service, get_diet_service, etc.)
Sprint 4: Auth dependencies (get_current_user, require_role)

Each dependency is documented with its design rationale inline.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_session


# ── Database session ──────────────────────────────────────────────────────────

async def get_db(
    session: AsyncSession = Depends(get_session),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a database session for a single request.

    Design choice — re-exported through this module:
        Routes depend on `get_db`, not on `get_session` from infrastructure.
        This keeps the presentation layer's dependency on infrastructure
        contained to this one file — not scattered across every route module.
        If the session strategy changes, only this file changes.
    """
    yield session


# ── Sprint 4: Auth dependencies ───────────────────────────────────────────────
#
# async def get_current_user(
#     token: str = Depends(oauth2_scheme),
#     session: AsyncSession = Depends(get_db),
# ) -> User:
#     """Decode the JWT access token and return the authenticated User entity."""
#     ...
#
# def require_role(*roles: Role) -> Callable:
#     """
#     Factory that returns a dependency checking the current user's role.
#
#     Design choice — factory pattern for role guards:
#         `require_role(Role.FITNESS_TRAINER, Role.MASTER_COACH)` returns a
#         FastAPI dependency that passes if the user has either role.
#         This avoids per-route if/else role checks and makes the required
#         role visible in the route signature.
#     """
#     async def check_role(current_user: User = Depends(get_current_user)) -> User:
#         if current_user.role not in roles:
#             raise ForbiddenError(f"Role {current_user.role!r} cannot access this resource")
#         return current_user
#     return check_role


# ── Sprint 3: Service dependencies ────────────────────────────────────────────
#
# async def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
#     return AuthService(
#         user_repo=UserRepository(session),
#         token_repo=RefreshTokenRepository(session),
#     )
#
# async def get_workout_service(session: AsyncSession = Depends(get_db)) -> WorkoutService:
#     return WorkoutService(
#         program_repo=WorkoutProgramRepository(session),
#         factory=WorkoutFactory(),
#     )
#
# async def get_assignment_service(session: AsyncSession = Depends(get_db)) -> AssignmentService:
#     return AssignmentService(
#         assignment_repo=ClientStaffAssignmentRepository(session),
#         user_repo=UserRepository(session),
#     )
