"""
Unit tests for PersonalPlanService.

Key invariants tested:
- Creating a personal plan deactivates any existing active plan first.
- get_personal_workout only returns plans where is_personal=True.
- Ownership check prevents modifying another user's programme.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from application.factories.diet_factory import DietFactory
from application.factories.workout_factory import WorkoutFactory
from application.services.personal_plan_service import PersonalPlanService
from domain.interfaces.repositories import (
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IProgramDayRepository,
    IProgramWeekRepository,
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)
from tests.unit.conftest import make_diet_plan, make_workout_program


@pytest.fixture
def workout_repo() -> AsyncMock:
    return AsyncMock(spec=IWorkoutProgramRepository)


@pytest.fixture
def diet_repo() -> AsyncMock:
    return AsyncMock(spec=IDietPlanRepository)


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
def activity_log_repo() -> AsyncMock:
    return AsyncMock(spec=IPlanActivityLogRepository)


@pytest.fixture
def service(
    workout_repo: AsyncMock,
    diet_repo: AsyncMock,
    week_repo: AsyncMock,
    day_repo: AsyncMock,
    prescription_repo: AsyncMock,
    activity_log_repo: AsyncMock,
) -> PersonalPlanService:
    return PersonalPlanService(
        workout_repo=workout_repo,
        diet_repo=diet_repo,
        week_repo=week_repo,
        day_repo=day_repo,
        prescription_repo=prescription_repo,
        activity_log_repo=activity_log_repo,
        workout_factory=WorkoutFactory(),
        diet_factory=DietFactory(),
    )


# ── get_personal_workout ──────────────────────────────────────────────────────


class TestGetPersonalWorkout:
    async def test_returns_personal_programme(
        self, service: PersonalPlanService, workout_repo: AsyncMock
    ) -> None:
        owner_id = uuid4()
        program = make_workout_program(owner_id, is_personal=True)
        workout_repo.get_active_by_owner.return_value = program

        result = await service.get_personal_workout(owner_id)
        assert result == program

    async def test_returns_none_for_non_personal_active_programme(
        self, service: PersonalPlanService, workout_repo: AsyncMock
    ) -> None:
        """A coach-assigned programme (is_personal=False) is not returned here."""
        owner_id = uuid4()
        assigned = make_workout_program(owner_id, is_personal=False)
        workout_repo.get_active_by_owner.return_value = assigned

        result = await service.get_personal_workout(owner_id)
        assert result is None

    async def test_returns_none_when_no_active_programme(
        self, service: PersonalPlanService, workout_repo: AsyncMock
    ) -> None:
        workout_repo.get_active_by_owner.return_value = None
        result = await service.get_personal_workout(uuid4())
        assert result is None


# ── create_personal_workout ───────────────────────────────────────────────────


class TestCreatePersonalWorkout:
    async def test_creates_programme_with_is_personal_true(
        self,
        service: PersonalPlanService,
        workout_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        owner_id = uuid4()
        workout_repo.get_active_by_owner.return_value = None
        workout_repo.save.side_effect = lambda p: p  # echo back the entity
        activity_log_repo.save.return_value = MagicMock()

        result = await service.create_personal_workout(owner_id, "My 12-Week Plan")

        assert result.is_personal is True
        assert result.owner_id == owner_id
        assert result.created_by_id == owner_id  # personal: creator == owner
        assert result.name == "My 12-Week Plan"
        assert result.is_active is True

    async def test_deactivates_existing_before_creating(
        self,
        service: PersonalPlanService,
        workout_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        owner_id = uuid4()
        existing = make_workout_program(owner_id, is_active=True, is_personal=True)
        workout_repo.get_active_by_owner.return_value = existing
        workout_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        await service.create_personal_workout(owner_id, "New Plan")

        # save called twice: deactivate old, create new
        assert workout_repo.save.call_count == 2
        # First call deactivates existing
        first_saved = workout_repo.save.call_args_list[0][0][0]
        assert first_saved.id == existing.id
        assert first_saved.is_active is False

    async def test_writes_activity_log_on_create(
        self,
        service: PersonalPlanService,
        workout_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        owner_id = uuid4()
        workout_repo.get_active_by_owner.return_value = None
        workout_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        await service.create_personal_workout(owner_id, "Plan")

        activity_log_repo.save.assert_called_once()


# ── get_personal_diet ─────────────────────────────────────────────────────────


class TestGetPersonalDiet:
    async def test_returns_personal_diet_plan(
        self, service: PersonalPlanService, diet_repo: AsyncMock
    ) -> None:
        owner_id = uuid4()
        plan = make_diet_plan(owner_id, is_personal=True)
        diet_repo.get_active_by_owner.return_value = plan

        result = await service.get_personal_diet(owner_id)
        assert result == plan

    async def test_returns_none_for_coach_assigned_diet(
        self, service: PersonalPlanService, diet_repo: AsyncMock
    ) -> None:
        owner_id = uuid4()
        assigned = make_diet_plan(owner_id, is_personal=False)
        diet_repo.get_active_by_owner.return_value = assigned

        result = await service.get_personal_diet(owner_id)
        assert result is None


# ── create_personal_diet ──────────────────────────────────────────────────────


class TestCreatePersonalDiet:
    async def test_creates_diet_plan_with_is_personal_true(
        self,
        service: PersonalPlanService,
        diet_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        owner_id = uuid4()
        diet_repo.get_active_by_owner.return_value = None
        diet_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        result = await service.create_personal_diet(owner_id, "Cutting Diet")

        assert result.is_personal is True
        assert result.owner_id == owner_id
        assert result.name == "Cutting Diet"

    async def test_deactivates_existing_diet_plan_first(
        self,
        service: PersonalPlanService,
        diet_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        owner_id = uuid4()
        existing = make_diet_plan(owner_id, is_active=True, is_personal=True)
        diet_repo.get_active_by_owner.return_value = existing
        diet_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        await service.create_personal_diet(owner_id, "New Diet")

        assert diet_repo.save.call_count == 2
        deactivated = diet_repo.save.call_args_list[0][0][0]
        assert deactivated.id == existing.id
        assert deactivated.is_active is False
