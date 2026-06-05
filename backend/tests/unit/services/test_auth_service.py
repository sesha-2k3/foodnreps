"""
Unit tests for AuthService.

Security functions (verify_password, create_access_token, etc.) are patched
so tests run without bcrypt or JWT signing overhead and without a real settings
object being needed for JWT_SECRET at test time.

All repository calls use AsyncMock(spec=I...Repository) so any typo in a method
name raises AttributeError immediately rather than silently returning a Mock.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from application.services.auth_service import AuthService
from core.exceptions import InactiveUserError, UnauthorizedError
from domain.entities.enums import UserRole
from domain.interfaces.repositories import IRefreshTokenRepository, IUserRepository
from tests.unit.conftest import make_refresh_token, make_user

PATCH_BASE = "application.services.auth_service"


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock(spec=IUserRepository)


@pytest.fixture
def token_repo() -> AsyncMock:
    return AsyncMock(spec=IRefreshTokenRepository)


@pytest.fixture
def service(user_repo: AsyncMock, token_repo: AsyncMock) -> AuthService:
    return AuthService(user_repo=user_repo, token_repo=token_repo)


# ── login ─────────────────────────────────────────────────────────────────────


class TestLogin:
    async def test_returns_token_pair_on_success(
        self, service: AuthService, user_repo: AsyncMock, token_repo: AsyncMock
    ) -> None:
        client = make_user(role=UserRole.CLIENT)
        user_repo.get_by_email.return_value = client
        token_repo.save.return_value = make_refresh_token(client.id)

        with (
            patch(f"{PATCH_BASE}.verify_password", return_value=True),
            patch(f"{PATCH_BASE}.create_access_token", return_value="access.jwt"),
            patch(f"{PATCH_BASE}.create_refresh_token_jwt", return_value="refresh.jwt"),
        ):
            access, refresh = await service.login("test@example.com", "correct-pw")

        assert access == "access.jwt"
        assert refresh == "refresh.jwt"

    async def test_raises_on_wrong_password(
        self, service: AuthService, user_repo: AsyncMock
    ) -> None:
        user_repo.get_by_email.return_value = make_user()

        with (
            patch(f"{PATCH_BASE}.verify_password", return_value=False),
            pytest.raises(UnauthorizedError, match="Invalid email or password"),
        ):
            await service.login("test@example.com", "wrong")

    async def test_raises_on_unknown_email(
        self, service: AuthService, user_repo: AsyncMock
    ) -> None:
        user_repo.get_by_email.return_value = None

        with (
            patch(f"{PATCH_BASE}.verify_password", return_value=True),
            pytest.raises(UnauthorizedError, match="Invalid email or password"),
        ):
            await service.login("unknown@example.com", "pw")

    async def test_raises_on_inactive_user(
        self, service: AuthService, user_repo: AsyncMock
    ) -> None:
        inactive = make_user(is_active=False)
        user_repo.get_by_email.return_value = inactive

        with (
            patch(f"{PATCH_BASE}.verify_password", return_value=True),
            pytest.raises(InactiveUserError),
        ):
            await service.login("test@example.com", "pw")

    async def test_saves_refresh_token_entity(
        self, service: AuthService, user_repo: AsyncMock, token_repo: AsyncMock
    ) -> None:
        client = make_user()
        user_repo.get_by_email.return_value = client
        token_repo.save.return_value = make_refresh_token(client.id)

        with (
            patch(f"{PATCH_BASE}.verify_password", return_value=True),
            patch(f"{PATCH_BASE}.create_access_token", return_value="a"),
            patch(f"{PATCH_BASE}.create_refresh_token_jwt", return_value="r"),
        ):
            await service.login("test@example.com", "pw")

        token_repo.save.assert_called_once()
        saved_token = token_repo.save.call_args[0][0]
        assert saved_token.user_id == client.id
        assert saved_token.is_revoked is False


# ── refresh ───────────────────────────────────────────────────────────────────


class TestRefresh:
    async def test_rotates_token_and_returns_new_pair(
        self, service: AuthService, user_repo: AsyncMock, token_repo: AsyncMock
    ) -> None:
        token_id = uuid4()
        user = make_user()
        stored = make_refresh_token(user.id, token_id=token_id)

        user_repo.get_by_id.return_value = user
        token_repo.get_by_token_id.return_value = stored
        token_repo.save.return_value = make_refresh_token(user.id)

        payload = {
            "type": "refresh",
            "jti": str(token_id),
            "sub": str(user.id),
        }

        with (
            patch(f"{PATCH_BASE}.decode_token", return_value=payload),
            patch(f"{PATCH_BASE}.create_access_token", return_value="new.access"),
            patch(f"{PATCH_BASE}.create_refresh_token_jwt", return_value="new.refresh"),
        ):
            access, refresh = await service.refresh("old.refresh.jwt")

        assert access == "new.access"
        assert refresh == "new.refresh"
        token_repo.revoke.assert_called_once()

    async def test_raises_on_revoked_token(
        self, service: AuthService, user_repo: AsyncMock, token_repo: AsyncMock
    ) -> None:
        user = make_user()
        revoked = make_refresh_token(user.id, is_revoked=True)
        token_repo.get_by_token_id.return_value = revoked
        token_id = uuid4()

        with patch(
            f"{PATCH_BASE}.decode_token",
            return_value={
                "type": "refresh",
                "jti": str(token_id),
                "sub": str(user.id),
            },
        ), pytest.raises(UnauthorizedError, match="revoked"):
            await service.refresh("bad.token")

    async def test_raises_on_non_refresh_token_type(self, service: AuthService) -> None:
        with (
            patch(
                f"{PATCH_BASE}.decode_token",
                return_value={
                    "type": "access",  # wrong type
                    "sub": str(uuid4()),
                },
            ),
            pytest.raises(UnauthorizedError, match="not a refresh token"),
        ):
            await service.refresh("access.token.used.as.refresh")

    async def test_raises_on_inactive_user_during_refresh(
        self, service: AuthService, user_repo: AsyncMock, token_repo: AsyncMock
    ) -> None:
        user = make_user(is_active=False)
        token = make_refresh_token(user.id)
        token_repo.get_by_token_id.return_value = token
        user_repo.get_by_id.return_value = user

        with patch(
            f"{PATCH_BASE}.decode_token",
            return_value={
                "type": "refresh",
                "jti": str(token.token_id),
                "sub": str(user.id),
            },
        ), pytest.raises(InactiveUserError):
            await service.refresh("any.token")


# ── logout ────────────────────────────────────────────────────────────────────


class TestLogout:
    async def test_revokes_valid_token(
        self, service: AuthService, token_repo: AsyncMock
    ) -> None:
        token_id = uuid4()
        user_id = uuid4()
        stored = make_refresh_token(user_id, token_id=token_id)
        token_repo.get_by_token_id.return_value = stored

        with patch(
            f"{PATCH_BASE}.decode_token_ignore_expiry",
            return_value={
                "type": "refresh",
                "jti": str(token_id),
                "sub": str(user_id),
            },
        ):
            await service.logout("some.refresh.jwt")

        token_repo.revoke.assert_called_once()

    async def test_silent_on_malformed_token(
        self, service: AuthService, token_repo: AsyncMock
    ) -> None:
        """Logout must not raise even if the token is completely malformed."""
        with patch(
            f"{PATCH_BASE}.decode_token_ignore_expiry",
            side_effect=UnauthorizedError("Malformed"),
        ):
            await service.logout("garbage")  # must not raise

        token_repo.revoke.assert_not_called()

    async def test_silent_when_token_already_revoked(
        self, service: AuthService, token_repo: AsyncMock
    ) -> None:
        token_id = uuid4()
        already_revoked = make_refresh_token(
            uuid4(), token_id=token_id, is_revoked=True
        )
        token_repo.get_by_token_id.return_value = already_revoked

        with patch(
            f"{PATCH_BASE}.decode_token_ignore_expiry",
            return_value={
                "jti": str(token_id),
            },
        ):
            await service.logout("already.gone")

        token_repo.revoke.assert_not_called()

    async def test_silent_when_token_not_found(
        self, service: AuthService, token_repo: AsyncMock
    ) -> None:
        token_id = uuid4()
        token_repo.get_by_token_id.return_value = None

        with patch(
            f"{PATCH_BASE}.decode_token_ignore_expiry",
            return_value={
                "jti": str(token_id),
            },
        ):
            await service.logout("not.in.db")

        token_repo.revoke.assert_not_called()
