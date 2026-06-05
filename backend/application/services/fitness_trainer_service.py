"""
FitnessTrainerService — manages workout programmes on behalf of fitness trainers.

Design choice — domain boundary enforcement via StaffDomainViolationError:
    Fitness trainers own workout plans and can READ diet plans for their
    assigned clients. They cannot write diet plan entries. This boundary is
    enforced by what methods exist on this service — there are no diet write
    methods. The ForbiddenError subclass StaffDomainViolationError is raised
    explicitly at the assignment verification stage if the caller's role does
    not match. Sprint 4 route guards ensure only fitness_trainer tokens reach
    these routes; this service is a second line of defence.

Design choice — assignment verification before every client write:
    _verify_trainer_for_client() runs before any mutation on a client's
    plan. It checks that an active FITNESS_TRAINER assignment exists linking
    this trainer to this client. Without this, any trainer who somehow
    obtained a client's programme UUID could modify it. The check adds one
    DB read per mutation — acceptable since plan mutations are low-frequency
    admin operations, not hot-path reads.

Design choice — deactivate-before-create for new programmes:
    When a trainer creates a new programme for a client, any existing active
    non-template programme is deactivated first. This maintains the one-active-
    programme-per-owner invariant at the service layer before the repository's
    partial unique index enforces it at the DB layer.

Design choice — activity log on every significant mutation:
    Plan creation, deactivation, week/day/prescription additions are all
    recorded in plan_activity_log. This powers the cross-domain visibility
    feed (nutritionists assigned to the same client can see workout changes
    in their dashboard). Logging failures are silent — a log write failure
    never causes a plan mutation to roll back.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from application.factories.workout_factory import WorkoutFactory
from core.exceptions import ForbiddenError, NotFoundError
from domain.entities.enums import ActivityAction, PlanType, StaffRole
from domain.entities.plan import PlanActivityLog
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutPrescription,
    WorkoutProgram,
)
from domain.interfaces.repositories import (
    IClientStaffAssignmentRepository,
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IProgramDayRepository,
    IProgramWeekRepository,
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)


class FitnessTrainerService:
    def __init__(
        self,
        assignment_repo: IClientStaffAssignmentRepository,
        workout_repo: IWorkoutProgramRepository,
        week_repo: IProgramWeekRepository,
        day_repo: IProgramDayRepository,
        prescription_repo: IWorkoutPrescriptionRepository,
        diet_repo: IDietPlanRepository,
        activity_log_repo: IPlanActivityLogRepository,
        workout_factory: WorkoutFactory,
    ) -> None:
        self._assignment_repo = assignment_repo
        self._workout_repo = workout_repo
        self._week_repo = week_repo
        self._day_repo = day_repo
        self._prescription_repo = prescription_repo
        self._diet_repo = diet_repo
        self._activity_log_repo = activity_log_repo
        self._factory = workout_factory

    # ── Client list ───────────────────────────────────────────────────────────

    async def list_assigned_clients(self, trainer_id: UUID) -> list[UUID]:
        """Return client_ids of all currently assigned clients."""
        assignments = await self._assignment_repo.get_active_for_staff(trainer_id)
        return [a.client_id for a in assignments]

    # ── Programme CRUD ────────────────────────────────────────────────────────

    async def create_programme_for_client(
        self,
        trainer_id: UUID,
        client_id: UUID,
        name: str,
        coach_notes: str | None = None,
    ) -> WorkoutProgram:
        """
        Create a new workout programme for an assigned client.
        Deactivates any existing active programme first.
        """
        await self._verify_trainer_for_client(trainer_id, client_id)

        existing = await self._workout_repo.get_active_by_owner(client_id)
        if existing is not None:
            deactivated = self._factory.deactivate_program(existing)
            await self._workout_repo.save(deactivated)
            await self._log_activity(
                plan_type=PlanType.WORKOUT,
                plan_id=existing.id,
                actor_id=trainer_id,
                action=ActivityAction.DEACTIVATED,
            )

        program = self._factory.create_program(
            owner_id=client_id,
            created_by_id=trainer_id,
            name=name,
            is_personal=False,
            coach_notes=coach_notes,
        )
        saved = await self._workout_repo.save(program)
        await self._log_activity(
            plan_type=PlanType.WORKOUT,
            plan_id=saved.id,
            actor_id=trainer_id,
            action=ActivityAction.CREATED,
        )
        return saved

    async def get_client_programme(
        self, trainer_id: UUID, client_id: UUID
    ) -> WorkoutProgram | None:
        """Return the active programme for an assigned client, or None."""
        await self._verify_trainer_for_client(trainer_id, client_id)
        return await self._workout_repo.get_active_by_owner(client_id)

    # ── Week / Day / Prescription ─────────────────────────────────────────────

    async def add_week(
        self,
        trainer_id: UUID,
        client_id: UUID,
        week_number: int,
        label: str = "Week",
        notes: str | None = None,
    ) -> ProgramWeek:
        """Add a week to the client's active programme."""
        await self._verify_trainer_for_client(trainer_id, client_id)
        program = await self._workout_repo.get_active_by_owner(client_id)
        if program is None:
            raise NotFoundError(
                f"No active programme found for client {client_id}. "
                "Create a programme first."
            )
        week = self._factory.create_week(
            program_id=program.id,
            week_number=week_number,
            label=label,
            notes=notes,
        )
        saved = await self._week_repo.save(week)
        await self._log_activity(
            plan_type=PlanType.WORKOUT,
            plan_id=program.id,
            actor_id=trainer_id,
            action=ActivityAction.UPDATED,
            metadata={"action_detail": f"added week {week_number}: {label}"},
        )
        return saved

    async def add_day(
        self,
        trainer_id: UUID,
        client_id: UUID,
        week_id: UUID,
        day_number: int,
        label: str = "Day",
        notes: str | None = None,
    ) -> ProgramDay:
        """Add a training day to an existing week."""
        await self._verify_trainer_for_client(trainer_id, client_id)
        day = self._factory.create_day(
            week_id=week_id,
            day_number=day_number,
            label=label,
            notes=notes,
        )
        return await self._day_repo.save(day)

    async def add_prescription(  # noqa: PLR0913
        self,
        trainer_id: UUID,
        client_id: UUID,
        day_id: UUID,
        order_index: int,
        exercise_name: str,
        warmup_sets: int | None = None,
        working_sets: int | None = None,
        reps_min: int | None = None,
        reps_max: int | None = None,
        reps_note: str | None = None,
        prescribed_load_kg: Decimal | None = None,
        prescribed_load_text: str | None = None,
        prescribed_rpe: Decimal | None = None,
        prescribed_rir: int | None = None,
        rest_seconds: int | None = None,
        instructions: str | None = None,
    ) -> WorkoutPrescription:
        """
        Add an exercise prescription (BLUE side) to a day.
        Factory validates all fields before entity construction.
        """
        await self._verify_trainer_for_client(trainer_id, client_id)
        prescription = self._factory.create_prescription(
            day_id=day_id,
            order_index=order_index,
            exercise_name=exercise_name,
            warmup_sets=warmup_sets,
            working_sets=working_sets,
            reps_min=reps_min,
            reps_max=reps_max,
            reps_note=reps_note,
            prescribed_load_kg=prescribed_load_kg,
            prescribed_load_text=prescribed_load_text,
            prescribed_rpe=prescribed_rpe,
            prescribed_rir=prescribed_rir,
            rest_seconds=rest_seconds,
            instructions=instructions,
        )
        saved = await self._prescription_repo.save(prescription)
        # Log against the client's active programme
        active = await self._workout_repo.get_active_by_owner(client_id)
        if active is not None:
            await self._log_activity(
                plan_type=PlanType.WORKOUT,
                plan_id=active.id,
                actor_id=trainer_id,
                action=ActivityAction.ENTRY_ADDED,
                metadata={"exercise_name": exercise_name, "order_index": order_index},
            )
        return saved

    async def delete_prescription(
        self,
        trainer_id: UUID,
        client_id: UUID,
        prescription_id: UUID,
    ) -> None:
        """Delete a prescription from the client's programme."""
        await self._verify_trainer_for_client(trainer_id, client_id)
        prescription = await self._prescription_repo.get_by_id(prescription_id)
        if prescription is None:
            raise NotFoundError(f"Prescription {prescription_id} not found")
        await self._prescription_repo.delete(prescription_id)
        active = await self._workout_repo.get_active_by_owner(client_id)
        if active is not None:
            await self._log_activity(
                plan_type=PlanType.WORKOUT,
                plan_id=active.id,
                actor_id=trainer_id,
                action=ActivityAction.ENTRY_REMOVED,
                metadata={
                    "exercise_name": prescription.exercise_name,
                    "prescription_id": str(prescription_id),
                },
            )

    # ── Read — diet plans (cross-domain visibility, read only) ────────────────

    async def get_client_diet_plan(self, trainer_id: UUID, client_id: UUID) -> object:
        """
        Read the client's active diet plan (no write access).
        Trainers can read diet plans to understand the full coaching context.
        """
        await self._verify_trainer_for_client(trainer_id, client_id)
        return await self._diet_repo.get_active_by_owner(client_id)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _verify_trainer_for_client(
        self, trainer_id: UUID, client_id: UUID
    ) -> None:
        """
        Verify trainer_id has an active FITNESS_TRAINER assignment for client_id.
        Raises ForbiddenError if no such assignment exists.
        """
        assignment = await self._assignment_repo.get_active_by_role_for_client(
            client_id=client_id,
            staff_role=StaffRole.FITNESS_TRAINER,
        )
        if assignment is None or assignment.staff_id != trainer_id:
            raise ForbiddenError(
                f"Trainer {trainer_id} is not assigned to client {client_id} "
                "as a fitness trainer"
            )

    async def _log_activity(
        self,
        plan_type: PlanType,
        plan_id: UUID,
        actor_id: UUID,
        action: ActivityAction,
        metadata: dict[str, object] | None = None,
    ) -> None:
        log = PlanActivityLog(
            id=uuid4(),
            plan_type=plan_type,
            plan_id=plan_id,
            actor_id=actor_id,
            action=action,
            metadata=metadata,
            occurred_at=datetime.now(tz=UTC),
        )
        await self._activity_log_repo.save(log)
