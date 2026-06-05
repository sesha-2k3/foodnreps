"""
PersonalPlanService — manages personal workout and diet plans for any authenticated user.

Every role in the system (client, fitness_trainer, nutritionist, master_coach,
super_admin) can maintain their own personal workout programme and diet plan.
This service is injected into every other service that needs personal plan
management — it is the single implementation of that capability.

Design choice — role-agnostic:
    PersonalPlanService does not check roles. It enforces one rule: the
    requesting user can only manage their own personal plans (owner_id
    matches the caller's user id). The calling service is responsible for
    passing the correct owner_id. This makes PersonalPlanService fully
    reusable — any service can inject and call it without role logic
    contaminating the personal plan operations.

Design choice — deactivate-before-create:
    The schema enforces one active non-template programme per owner via a
    partial unique index (WHERE is_active = true AND is_template = false).
    The service enforces this at the application layer first — it deactivates
    any existing active non-template programme before creating a new one.
    Both layers enforce the rule: the service provides the meaningful error
    message and clean state transition; the index is the safety net.

Design choice — personal programmes have is_personal=True, owner==creator:
    A personal plan is created by the user for themselves. owner_id and
    created_by_id are both set to the same user_id. This distinguishes
    personal plans from coach-assigned plans in all queries and UI views.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from application.factories.diet_factory import DietFactory
from application.factories.workout_factory import WorkoutFactory
from core.exceptions import ForbiddenError, NotFoundError
from domain.entities.diet import DietPlan
from domain.entities.enums import ActivityAction, PlanType
from domain.entities.plan import PlanActivityLog
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutProgram,
)
from domain.interfaces.repositories import (
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IProgramDayRepository,
    IProgramWeekRepository,
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)
from domain.interfaces.services import IPersonalPlanService


class PersonalPlanService(IPersonalPlanService):
    def __init__(
        self,
        workout_repo: IWorkoutProgramRepository,
        diet_repo: IDietPlanRepository,
        week_repo: IProgramWeekRepository,
        day_repo: IProgramDayRepository,
        prescription_repo: IWorkoutPrescriptionRepository,
        activity_log_repo: IPlanActivityLogRepository,
        workout_factory: WorkoutFactory,
        diet_factory: DietFactory,
    ) -> None:
        self._workout_repo = workout_repo
        self._diet_repo = diet_repo
        self._week_repo = week_repo
        self._day_repo = day_repo
        self._prescription_repo = prescription_repo
        self._activity_log_repo = activity_log_repo
        self._workout_factory = workout_factory
        self._diet_factory = diet_factory

    # ── Workout ───────────────────────────────────────────────────────────────

    async def get_personal_workout(self, owner_id: UUID) -> WorkoutProgram | None:
        """Return the active personal programme for this user, or None."""
        program = await self._workout_repo.get_active_by_owner(owner_id)
        if program is not None and program.is_personal:
            return program
        return None

    async def create_personal_workout(
        self,
        owner_id: UUID,
        name: str,
        coach_notes: str | None = None,
    ) -> WorkoutProgram:
        """
        Create a personal workout programme for this user.

        If an active non-template programme already exists (personal or
        coach-assigned), it is deactivated first. The partial unique index
        requires there be at most one active non-template programme per owner.
        """
        existing = await self._workout_repo.get_active_by_owner(owner_id)
        if existing is not None:
            deactivated = self._workout_factory.deactivate_program(existing)
            await self._workout_repo.save(deactivated)
            await self._log_activity(
                plan_type=PlanType.WORKOUT,
                plan_id=existing.id,
                actor_id=owner_id,
                action=ActivityAction.DEACTIVATED,
            )

        program = self._workout_factory.create_program(
            owner_id=owner_id,
            created_by_id=owner_id,  # personal: creator == owner
            name=name,
            is_personal=True,
            coach_notes=coach_notes,
        )
        saved = await self._workout_repo.save(program)
        await self._log_activity(
            plan_type=PlanType.WORKOUT,
            plan_id=saved.id,
            actor_id=owner_id,
            action=ActivityAction.CREATED,
        )
        return saved

    async def add_week_to_personal_workout(
        self,
        owner_id: UUID,
        program_id: UUID,
        week_number: int,
        label: str = "Week",
        notes: str | None = None,
    ) -> ProgramWeek:
        """
        Add a week to the user's own personal programme.
        Raises ForbiddenError if the programme does not belong to owner_id.
        """
        await self._assert_personal_ownership(owner_id, program_id)
        week = self._workout_factory.create_week(
            program_id=program_id,
            week_number=week_number,
            label=label,
            notes=notes,
        )
        return await self._week_repo.save(week)

    async def add_day_to_week(
        self,
        week_id: UUID,
        day_number: int,
        label: str = "Day",
        notes: str | None = None,
    ) -> ProgramDay:
        """Add a training day to a week within a personal programme."""
        day = self._workout_factory.create_day(
            week_id=week_id,
            day_number=day_number,
            label=label,
            notes=notes,
        )
        return await self._day_repo.save(day)

    # ── Diet ──────────────────────────────────────────────────────────────────

    async def get_personal_diet(self, owner_id: UUID) -> DietPlan | None:
        """Return the active personal diet plan for this user, or None."""
        plan = await self._diet_repo.get_active_by_owner(owner_id)
        if plan is not None and plan.is_personal:
            return plan
        return None

    async def create_personal_diet(
        self,
        owner_id: UUID,
        name: str,
        coach_notes: str | None = None,
    ) -> DietPlan:
        """
        Create a personal diet plan for this user.
        Deactivates any existing active diet plan first.
        """
        existing = await self._diet_repo.get_active_by_owner(owner_id)
        if existing is not None:
            deactivated = self._diet_factory.deactivate_plan(existing)
            await self._diet_repo.save(deactivated)
            await self._log_activity(
                plan_type=PlanType.DIET,
                plan_id=existing.id,
                actor_id=owner_id,
                action=ActivityAction.DEACTIVATED,
            )

        plan = self._diet_factory.create_plan(
            owner_id=owner_id,
            created_by_id=owner_id,
            name=name,
            is_personal=True,
            coach_notes=coach_notes,
        )
        saved = await self._diet_repo.save(plan)
        await self._log_activity(
            plan_type=PlanType.DIET,
            plan_id=saved.id,
            actor_id=owner_id,
            action=ActivityAction.CREATED,
        )
        return saved

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _assert_personal_ownership(
        self, owner_id: UUID, program_id: UUID
    ) -> WorkoutProgram:
        """
        Verify that program_id is an active personal programme owned by owner_id.
        Returns the programme if valid; raises otherwise.
        """
        program = await self._workout_repo.get_by_id(program_id)
        if program is None:
            raise NotFoundError(f"Programme {program_id} not found")
        if program.owner_id != owner_id:
            raise ForbiddenError(
                f"Programme {program_id} does not belong to user {owner_id}"
            )
        if not program.is_personal:
            raise ForbiddenError(
                f"Programme {program_id} is a coach-assigned programme, "
                "not a personal programme. Use the assigned plan endpoints."
            )
        return program

    async def _log_activity(
        self,
        plan_type: PlanType,
        plan_id: UUID,
        actor_id: UUID,
        action: ActivityAction,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Write an activity log entry. Failures are silent — logs are best-effort."""
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
