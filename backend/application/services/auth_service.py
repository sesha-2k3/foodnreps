"""
AuthService — owns the complete session lifecycle.

Responsibilities:
    login    — verify credentials, issue (access_token, refresh_token) pair
    refresh  — rotate refresh token, issue new (access_token, refresh_token) pair
    logout   — revoke refresh token

Does NOT own:
    User creation or profile management (SuperAdminService)
    Any plan or assignment logic

Design choice — does not inherit from IAuthService:
    IAuthService.refresh was originally declared -> str. Sprint 3 implementation
    established that the correct return type is tuple[str, str] (both tokens).
    Rather than patching mypy strict compliance with a covariant override, this
    concrete class declares the correct signatures directly. IAuthService has been
    updated in domain/interfaces/services.py to match. Sprint 4 route handlers
    will inject AuthService directly; IAuthService is available for mock-based
    testing via the interface's corrected signature.

Design choice — token rotation on every refresh:
    On each use, the old refresh token is revoked and a brand-new one is issued.
    If a refresh token is stolen and used by an attacker, the legitimate user's
    next refresh finds their token already revoked — a detectable signal of
    compromise. Without rotation, a stolen token silently grants 7 days of access.

Design choice — login does not revoke previous sessions:
    Logging in from a new device does not invalidate existing sessions. Each
    device holds its own refresh token. A "log out all devices" path (revoke_all)
    is exposed via the repository but is only triggered by account deactivation
    or password change in Sprint 4. This is a product decision — silent session
    revocation on login would surprise multi-device users.

Design choice — logout is idempotent and silent on errors:
    If the token is already revoked, expired, or malformed, logout returns None.
    The caller's intent (end this session) is accomplished regardless of the
    token's current state. Raising an error on logout would prevent users from
    successfully logging out if their token had already been rotated away.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from core.config import settings
from core.exceptions import InactiveUserError, UnauthorizedError
from core.security import (
    create_access_token,
    create_refresh_token_jwt,
    decode_token,
    decode_token_ignore_expiry,
    verify_password,
)
from domain.entities.user import RefreshToken
from domain.interfaces.repositories import IRefreshTokenRepository, IUserRepository


class AuthService:
    """Concrete implementation of the authentication and session lifecycle."""

    def __init__(
        self,
        user_repo: IUserRepository,
        token_repo: IRefreshTokenRepository,
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo

    async def login(self, email: str, password: str) -> tuple[str, str]:
        """
        Verify credentials and return (access_token_jwt, refresh_token_jwt).

        The error message on credential failure is deliberately vague —
        "Invalid email or password" — so the response cannot be used to
        enumerate which emails are registered in the system.
        """
        user = await self._user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            raise InactiveUserError(
                "This account has been deactivated. "
                "Contact your administrator to restore access."
            )

        return await self._issue_token_pair(user.id, user.role.value)

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """
        Validate and rotate the refresh token.
        Returns (new_access_token_jwt, new_refresh_token_jwt).

        Steps:
        1. Decode and verify the incoming JWT (signature + expiry).
        2. Confirm the token type claim is "refresh".
        3. Look up the stored RefreshToken by jti (token_id).
        4. Check the stored record is not revoked or expired.
        5. Verify the user account is still active.
        6. Revoke the old token.
        7. Issue a fresh token pair.
        """
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Provided token is not a refresh token")

        token_id_raw = payload.get("jti")
        user_id_raw = payload.get("sub")
        if not isinstance(token_id_raw, str) or not isinstance(user_id_raw, str):
            raise UnauthorizedError("Malformed token payload")

        token_id = UUID(token_id_raw)
        user_id = UUID(user_id_raw)

        stored = await self._token_repo.get_by_token_id(token_id)
        if stored is None or not stored.is_valid:
            raise UnauthorizedError(
                "Refresh token is invalid or has been revoked. Please log in again."
            )

        user = await self._user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InactiveUserError("Account has been deactivated")

        # Revoke the consumed token before issuing the new pair
        await self._token_repo.revoke(
            token_id=token_id,
            revoked_at=datetime.now(tz=UTC),
        )

        return await self._issue_token_pair(user.id, user.role.value)

    async def logout(self, refresh_token: str) -> None:
        """
        Revoke the refresh token. Idempotent — no error if already revoked,
        expired, or not found.
        """
        try:
            payload = decode_token_ignore_expiry(refresh_token)
        except UnauthorizedError:
            # Malformed token — nothing to revoke; logout intent is still satisfied
            return

        token_id_raw = payload.get("jti")
        if not isinstance(token_id_raw, str):
            return

        token_id = UUID(token_id_raw)
        stored = await self._token_repo.get_by_token_id(token_id)
        if stored is not None and not stored.is_revoked:
            await self._token_repo.revoke(
                token_id=token_id,
                revoked_at=datetime.now(tz=UTC),
            )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _issue_token_pair(self, user_id: UUID, role: str) -> tuple[str, str]:
        """
        Persist a new RefreshToken entity and encode both JWTs.
        Called by login() and refresh() after all validation has passed.
        """
        token_id = uuid4()
        expires_at = datetime.now(tz=UTC) + timedelta(
            days=settings.refresh_token_expire_days
        )
        refresh_entity = RefreshToken(
            id=uuid4(),
            user_id=user_id,
            token_id=token_id,
            is_revoked=False,
            expires_at=expires_at,
            revoked_at=None,
            created_at=datetime.now(tz=UTC),
        )
        await self._token_repo.save(refresh_entity)

        access_jwt = create_access_token(user_id=user_id, role=role)
        refresh_jwt = create_refresh_token_jwt(user_id=user_id, token_id=token_id)
        return access_jwt, refresh_jwt
