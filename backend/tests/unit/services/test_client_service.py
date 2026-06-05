"""
Unit tests for ClientService.

Key invariants tested:
- get_assigned_workout only returns is_personal=False plans.
- log_workout validates prescription ownership.
- log_workout allows orphan (no prescription) mode when exercise_name provided.
- log_workout raises ValidationError when neither prescription_id nor exercise_name given.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from application.services.client_service import ClientService
from core.exceptions import NotFoundError, ValidationError
from domain.interfaces.repositories import (
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IWorkoutLogRepository,
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)
from tests.unit.conftest import (
    make_diet_plan,
    make_prescription,
    make_workout_program,
)


@pytest.fixture
def workout_repo() -> AsyncMock:
    return AsyncMock(spec=IWorkoutProgramRepository)


@pytest.fixture
def diet_repo() -> AsyncMock:
    return AsyncMock(spec=IDietPlanRepository)


@pytest.fixture
def prescription_repo() -> AsyncMock:
    return AsyncMock(spec=IWorkoutPrescriptionRepository)


@pytest.fixture
def log_repo() -> AsyncMock:
    return AsyncMock(spec=IWorkoutLogRepository)


@pytest.fixture
def activity_log_repo() -> AsyncMock:
    return AsyncMock(spec=IPlanActivityLogRepository)


@pytest.fixture
def service(
    workout_repo: AsyncMock,
    diet_repo: AsyncMock,
    prescription_repo: AsyncMock,
    log_repo: AsyncMock,
    activity_log_repo: AsyncMock,
) -> ClientService:
    return ClientService(
        workout_repo=workout_repo,
        diet_repo=diet_repo,
        prescription_repo=prescription_repo,
        log_repo=log_repo,
        activity_log_repo=activity_log_repo,
    )


# ── get_assigned_workout ──────────────────────────────────────────────────────


class TestGetAssignedWorkout:
    async def test_returns_coach_assigned_programme(
        self, service: ClientService, workout_repo: AsyncMock
    ) -> None:
        client_id = uuid4()
        program = make_workout_program(client_id, is_personal=False)
        workout_repo.get_active_by_owner.return_value = program

        result = await service.get_assigned_workout(client_id)
        assert result == program

    async def test_returns_none_for_personal_programme(
        self, service: ClientService, workout_repo: AsyncMock
    ) -> None:
        """Personal programmes are not accessible through assigned plan routes."""
        client_id = uuid4()
        personal = make_workout_program(client_id, is_personal=True)
        workout_repo.get_active_by_owner.return_value = personal

        result = await service.get_assigned_workout(client_id)
        assert result is None

    async def test_returns_none_when_no_active_programme(
        self, service: ClientService, workout_repo: AsyncMock
    ) -> None:
        workout_repo.get_active_by_owner.return_value = None
        result = await service.get_assigned_workout(uuid4())
        assert result is None


# ── get_assigned_diet ─────────────────────────────────────────────────────────


class TestGetAssignedDiet:
    async def test_returns_coach_assigned_plan(
        self, service: ClientService, diet_repo: AsyncMock
    ) -> None:
        client_id = uuid4()
        plan = make_diet_plan(client_id, is_personal=False)
        diet_repo.get_active_by_owner.return_value = plan

        result = await service.get_assigned_diet(client_id)
        assert result == plan

    async def test_returns_none_for_personal_diet(
        self, service: ClientService, diet_repo: AsyncMock
    ) -> None:
        client_id = uuid4()
        personal = make_diet_plan(client_id, is_personal=True)
        diet_repo.get_active_by_owner.return_value = personal

        result = await service.get_assigned_diet(client_id)
        assert result is None


# ── log_workout ───────────────────────────────────────────────────────────────


class TestLogWorkout:
    async def test_logs_workout_linked_to_prescription(
        self,
        service: ClientService,
        prescription_repo: AsyncMock,
        workout_repo: AsyncMock,
        log_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        client_id = uuid4()
        day_id = uuid4()
        prescription = make_prescription(day_id)
        program = make_workout_program(client_id, is_personal=False)

        prescription_repo.get_by_id.return_value = prescription
        workout_repo.get_active_by_owner.return_value = program
        log_repo.save.side_effect = lambda entry: entry
        activity_log_repo.save.return_value = MagicMock()

        log = await service.log_workout(
            client_id=client_id,
            prescription_id=prescription.id,
            exercise_name=None,
            actual_sets=4,
            actual_reps=6,
            actual_load_kg=Decimal("70"),
        )

        assert log.client_id == client_id
        assert log.prescription_id == prescription.id
        assert log.actual_sets == 4
        assert log.actual_reps == 6
        log_repo.save.assert_called_once()

    async def test_logs_orphan_workout_without_prescription(
        self,
        service: ClientService,
        log_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        """Client self-logging with exercise_name and no prescription_id."""
        client_id = uuid4()
        log_repo.save.side_effect = lambda entry: entry
        activity_log_repo.save.return_value = MagicMock()

        log = await service.log_workout(
            client_id=client_id,
            prescription_id=None,
            exercise_name="Deadlift",
            actual_sets=3,
            actual_reps=5,
        )

        assert log.prescription_id is None
        assert log.exercise_name == "Deadlift"
        assert log.is_self_logged is True

    async def test_raises_when_neither_prescription_nor_exercise_name(
        self, service: ClientService
    ) -> None:
        with pytest.raises(ValidationError, match="prescription_id or exercise_name"):
            await service.log_workout(
                client_id=uuid4(),
                prescription_id=None,
                exercise_name=None,  # neither provided
                actual_sets=3,
                actual_reps=5,
            )

    async def test_raises_when_prescription_not_found(
        self,
        service: ClientService,
        prescription_repo: AsyncMock,
    ) -> None:
        prescription_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.log_workout(
                client_id=uuid4(),
                prescription_id=uuid4(),
                exercise_name=None,
                actual_sets=3,
                actual_reps=5,
            )

    async def test_video_fields_are_none_phase2(
        self,
        service: ClientService,
        log_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        """video_url and video_source are Phase 2 — always None in Phase 1."""
        log_repo.save.side_effect = lambda entry: entry
        activity_log_repo.save.return_value = MagicMock()

        log = await service.log_workout(
            client_id=uuid4(),
            prescription_id=None,
            exercise_name="Bench Press",
            actual_sets=4,
            actual_reps=8,
        )

        assert log.video_url is None
        assert log.video_source is None
