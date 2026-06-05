"""
NutritionistService — manages diet plans on behalf of nutritionists.

Mirror of FitnessTrainerService across the diet domain boundary. The
design rationale is identical — see fitness_trainer_service.py for the
full explanation.

Key asymmetry from FitnessTrainerService:
    Nutritionists own diet plans and can read workout programmes.
    They cannot write workout prescriptions.
    The no-diet-write methods on FitnessTrainerService and the
    no-workout-write methods on NutritionistService together enforce
    the domain boundary at the service layer for each role.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from application.factories.diet_factory import DietFactory
from core.exceptions import ForbiddenError, NotFoundError
from domain.entities.diet import DietEntry, DietPlan
from domain.entities.enums import ActivityAction, PlanType, StaffRole
from domain.entities.plan import PlanActivityLog
from domain.interfaces.repositories import (
    IClientStaffAssignmentRepository,
    IDietEntryRepository,
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IWorkoutProgramRepository,
)


class NutritionistService:
    def __init__(
        self,
        assignment_repo: IClientStaffAssignmentRepository,
        diet_repo: IDietPlanRepository,
        entry_repo: IDietEntryRepository,
        workout_repo: IWorkoutProgramRepository,
        activity_log_repo: IPlanActivityLogRepository,
        diet_factory: DietFactory,
    ) -> None:
        self._assignment_repo = assignment_repo
        self._diet_repo = diet_repo
        self._entry_repo = entry_repo
        self._workout_repo = workout_repo
        self._activity_log_repo = activity_log_repo
        self._factory = diet_factory

    # ── Client list ───────────────────────────────────────────────────────────

    async def list_assigned_clients(self, nutritionist_id: UUID) -> list[UUID]:
        """Return client_ids of all currently assigned clients."""
        assignments = await self._assignment_repo.get_active_for_staff(nutritionist_id)
        return [a.client_id for a in assignments]

    # ── Diet plan CRUD ────────────────────────────────────────────────────────

    async def create_plan_for_client(
        self,
        nutritionist_id: UUID,
        client_id: UUID,
        name: str,
        coach_notes: str | None = None,
    ) -> DietPlan:
        """
        Create a new diet plan for an assigned client.
        Deactivates any existing active diet plan first.
        """
        await self._verify_nutritionist_for_client(nutritionist_id, client_id)

        existing = await self._diet_repo.get_active_by_owner(client_id)
        if existing is not None:
            deactivated = self._factory.deactivate_plan(existing)
            await self._diet_repo.save(deactivated)
            await self._log_activity(
                plan_type=PlanType.DIET,
                plan_id=existing.id,
                actor_id=nutritionist_id,
                action=ActivityAction.DEACTIVATED,
            )

        plan = self._factory.create_plan(
            owner_id=client_id,
            created_by_id=nutritionist_id,
            name=name,
            is_personal=False,
            coach_notes=coach_notes,
        )
        saved = await self._diet_repo.save(plan)
        await self._log_activity(
            plan_type=PlanType.DIET,
            plan_id=saved.id,
            actor_id=nutritionist_id,
            action=ActivityAction.CREATED,
        )
        return saved

    async def get_client_diet_plan(
        self, nutritionist_id: UUID, client_id: UUID
    ) -> DietPlan | None:
        """Return the active diet plan for an assigned client."""
        await self._verify_nutritionist_for_client(nutritionist_id, client_id)
        return await self._diet_repo.get_active_by_owner(client_id)

    # ── Entry CRUD ────────────────────────────────────────────────────────────

    async def add_entry(
        self,
        nutritionist_id: UUID,
        client_id: UUID,
        food_name: str,
        calories: Decimal,
        protein_g: Decimal,
        fat_g: Decimal,
        carbs_g: Decimal,
        order_index: int,
    ) -> DietEntry:
        """Add a food item to the client's active diet plan."""
        await self._verify_nutritionist_for_client(nutritionist_id, client_id)

        plan = await self._diet_repo.get_active_by_owner(client_id)
        if plan is None:
            raise NotFoundError(
                f"No active diet plan found for client {client_id}. "
                "Create a diet plan first."
            )

        entry = self._factory.create_entry(
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
            plan_type=PlanType.DIET,
            plan_id=plan.id,
            actor_id=nutritionist_id,
            action=ActivityAction.ENTRY_ADDED,
            metadata={"food_name": food_name, "calories": float(calories)},
        )
        return saved

    async def delete_entry(
        self,
        nutritionist_id: UUID,
        client_id: UUID,
        entry_id: UUID,
    ) -> None:
        """Remove a food entry from the client's diet plan."""
        await self._verify_nutritionist_for_client(nutritionist_id, client_id)

        entry = await self._entry_repo.get_by_id(entry_id)
        if entry is None:
            raise NotFoundError(f"Diet entry {entry_id} not found")

        await self._entry_repo.delete(entry_id)
        plan = await self._diet_repo.get_active_by_owner(client_id)
        if plan is not None:
            await self._log_activity(
                plan_type=PlanType.DIET,
                plan_id=plan.id,
                actor_id=nutritionist_id,
                action=ActivityAction.ENTRY_REMOVED,
                metadata={"food_name": entry.food_name, "entry_id": str(entry_id)},
            )

    # ── Read — workout programme (cross-domain visibility, read only) ──────────

    async def get_client_workout_programme(
        self, nutritionist_id: UUID, client_id: UUID
    ) -> object:
        """
        Read the client's active workout programme (no write access).
        Nutritionists can read workout programmes to calibrate calorie targets.
        """
        await self._verify_nutritionist_for_client(nutritionist_id, client_id)
        return await self._workout_repo.get_active_by_owner(client_id)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _verify_nutritionist_for_client(
        self, nutritionist_id: UUID, client_id: UUID
    ) -> None:
        """
        Verify nutritionist_id has an active NUTRITIONIST assignment for client_id.
        """
        assignment = await self._assignment_repo.get_active_by_role_for_client(
            client_id=client_id,
            staff_role=StaffRole.NUTRITIONIST,
        )
        if assignment is None or assignment.staff_id != nutritionist_id:
            raise ForbiddenError(
                f"Nutritionist {nutritionist_id} is not assigned to client {client_id}"
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
