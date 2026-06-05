"""
Unit tests for SuperAdminService.

Key invariants tested:
- create_user hashes the password and rejects invalid roles.
- deactivate_user is idempotent and revokes all refresh tokens.
- override_workout_programme requires a non-empty reason, writes a version
  snapshot, and logs the activity.
- Invalid role strings raise ValidationError (not a raw ValueError).
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from application.services.assignment_service import AssignmentService
from application.services.super_admin_service import SuperAdminService
from core.exceptions import NotFoundError, ValidationError
from domain.entities.enums import UserRole
from domain.interfaces.repositories import (
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IPlanVersionRepository,
    IRefreshTokenRepository,
    IUserRepository,
    IWorkoutProgramRepository,
)
from tests.unit.conftest import make_user, make_workout_program

PATCH_BASE = "application.services.super_admin_service"


@pytest.fixture
def user_repo() -> AsyncMock:
    return AsyncMock(spec=IUserRepository)


@pytest.fixture
def token_repo() -> AsyncMock:
    return AsyncMock(spec=IRefreshTokenRepository)


@pytest.fixture
def workout_repo() -> AsyncMock:
    return AsyncMock(spec=IWorkoutProgramRepository)


@pytest.fixture
def diet_repo() -> AsyncMock:
    return AsyncMock(spec=IDietPlanRepository)


@pytest.fixture
def plan_version_repo() -> AsyncMock:
    return AsyncMock(spec=IPlanVersionRepository)


@pytest.fixture
def activity_log_repo() -> AsyncMock:
    return AsyncMock(spec=IPlanActivityLogRepository)


@pytest.fixture
def assignment_service() -> AsyncMock:
    """Mock AssignmentService — not its repository, the service itself."""
    mock = AsyncMock(spec=AssignmentService)
    return mock


@pytest.fixture
def service(
    user_repo: AsyncMock,
    token_repo: AsyncMock,
    workout_repo: AsyncMock,
    diet_repo: AsyncMock,
    plan_version_repo: AsyncMock,
    activity_log_repo: AsyncMock,
    assignment_service: AsyncMock,
) -> SuperAdminService:
    return SuperAdminService(
        user_repo=user_repo,
        token_repo=token_repo,
        workout_repo=workout_repo,
        diet_repo=diet_repo,
        plan_version_repo=plan_version_repo,
        activity_log_repo=activity_log_repo,
        assignment_service=assignment_service,
    )


# ── create_user ───────────────────────────────────────────────────────────────


class TestCreateUser:
    async def test_creates_user_with_hashed_password(
        self, service: SuperAdminService, user_repo: AsyncMock
    ) -> None:
        created_user = make_user(role=UserRole.FITNESS_TRAINER)
        user_repo.save.return_value = created_user

        with patch(f"{PATCH_BASE}.hash_password", return_value="$2b$12$hashed"):
            result = await service.create_user(
                email="trainer@example.com",
                password="plaintext",
                full_name="Alice Trainer",
                role="fitness_trainer",
            )

        assert result == created_user
        saved = user_repo.save.call_args[0][0]
        assert saved.password_hash == "$2b$12$hashed"
        assert saved.is_active is True
        assert saved.is_deleted is False

    async def test_email_is_lowercased_and_stripped(
        self, service: SuperAdminService, user_repo: AsyncMock
    ) -> None:
        user_repo.save.side_effect = lambda u: u

        with patch(f"{PATCH_BASE}.hash_password", return_value="hash"):
            result = await service.create_user(
                email="  ADMIN@EXAMPLE.COM  ",
                password="pw",
                full_name="Admin",
                role="super_admin",
            )

        assert result.email == "admin@example.com"

    async def test_invalid_role_raises_validation_error(
        self, service: SuperAdminService
    ) -> None:
        with pytest.raises(ValidationError, match="not a valid role"):
            await service.create_user(
                email="x@example.com",
                password="pw",
                full_name="X",
                role="superuser",  # not a valid UserRole value
            )

    async def test_all_valid_roles_accepted(
        self, service: SuperAdminService, user_repo: AsyncMock
    ) -> None:
        user_repo.save.side_effect = lambda u: u

        for role in UserRole:
            with patch(f"{PATCH_BASE}.hash_password", return_value="hash"):
                result = await service.create_user(
                    email=f"{role.value}@example.com",
                    password="pw",
                    full_name=role.value,
                    role=role.value,
                )
            assert result.role == role


# ── deactivate_user ───────────────────────────────────────────────────────────


class TestDeactivateUser:
    async def test_deactivates_user_and_revokes_tokens(
        self, service: SuperAdminService, user_repo: AsyncMock, token_repo: AsyncMock
    ) -> None:
        user = make_user(is_active=True)
        user_repo.get_by_id.return_value = user
        user_repo.save.side_effect = lambda u: u

        await service.deactivate_user(user.id)

        saved = user_repo.save.call_args[0][0]
        assert saved.is_active is False
        token_repo.revoke_all_for_user.assert_called_once()
        call_kwargs = token_repo.revoke_all_for_user.call_args.kwargs
        assert call_kwargs["user_id"] == user.id

    async def test_deactivate_is_idempotent(
        self,
        service: SuperAdminService,
        user_repo: AsyncMock,
        token_repo: AsyncMock,
    ) -> None:
        """Calling deactivate on an already-inactive user is a no-op."""
        already_inactive = make_user(is_active=False)
        user_repo.get_by_id.return_value = already_inactive

        await service.deactivate_user(already_inactive.id)

        user_repo.save.assert_not_called()
        token_repo.revoke_all_for_user.assert_not_called()

    async def test_raises_when_user_not_found(
        self, service: SuperAdminService, user_repo: AsyncMock
    ) -> None:
        user_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.deactivate_user(uuid4())


# ── override_workout_programme ────────────────────────────────────────────────


class TestOverrideWorkoutProgramme:
    async def test_writes_version_snapshot_and_updates_programme(
        self,
        service: SuperAdminService,
        workout_repo: AsyncMock,
        plan_version_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        admin_id = uuid4()
        program = make_workout_program(uuid4())
        workout_repo.get_by_id.return_value = program
        workout_repo.save.side_effect = lambda p: p
        plan_version_repo.save.return_value = MagicMock()
        activity_log_repo.save.return_value = MagicMock()

        result = await service.override_workout_programme(
            program_id=program.id,
            override_reason="Correcting coach data entry error",
            admin_id=admin_id,
        )

        assert result.last_modified_by == admin_id
        assert result.override_reason == "Correcting coach data entry error"
        plan_version_repo.save.assert_called_once()
        activity_log_repo.save.assert_called_once()

    async def test_snapshot_captures_plan_id_and_version(
        self,
        service: SuperAdminService,
        workout_repo: AsyncMock,
        plan_version_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        program = make_workout_program(uuid4(), version=3)
        workout_repo.get_by_id.return_value = program
        workout_repo.save.side_effect = lambda p: p
        plan_version_repo.save.return_value = MagicMock()
        activity_log_repo.save.return_value = MagicMock()

        await service.override_workout_programme(
            program_id=program.id,
            override_reason="Fix",
            admin_id=uuid4(),
        )

        version_entity = plan_version_repo.save.call_args[0][0]
        assert version_entity.snapshot["plan_id"] == str(program.id)
        assert version_entity.snapshot["version"] == 3
        assert version_entity.change_reason == "Fix"

    async def test_empty_reason_raises_validation_error(
        self, service: SuperAdminService
    ) -> None:
        with pytest.raises(ValidationError, match="reason is required"):
            await service.override_workout_programme(
                program_id=uuid4(), override_reason="  ", admin_id=uuid4()
            )

    async def test_raises_when_programme_not_found(
        self, service: SuperAdminService, workout_repo: AsyncMock
    ) -> None:
        workout_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            await service.override_workout_programme(
                program_id=uuid4(),
                override_reason="Valid reason",
                admin_id=uuid4(),
            )


# ── list_clients ──────────────────────────────────────────────────────────────


class TestListClients:
    async def test_returns_paginated_slice(
        self, service: SuperAdminService, user_repo: AsyncMock
    ) -> None:
        all_clients = [make_user(role=UserRole.CLIENT) for _ in range(50)]
        user_repo.list_clients.return_value = all_clients

        page_one = await service.list_clients(limit=20, offset=0)
        page_two = await service.list_clients(limit=20, offset=20)

        assert len(page_one) == 20
        assert len(page_two) == 20
        assert page_one[0].id != page_two[0].id
