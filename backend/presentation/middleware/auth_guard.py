"""
JWT authentication dependency and role-based authorisation guard.

Design choice — CurrentUser is not a full User domain entity:
    Decoding the access token gives us user_id and role from the JWT payload.
    Loading the full User entity from the database on every authenticated request
    would add a DB round-trip to every API call. The role is already encoded in
    the token — re-reading it from the DB produces no new information for the
    15-minute access token lifetime. If a role changes in the database, the
    current token reflects the login-time role until it expires. Role changes
    requiring re-login is consistent with standard JWT practice.

Design choice — two separate dependencies, not one combined:
    get_current_user handles authentication only (who are you?).
    require_role handles authorisation only (can you do this?).
    Separating them enables personal plan routes to use get_current_user
    directly (any authenticated role passes), while role-specific routes
    compose require_role on top. If they were one combined function, a
    "any authenticated user" route would need a special sentinel value.

Design choice — require_role is a factory, not a dependency:
    Depends(require_role(UserRole.FITNESS_TRAINER)) is a per-role closure
    created at route definition time. The alternative (a single dependency
    that reads the role from a route parameter) is less explicit and harder
    to read in the route signature.
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.exceptions import ForbiddenError, UnauthorizedError
from core.security import decode_token
from domain.entities.enums import UserRole

# FastAPI's built-in Bearer scheme — reads the Authorization: Bearer <token> header.
# auto_error=False lets us produce our own UnauthorizedError instead of FastAPI's
# default 403 (which would be semantically wrong — missing credentials → 401).
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """
    Lightweight authenticated user context decoded from the access token.

    Carried through every authenticated request. Frozen so it cannot be
    accidentally mutated between the middleware and the service call.

    Design: id and role are the only fields needed by services for
    authorisation decisions. Services receive CurrentUser.id as the
    actor_id parameter — never the full User entity for auth purposes.
    """

    id: UUID
    role: UserRole


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> CurrentUser:
    """
    Decode the Bearer access token and return a CurrentUser.

    Raises UnauthorizedError (→ HTTP 401) if:
    - No Authorization header is present.
    - The token is expired.
    - The token signature is invalid.
    - The token type claim is not "access" (prevents refresh tokens being
      used as access tokens — the type claim is set by create_access_token).

    Does not touch the database.
    """
    if credentials is None:
        raise UnauthorizedError(
            "Authentication required. "
            "Provide an access token in the Authorization: Bearer header."
        )

    payload = decode_token(
        credentials.credentials
    )  # raises UnauthorizedError if invalid

    if payload.get("type") != "access":
        raise UnauthorizedError(
            "The provided token is a refresh token, not an access token. "
            "Use the access token returned by /auth/login or /auth/refresh."
        )

    user_id_raw = payload.get("sub")
    role_raw = payload.get("role")
    if not isinstance(user_id_raw, str) or not isinstance(role_raw, str):
        raise UnauthorizedError("Malformed token payload: missing sub or role claim")

    try:
        role = UserRole(role_raw)
    except ValueError:
        raise UnauthorizedError(
            f"Unrecognised role in token payload: '{role_raw}'"
        ) from None

    return CurrentUser(id=UUID(user_id_raw), role=role)


def require_role(*roles: UserRole) -> Callable[..., Coroutine[Any, Any, CurrentUser]]:
    """
    Return a FastAPI dependency that enforces role membership.

    Usage in routes:
        current_user: CurrentUser = Depends(require_role(UserRole.FITNESS_TRAINER))
        current_user: CurrentUser = Depends(require_role(
            UserRole.MASTER_COACH, UserRole.SUPER_ADMIN
        ))

    Raises ForbiddenError (→ HTTP 403) if the authenticated user's role
    is not in the allowed set.
    """

    async def _check_role(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role not in roles:
            allowed = [r.value for r in roles]
            raise ForbiddenError(
                f"This endpoint requires one of the following roles: {allowed}. "
                f"Your role is '{current_user.role.value}'."
            )
        return current_user

    return _check_role
