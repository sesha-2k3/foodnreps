"""
MasterCoachService — manages both workout and diet plans for master coaches.

A master coach owns both coaching domains for their assigned clients. This
service is the union of FitnessTrainerService (workout) and NutritionistService
(diet) capabilities, with a MASTER_COACH assignment check instead of role-specific
checks.

Design choice — no inheritance from FitnessTrainerService or NutritionistService:
    Python inheritance here would be convenient but architecturally misleading.
    A master coach is NOT a specialised kind of fitness trainer. The Liskov
    Substitution Principle would imply anywhere FitnessTrainerService is expected,
    MasterCoachService could substitute — which is false (they check different
    assignment roles). Composition via shared factories and repositories is the
    correct tool: each service independently implements the same patterns.

Design choice — single _verify_coach_for_client check for both domains:
    A master coach's assignment covers both workout and diet writes. One
    assignment check (StaffRole.MASTER_COACH) gates all operations on both
    plan types. This simplifies the verification compared to the per-domain
    checks in FitnessTrainerService and NutritionistService.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from application.factories.diet_factory import DietFactory
from application.factories.workout_factory import WorkoutFactory
from core.exceptions import ForbiddenError, NotFoundError
from domain.entities.diet import DietEntry, DietPlan
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
    IDietEntryRepository,
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IProgramDayRepository,
    IProgramWeekRepository,
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)


class MasterCoachService:
    def __init__(
        self,
        assignment_repo: IClientStaffAssignmentRepository,
        workout_repo: IWorkoutProgramRepository,
        week_repo: IProgramWeekRepository,
        day_repo: IProgramDayRepository,
        prescription_repo: IWorkoutPrescriptionRepository,
        diet_repo: IDietPlanRepository,
        entry_repo: IDietEntryRepository,
        activity_log_repo: IPlanActivityLogRepository,
        workout_factory: WorkoutFactory,
        diet_factory: DietFactory,
    ) -> None:
        self._assignment_repo = assignment_repo
        self._workout_repo = workout_repo
        self._week_repo = week_repo
        self._day_repo = day_repo
        self._prescription_repo = prescription_repo
        self._diet_repo = diet_repo
        self._entry_repo = entry_repo
        self._activity_log_repo = activity_log_repo
        self._workout_factory = workout_factory
        self._diet_factory = diet_factory

    # ── Client list ───────────────────────────────────────────────────────────

    async def list_assigned_clients(self, coach_id: UUID) -> list[UUID]:
        """Return client_ids of all clients currently assigned to this coach."""
        assignments = await self._assignment_repo.get_active_for_staff(coach_id)
        return [a.client_id for a in assignments]

    # ── Workout — programme CRUD ──────────────────────────────────────────────

    async def create_workout_programme(
        self,
        coach_id: UUID,
        client_id: UUID,
        name: str,
        coach_notes: str | None = None,
    ) -> WorkoutProgram:
        """Create a new workout programme for an assigned client."""
        await self._verify_coach_for_client(coach_id, client_id)

        existing = await self._workout_repo.get_active_by_owner(client_id)
        if existing is not None:
            deactivated = self._workout_factory.deactivate_program(existing)
            await self._workout_repo.save(deactivated)
            await self._log_activity(
                PlanType.WORKOUT, existing.id, coach_id, ActivityAction.DEACTIVATED
            )

        program = self._workout_factory.create_program(
            owner_id=client_id,
            created_by_id=coach_id,
            name=name,
            is_personal=False,
            coach_notes=coach_notes,
        )
        saved = await self._workout_repo.save(program)
        await self._log_activity(
            PlanType.WORKOUT, saved.id, coach_id, ActivityAction.CREATED
        )
        return saved

    async def get_client_workout(
        self, coach_id: UUID, client_id: UUID
    ) -> WorkoutProgram | None:
        """Return the active workout programme for an assigned client."""
        await self._verify_coach_for_client(coach_id, client_id)
        return await self._workout_repo.get_active_by_owner(client_id)

    async def add_week(
        self,
        coach_id: UUID,
        client_id: UUID,
        week_number: int,
        label: str = "Week",
        notes: str | None = None,
    ) -> ProgramWeek:
        """Add a training week to the client's active workout programme."""
        await self._verify_coach_for_client(coach_id, client_id)
        program = await self._workout_repo.get_active_by_owner(client_id)
        if program is None:
            raise NotFoundError(
                f"No active workout programme found for client {client_id}"
            )
        week = self._workout_factory.create_week(program.id, week_number, label, notes)
        saved = await self._week_repo.save(week)
        await self._log_activity(
            PlanType.WORKOUT,
            program.id,
            coach_id,
            ActivityAction.UPDATED,
            {"action_detail": f"added week {week_number}: {label}"},
        )
        return saved

    async def add_day(
        self,
        coach_id: UUID,
        client_id: UUID,
        week_id: UUID,
        day_number: int,
        label: str = "Day",
        notes: str | None = None,
    ) -> ProgramDay:
        """Add a training day to a week in the client's programme."""
        await self._verify_coach_for_client(coach_id, client_id)
        day = self._workout_factory.create_day(week_id, day_number, label, notes)
        return await self._day_repo.save(day)

    async def add_prescription(  # noqa: PLR0913
        self,
        coach_id: UUID,
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
        """Add an exercise prescription to a day in the client's programme."""
        await self._verify_coach_for_client(coach_id, client_id)
        prescription = self._workout_factory.create_prescription(
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
        active = await self._workout_repo.get_active_by_owner(client_id)
        if active is not None:
            await self._log_activity(
                PlanType.WORKOUT,
                active.id,
                coach_id,
                ActivityAction.ENTRY_ADDED,
                {"exercise_name": exercise_name, "order_index": order_index},
            )
        return saved

    # ── Diet — plan CRUD ──────────────────────────────────────────────────────

    async def create_diet_plan(
        self,
        coach_id: UUID,
        client_id: UUID,
        name: str,
        coach_notes: str | None = None,
    ) -> DietPlan:
        """Create a new diet plan for an assigned client."""
        await self._verify_coach_for_client(coach_id, client_id)

        existing = await self._diet_repo.get_active_by_owner(client_id)
        if existing is not None:
            deactivated = self._diet_factory.deactivate_plan(existing)
            await self._diet_repo.save(deactivated)
            await self._log_activity(
                PlanType.DIET, existing.id, coach_id, ActivityAction.DEACTIVATED
            )

        plan = self._diet_factory.create_plan(
            owner_id=client_id,
            created_by_id=coach_id,
            name=name,
            is_personal=False,
            coach_notes=coach_notes,
        )
        saved = await self._diet_repo.save(plan)
        await self._log_activity(
            PlanType.DIET, saved.id, coach_id, ActivityAction.CREATED
        )
        return saved

    async def get_client_diet(self, coach_id: UUID, client_id: UUID) -> DietPlan | None:
        """Return the active diet plan for an assigned client."""
        await self._verify_coach_for_client(coach_id, client_id)
        return await self._diet_repo.get_active_by_owner(client_id)

    async def add_diet_entry(
        self,
        coach_id: UUID,
        client_id: UUID,
        food_name: str,
        calories: Decimal,
        protein_g: Decimal,
        fat_g: Decimal,
        carbs_g: Decimal,
        order_index: int,
    ) -> DietEntry:
        """Add a food item to the client's active diet plan."""
        await self._verify_coach_for_client(coach_id, client_id)
        plan = await self._diet_repo.get_active_by_owner(client_id)
        if plan is None:
            raise NotFoundError(f"No active diet plan found for client {client_id}")
        entry = self._diet_factory.create_entry(
            plan_id=plan.id,
            food_name=food_name,
            calories=calories,
            protein_g=protein_g,
            fat_g=fat_g,
            carbs_g=carbs_g,
            order_index=order_index,
        )
        saved = await self._entry_repo.save(entry)
        await self._log_activity(
            PlanType.DIET,
            plan.id,
            coach_id,
            ActivityAction.ENTRY_ADDED,
            {"food_name": food_name, "calories": float(calories)},
        )
        return saved

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _verify_coach_for_client(self, coach_id: UUID, client_id: UUID) -> None:
        """
        Verify coach_id has an active MASTER_COACH assignment for client_id.
        A single assignment check covers both workout and diet write access.
        """
        assignment = await self._assignment_repo.get_active_by_role_for_client(
            client_id=client_id,
            staff_role=StaffRole.MASTER_COACH,
        )
        if assignment is None or assignment.staff_id != coach_id:
            raise ForbiddenError(
                f"Coach {coach_id} is not assigned to client {client_id} "
                "as a master coach"
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
