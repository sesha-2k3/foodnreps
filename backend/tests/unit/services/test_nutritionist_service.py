"""
Unit tests for NutritionistService.

Mirrors the structure of test_fitness_trainer_service.py for the diet domain.
Key invariants:
- All writes are gated by an active NUTRITIONIST assignment for the client.
- Deactivate-before-create for diet plans.
- Entry add/delete with activity log confirmation.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from application.factories.diet_factory import DietFactory
from application.services.nutritionist_service import NutritionistService
from core.exceptions import ForbiddenError, NotFoundError
from domain.entities.enums import StaffRole
from domain.interfaces.repositories import (
    IClientStaffAssignmentRepository,
    IDietEntryRepository,
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IWorkoutProgramRepository,
)
from tests.unit.conftest import make_assignment, make_diet_entry, make_diet_plan


@pytest.fixture
def assignment_repo() -> AsyncMock:
    return AsyncMock(spec=IClientStaffAssignmentRepository)


@pytest.fixture
def diet_repo() -> AsyncMock:
    return AsyncMock(spec=IDietPlanRepository)


@pytest.fixture
def entry_repo() -> AsyncMock:
    return AsyncMock(spec=IDietEntryRepository)


@pytest.fixture
def workout_repo() -> AsyncMock:
    return AsyncMock(spec=IWorkoutProgramRepository)


@pytest.fixture
def activity_log_repo() -> AsyncMock:
    return AsyncMock(spec=IPlanActivityLogRepository)


@pytest.fixture
def service(
    assignment_repo: AsyncMock,
    diet_repo: AsyncMock,
    entry_repo: AsyncMock,
    workout_repo: AsyncMock,
    activity_log_repo: AsyncMock,
) -> NutritionistService:
    return NutritionistService(
        assignment_repo=assignment_repo,
        diet_repo=diet_repo,
        entry_repo=entry_repo,
        workout_repo=workout_repo,
        activity_log_repo=activity_log_repo,
        diet_factory=DietFactory(),
    )


def setup_valid_assignment(
    assignment_repo: AsyncMock, nutritionist_id: UUID, client_id: UUID
) -> None:
    assignment = make_assignment(client_id, nutritionist_id, StaffRole.NUTRITIONIST)
    assignment_repo.get_active_by_role_for_client.return_value = assignment


# ── Assignment guard ──────────────────────────────────────────────────────────


class TestAssignmentVerification:
    async def test_raises_when_nutritionist_not_assigned(
        self, service: NutritionistService, assignment_repo: AsyncMock
    ) -> None:
        assignment_repo.get_active_by_role_for_client.return_value = None

        with pytest.raises(ForbiddenError):
            await service.create_plan_for_client(
                nutritionist_id=uuid4(), client_id=uuid4(), name="Cutting"
            )

    async def test_raises_when_different_nutritionist_holds_assignment(
        self, service: NutritionistService, assignment_repo: AsyncMock
    ) -> None:
        client_id = uuid4()
        correct_nutritionist = uuid4()
        impostor = uuid4()
        assignment = make_assignment(
            client_id, correct_nutritionist, StaffRole.NUTRITIONIST
        )
        assignment_repo.get_active_by_role_for_client.return_value = assignment

        with pytest.raises(ForbiddenError):
            await service.create_plan_for_client(
                nutritionist_id=impostor, client_id=client_id, name="Plan"
            )


# ── create_plan_for_client ────────────────────────────────────────────────────


class TestCreatePlanForClient:
    async def test_creates_diet_plan(
        self,
        service: NutritionistService,
        assignment_repo: AsyncMock,
        diet_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        nutritionist_id = uuid4()
        client_id = uuid4()
        setup_valid_assignment(assignment_repo, nutritionist_id, client_id)
        diet_repo.get_active_by_owner.return_value = None
        diet_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        result = await service.create_plan_for_client(
            nutritionist_id=nutritionist_id, client_id=client_id, name="Muscle Gain"
        )

        assert result.owner_id == client_id
        assert result.created_by_id == nutritionist_id
        assert result.is_personal is False

    async def test_deactivates_existing_plan_first(
        self,
        service: NutritionistService,
        assignment_repo: AsyncMock,
        diet_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        nutritionist_id = uuid4()
        client_id = uuid4()
        existing = make_diet_plan(client_id, is_active=True)
        setup_valid_assignment(assignment_repo, nutritionist_id, client_id)
        diet_repo.get_active_by_owner.return_value = existing
        diet_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        await service.create_plan_for_client(
            nutritionist_id=nutritionist_id, client_id=client_id, name="New Plan"
        )

        assert diet_repo.save.call_count == 2
        first = diet_repo.save.call_args_list[0][0][0]
        assert first.id == existing.id
        assert first.is_active is False


# ── add_entry ─────────────────────────────────────────────────────────────────


class TestAddEntry:
    async def test_adds_entry_to_active_plan(
        self,
        service: NutritionistService,
        assignment_repo: AsyncMock,
        diet_repo: AsyncMock,
        entry_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        nutritionist_id = uuid4()
        client_id = uuid4()
        plan = make_diet_plan(client_id)
        setup_valid_assignment(assignment_repo, nutritionist_id, client_id)
        diet_repo.get_active_by_owner.return_value = plan
        entry_repo.save.side_effect = lambda e: e
        activity_log_repo.save.return_value = MagicMock()

        entry = await service.add_entry(
            nutritionist_id=nutritionist_id,
            client_id=client_id,
            food_name="Salmon",
            calories=Decimal("200"),
            protein_g=Decimal("25"),
            fat_g=Decimal("10"),
            carbs_g=Decimal("0"),
            order_index=1,
        )

        assert entry.food_name == "Salmon"
        assert entry.plan_id == plan.id
        activity_log_repo.save.assert_called_once()

    async def test_raises_when_no_active_plan(
        self,
        service: NutritionistService,
        assignment_repo: AsyncMock,
        diet_repo: AsyncMock,
    ) -> None:
        nutritionist_id = uuid4()
        client_id = uuid4()
        setup_valid_assignment(assignment_repo, nutritionist_id, client_id)
        diet_repo.get_active_by_owner.return_value = None

        with pytest.raises(NotFoundError, match="No active diet plan"):
            await service.add_entry(
                nutritionist_id=nutritionist_id,
                client_id=client_id,
                food_name="Oats",
                calories=Decimal("350"),
                protein_g=Decimal("12"),
                fat_g=Decimal("6"),
                carbs_g=Decimal("60"),
                order_index=1,
            )


# ── delete_entry ──────────────────────────────────────────────────────────────


class TestDeleteEntry:
    async def test_deletes_entry(
        self,
        service: NutritionistService,
        assignment_repo: AsyncMock,
        diet_repo: AsyncMock,
        entry_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        nutritionist_id = uuid4()
        client_id = uuid4()
        plan = make_diet_plan(client_id)
        entry = make_diet_entry(plan.id)
        setup_valid_assignment(assignment_repo, nutritionist_id, client_id)
        entry_repo.get_by_id.return_value = entry
        diet_repo.get_active_by_owner.return_value = plan
        activity_log_repo.save.return_value = MagicMock()

        await service.delete_entry(
            nutritionist_id=nutritionist_id, client_id=client_id, entry_id=entry.id
        )

        entry_repo.delete.assert_called_once_with(entry.id)

    async def test_raises_when_entry_not_found(
        self,
        service: NutritionistService,
        assignment_repo: AsyncMock,
        entry_repo: AsyncMock,
    ) -> None:
        nutritionist_id = uuid4()
        client_id = uuid4()
        setup_valid_assignment(assignment_repo, nutritionist_id, client_id)
        entry_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.delete_entry(
                nutritionist_id=nutritionist_id,
                client_id=client_id,
                entry_id=uuid4(),
            )
