"""
Unit tests for MasterCoachService.

A master coach has full write access to both domains (workout + diet).
Key invariants:
- A single MASTER_COACH assignment check gates all operations in both domains.
- Deactivate-before-create for both workout programmes and diet plans.
- No inheritance from FitnessTrainerService or NutritionistService — the
  tests confirm the same patterns are independently implemented.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from application.factories.diet_factory import DietFactory
from application.factories.workout_factory import WorkoutFactory
from application.services.master_coach_service import MasterCoachService
from core.exceptions import ForbiddenError, NotFoundError
from domain.entities.enums import StaffRole
from domain.interfaces.repositories import (
    IClientStaffAssignmentRepository,
    IDietEntryRepository,
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IProgramDayRepository,
    IProgramWeekRepository,
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)
from tests.unit.conftest import make_assignment, make_diet_plan, make_workout_program


@pytest.fixture
def assignment_repo() -> AsyncMock:
    return AsyncMock(spec=IClientStaffAssignmentRepository)


@pytest.fixture
def workout_repo() -> AsyncMock:
    return AsyncMock(spec=IWorkoutProgramRepository)


@pytest.fixture
def week_repo() -> AsyncMock:
    return AsyncMock(spec=IProgramWeekRepository)


@pytest.fixture
def day_repo() -> AsyncMock:
    return AsyncMock(spec=IProgramDayRepository)


@pytest.fixture
def prescription_repo() -> AsyncMock:
    return AsyncMock(spec=IWorkoutPrescriptionRepository)


@pytest.fixture
def diet_repo() -> AsyncMock:
    return AsyncMock(spec=IDietPlanRepository)


@pytest.fixture
def entry_repo() -> AsyncMock:
    return AsyncMock(spec=IDietEntryRepository)


@pytest.fixture
def activity_log_repo() -> AsyncMock:
    return AsyncMock(spec=IPlanActivityLogRepository)


@pytest.fixture
def service(
    assignment_repo: AsyncMock,
    workout_repo: AsyncMock,
    week_repo: AsyncMock,
    day_repo: AsyncMock,
    prescription_repo: AsyncMock,
    diet_repo: AsyncMock,
    entry_repo: AsyncMock,
    activity_log_repo: AsyncMock,
) -> MasterCoachService:
    return MasterCoachService(
        assignment_repo=assignment_repo,
        workout_repo=workout_repo,
        week_repo=week_repo,
        day_repo=day_repo,
        prescription_repo=prescription_repo,
        diet_repo=diet_repo,
        entry_repo=entry_repo,
        activity_log_repo=activity_log_repo,
        workout_factory=WorkoutFactory(),
        diet_factory=DietFactory(),
    )


def setup_valid_assignment(
    assignment_repo: AsyncMock, coach_id: UUID, client_id: UUID
) -> None:
    assignment = make_assignment(client_id, coach_id, StaffRole.MASTER_COACH)
    assignment_repo.get_active_by_role_for_client.return_value = assignment


def setup_no_assignment(assignment_repo: AsyncMock) -> None:
    assignment_repo.get_active_by_role_for_client.return_value = None


# ── Assignment guard ──────────────────────────────────────────────────────────


class TestAssignmentGuard:
    async def test_workout_write_rejected_without_assignment(
        self, service: MasterCoachService, assignment_repo: AsyncMock
    ) -> None:
        setup_no_assignment(assignment_repo)
        with pytest.raises(ForbiddenError, match="not assigned"):
            await service.create_workout_programme(
                coach_id=uuid4(), client_id=uuid4(), name="Plan"
            )

    async def test_diet_write_rejected_without_assignment(
        self, service: MasterCoachService, assignment_repo: AsyncMock
    ) -> None:
        setup_no_assignment(assignment_repo)
        with pytest.raises(ForbiddenError):
            await service.create_diet_plan(
                coach_id=uuid4(), client_id=uuid4(), name="Diet"
            )

    async def test_impostor_coach_rejected(
        self, service: MasterCoachService, assignment_repo: AsyncMock
    ) -> None:
        client_id = uuid4()
        actual_coach = uuid4()
        impostor = uuid4()
        assignment = make_assignment(client_id, actual_coach, StaffRole.MASTER_COACH)
        assignment_repo.get_active_by_role_for_client.return_value = assignment

        with pytest.raises(ForbiddenError):
            await service.create_workout_programme(
                coach_id=impostor, client_id=client_id, name="Plan"
            )


# ── Workout operations ────────────────────────────────────────────────────────


class TestWorkoutOperations:
    async def test_creates_workout_programme(
        self,
        service: MasterCoachService,
        assignment_repo: AsyncMock,
        workout_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        coach_id = uuid4()
        client_id = uuid4()
        setup_valid_assignment(assignment_repo, coach_id, client_id)
        workout_repo.get_active_by_owner.return_value = None
        workout_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        result = await service.create_workout_programme(
            coach_id=coach_id, client_id=client_id, name="PPL Block"
        )

        assert result.owner_id == client_id
        assert result.created_by_id == coach_id
        assert result.is_active is True

    async def test_deactivates_existing_workout_before_creating(
        self,
        service: MasterCoachService,
        assignment_repo: AsyncMock,
        workout_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        coach_id = uuid4()
        client_id = uuid4()
        existing = make_workout_program(client_id, is_active=True)
        setup_valid_assignment(assignment_repo, coach_id, client_id)
        workout_repo.get_active_by_owner.return_value = existing
        workout_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        await service.create_workout_programme(
            coach_id=coach_id, client_id=client_id, name="New Programme"
        )

        assert workout_repo.save.call_count == 2
        first = workout_repo.save.call_args_list[0][0][0]
        assert first.is_active is False

    async def test_add_week_raises_when_no_active_programme(
        self,
        service: MasterCoachService,
        assignment_repo: AsyncMock,
        workout_repo: AsyncMock,
    ) -> None:
        coach_id = uuid4()
        client_id = uuid4()
        setup_valid_assignment(assignment_repo, coach_id, client_id)
        workout_repo.get_active_by_owner.return_value = None

        with pytest.raises(NotFoundError):
            await service.add_week(
                coach_id=coach_id, client_id=client_id, week_number=1, label="Week 1"
            )


# ── Diet operations ───────────────────────────────────────────────────────────


class TestDietOperations:
    async def test_creates_diet_plan(
        self,
        service: MasterCoachService,
        assignment_repo: AsyncMock,
        diet_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        coach_id = uuid4()
        client_id = uuid4()
        setup_valid_assignment(assignment_repo, coach_id, client_id)
        diet_repo.get_active_by_owner.return_value = None
        diet_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        result = await service.create_diet_plan(
            coach_id=coach_id, client_id=client_id, name="Recomp Protocol"
        )

        assert result.owner_id == client_id
        assert result.created_by_id == coach_id

    async def test_deactivates_existing_diet_before_creating(
        self,
        service: MasterCoachService,
        assignment_repo: AsyncMock,
        diet_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        coach_id = uuid4()
        client_id = uuid4()
        existing = make_diet_plan(client_id, is_active=True)
        setup_valid_assignment(assignment_repo, coach_id, client_id)
        diet_repo.get_active_by_owner.return_value = existing
        diet_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        await service.create_diet_plan(
            coach_id=coach_id, client_id=client_id, name="New Diet"
        )

        assert diet_repo.save.call_count == 2
        first = diet_repo.save.call_args_list[0][0][0]
        assert first.is_active is False

    async def test_adds_diet_entry(
        self,
        service: MasterCoachService,
        assignment_repo: AsyncMock,
        diet_repo: AsyncMock,
        entry_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        coach_id = uuid4()
        client_id = uuid4()
        plan = make_diet_plan(client_id)
        setup_valid_assignment(assignment_repo, coach_id, client_id)
        diet_repo.get_active_by_owner.return_value = plan
        entry_repo.save.side_effect = lambda e: e
        activity_log_repo.save.return_value = MagicMock()

        entry = await service.add_diet_entry(
            coach_id=coach_id,
            client_id=client_id,
            food_name="Brown Rice",
            calories=Decimal("215"),
            protein_g=Decimal("4"),
            fat_g=Decimal("1.6"),
            carbs_g=Decimal("45"),
            order_index=2,
        )

        assert entry.food_name == "Brown Rice"
        assert entry.plan_id == plan.id
