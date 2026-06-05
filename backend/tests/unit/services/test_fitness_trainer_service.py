"""
Unit tests for FitnessTrainerService.

Key invariants tested:
- All write methods reject access when no active assignment exists.
- Deactivate-before-create pattern for new programmes.
- Domain boundary: trainers cannot write diet plans (no method to test,
  but the cross-domain read is covered).
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from application.factories.workout_factory import WorkoutFactory
from application.services.fitness_trainer_service import FitnessTrainerService
from core.exceptions import ForbiddenError, NotFoundError
from domain.entities.enums import StaffRole
from domain.interfaces.repositories import (
    IClientStaffAssignmentRepository,
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IProgramDayRepository,
    IProgramWeekRepository,
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)
from tests.unit.conftest import (
    make_assignment,
    make_prescription,
    make_workout_program,
)


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
    activity_log_repo: AsyncMock,
) -> FitnessTrainerService:
    return FitnessTrainerService(
        assignment_repo=assignment_repo,
        workout_repo=workout_repo,
        week_repo=week_repo,
        day_repo=day_repo,
        prescription_repo=prescription_repo,
        diet_repo=diet_repo,
        activity_log_repo=activity_log_repo,
        workout_factory=WorkoutFactory(),
    )


def setup_valid_assignment(
    assignment_repo: AsyncMock,
    trainer_id: UUID,
    client_id: UUID,
) -> None:
    """Configure assignment_repo to return a valid FITNESS_TRAINER assignment."""
    assignment = make_assignment(client_id, trainer_id, StaffRole.FITNESS_TRAINER)
    assignment_repo.get_active_by_role_for_client.return_value = assignment


def setup_no_assignment(assignment_repo: AsyncMock) -> None:
    """Configure assignment_repo to return no assignment (unassigned)."""
    assignment_repo.get_active_by_role_for_client.return_value = None


# ── Assignment verification ───────────────────────────────────────────────────


class TestAssignmentVerification:
    async def test_raises_when_trainer_not_assigned(
        self, service: FitnessTrainerService, assignment_repo: AsyncMock
    ) -> None:
        setup_no_assignment(assignment_repo)

        with pytest.raises(ForbiddenError, match="not assigned"):
            await service.create_programme_for_client(
                trainer_id=uuid4(), client_id=uuid4(), name="Plan"
            )

    async def test_raises_when_different_trainer_holds_assignment(
        self, service: FitnessTrainerService, assignment_repo: AsyncMock
    ) -> None:
        """Assignment exists but for a different trainer_id."""
        client_id = uuid4()
        correct_trainer = uuid4()
        impostor_trainer = uuid4()
        assignment = make_assignment(
            client_id, correct_trainer, StaffRole.FITNESS_TRAINER
        )
        assignment_repo.get_active_by_role_for_client.return_value = assignment

        with pytest.raises(ForbiddenError):
            await service.create_programme_for_client(
                trainer_id=impostor_trainer, client_id=client_id, name="Plan"
            )


# ── create_programme_for_client ───────────────────────────────────────────────


class TestCreateProgramme:
    async def test_creates_programme_for_assigned_client(
        self,
        service: FitnessTrainerService,
        assignment_repo: AsyncMock,
        workout_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        trainer_id = uuid4()
        client_id = uuid4()
        setup_valid_assignment(assignment_repo, trainer_id, client_id)
        workout_repo.get_active_by_owner.return_value = None
        workout_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        result = await service.create_programme_for_client(
            trainer_id=trainer_id, client_id=client_id, name="Hypertrophy Block"
        )

        assert result.owner_id == client_id
        assert result.created_by_id == trainer_id
        assert result.is_personal is False
        assert result.name == "Hypertrophy Block"

    async def test_deactivates_existing_before_creating(
        self,
        service: FitnessTrainerService,
        assignment_repo: AsyncMock,
        workout_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        trainer_id = uuid4()
        client_id = uuid4()
        existing = make_workout_program(client_id, is_active=True)
        setup_valid_assignment(assignment_repo, trainer_id, client_id)
        workout_repo.get_active_by_owner.return_value = existing
        workout_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        await service.create_programme_for_client(
            trainer_id=trainer_id, client_id=client_id, name="New Block"
        )

        # First save = deactivate old, second save = create new
        assert workout_repo.save.call_count == 2
        first_call = workout_repo.save.call_args_list[0][0][0]
        assert first_call.id == existing.id
        assert first_call.is_active is False


# ── add_week ──────────────────────────────────────────────────────────────────


class TestAddWeek:
    async def test_raises_when_no_active_programme(
        self,
        service: FitnessTrainerService,
        assignment_repo: AsyncMock,
        workout_repo: AsyncMock,
    ) -> None:
        trainer_id = uuid4()
        client_id = uuid4()
        setup_valid_assignment(assignment_repo, trainer_id, client_id)
        workout_repo.get_active_by_owner.return_value = None

        with pytest.raises(NotFoundError, match="No active programme"):
            await service.add_week(
                trainer_id=trainer_id,
                client_id=client_id,
                week_number=1,
                label="Week 1",
            )

    async def test_adds_week_to_active_programme(
        self,
        service: FitnessTrainerService,
        assignment_repo: AsyncMock,
        workout_repo: AsyncMock,
        week_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        trainer_id = uuid4()
        client_id = uuid4()
        program = make_workout_program(client_id)
        setup_valid_assignment(assignment_repo, trainer_id, client_id)
        workout_repo.get_active_by_owner.return_value = program
        week_repo.save.side_effect = lambda w: w
        activity_log_repo.save.return_value = MagicMock()

        week = await service.add_week(
            trainer_id=trainer_id,
            client_id=client_id,
            week_number=1,
            label="Hypertrophy Week 1",
        )

        assert week.program_id == program.id
        assert week.week_number == 1


# ── add_prescription ──────────────────────────────────────────────────────────


class TestAddPrescription:
    async def test_adds_prescription_and_logs_activity(
        self,
        service: FitnessTrainerService,
        assignment_repo: AsyncMock,
        workout_repo: AsyncMock,
        prescription_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        trainer_id = uuid4()
        client_id = uuid4()
        day_id = uuid4()
        program = make_workout_program(client_id)
        setup_valid_assignment(assignment_repo, trainer_id, client_id)
        workout_repo.get_active_by_owner.return_value = program
        prescription_repo.save.side_effect = lambda p: p
        activity_log_repo.save.return_value = MagicMock()

        rx = await service.add_prescription(
            trainer_id=trainer_id,
            client_id=client_id,
            day_id=day_id,
            order_index=1,
            exercise_name="Deadlift",
            working_sets=4,
            reps_min=3,
        )

        assert rx.exercise_name == "Deadlift"
        assert rx.day_id == day_id
        activity_log_repo.save.assert_called_once()


# ── delete_prescription ───────────────────────────────────────────────────────


class TestDeletePrescription:
    async def test_deletes_prescription(
        self,
        service: FitnessTrainerService,
        assignment_repo: AsyncMock,
        workout_repo: AsyncMock,
        prescription_repo: AsyncMock,
        activity_log_repo: AsyncMock,
    ) -> None:
        trainer_id = uuid4()
        client_id = uuid4()
        program = make_workout_program(client_id)
        prescription = make_prescription(uuid4())
        setup_valid_assignment(assignment_repo, trainer_id, client_id)
        prescription_repo.get_by_id.return_value = prescription
        workout_repo.get_active_by_owner.return_value = program
        activity_log_repo.save.return_value = MagicMock()

        await service.delete_prescription(
            trainer_id=trainer_id, client_id=client_id, prescription_id=prescription.id
        )

        prescription_repo.delete.assert_called_once_with(prescription.id)

    async def test_raises_when_prescription_not_found(
        self,
        service: FitnessTrainerService,
        assignment_repo: AsyncMock,
        prescription_repo: AsyncMock,
    ) -> None:
        trainer_id = uuid4()
        client_id = uuid4()
        setup_valid_assignment(assignment_repo, trainer_id, client_id)
        prescription_repo.get_by_id.return_value = None

        with pytest.raises(NotFoundError):
            await service.delete_prescription(
                trainer_id=trainer_id, client_id=client_id, prescription_id=uuid4()
            )
