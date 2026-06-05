"""
Diet repository implementations — mirrors workout_repository.py in structure.

Design choice — structural symmetry between workout and diet repositories:
    DietPlanRepository mirrors WorkoutProgramRepository exactly (same save()
    optimistic lock, same list/get pattern). This symmetry is intentional:
    it makes the code predictable. A developer who understands one repository
    understands the other. Divergence should only happen when the business
    domains genuinely differ.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import PlanVersionConflictError
from domain.entities.diet import DietEntry, DietPlan
from domain.interfaces.repositories import IDietEntryRepository, IDietPlanRepository
from infrastructure.db.models import DietEntryModel, DietPlanModel


class DietPlanRepository(IDietPlanRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: DietPlanModel) -> DietPlan:
        return DietPlan(
            id=m.id,
            owner_id=m.owner_id,
            created_by_id=m.created_by_id,
            name=m.name,
            is_active=m.is_active,
            is_personal=m.is_personal,
            is_template=m.is_template,
            coach_notes=m.coach_notes,
            version=m.version,
            last_modified_by=m.last_modified_by,
            last_modified_at=m.last_modified_at,
            override_reason=m.override_reason,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def get_by_id(self, plan_id: UUID) -> DietPlan | None:
        model = await self._session.get(DietPlanModel, plan_id)
        return self._to_entity(model) if model else None

    async def get_active_by_owner(self, owner_id: UUID) -> DietPlan | None:
        stmt = select(DietPlanModel).where(
            DietPlanModel.owner_id == owner_id,
            DietPlanModel.is_active == True,  # noqa: E712
            DietPlanModel.is_template == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_owner(self, owner_id: UUID) -> list[DietPlan]:
        stmt = (
            select(DietPlanModel)
            .where(DietPlanModel.owner_id == owner_id)
            .order_by(DietPlanModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, plan: DietPlan) -> DietPlan:
        model = await self._session.get(DietPlanModel, plan.id)
        if model is None:
            model = DietPlanModel(
                id=plan.id,
                owner_id=plan.owner_id,
                created_by_id=plan.created_by_id,
                name=plan.name,
                is_active=plan.is_active,
                is_personal=plan.is_personal,
                is_template=plan.is_template,
                coach_notes=plan.coach_notes,
                version=plan.version,
                last_modified_by=plan.last_modified_by,
                last_modified_at=plan.last_modified_at,
                override_reason=plan.override_reason,
                created_at=plan.created_at,
                updated_at=plan.updated_at,
            )
            self._session.add(model)
        else:
            if model.version != plan.version:
                raise PlanVersionConflictError(
                    f"Diet plan '{plan.name}' was modified by someone else "
                    f"(expected version {plan.version}, found {model.version}). "
                    "Please reload and try again."
                )
            model.name = plan.name
            model.is_active = plan.is_active
            model.is_personal = plan.is_personal
            model.is_template = plan.is_template
            model.coach_notes = plan.coach_notes
            model.version = plan.version + 1
            model.last_modified_by = plan.last_modified_by
            model.last_modified_at = plan.last_modified_at
            model.override_reason = plan.override_reason
            model.updated_at = plan.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)


class DietEntryRepository(IDietEntryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: DietEntryModel) -> DietEntry:
        return DietEntry(
            id=m.id,
            plan_id=m.plan_id,
            food_name=m.food_name,
            calories=m.calories,
            protein_g=m.protein_g,
            fat_g=m.fat_g,
            carbs_g=m.carbs_g,
            order_index=m.order_index,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def get_by_id(self, entry_id: UUID) -> DietEntry | None:
        model = await self._session.get(DietEntryModel, entry_id)
        return self._to_entity(model) if model else None

    async def list_by_plan(self, plan_id: UUID) -> list[DietEntry]:
        stmt = (
            select(DietEntryModel)
            .where(DietEntryModel.plan_id == plan_id)
            .order_by(DietEntryModel.order_index)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, entry: DietEntry) -> DietEntry:
        model = await self._session.get(DietEntryModel, entry.id)
        if model is None:
            model = DietEntryModel(
                id=entry.id,
                plan_id=entry.plan_id,
                food_name=entry.food_name,
                calories=entry.calories,
                protein_g=entry.protein_g,
                fat_g=entry.fat_g,
                carbs_g=entry.carbs_g,
                order_index=entry.order_index,
                created_at=entry.created_at,
                updated_at=entry.updated_at,
            )
            self._session.add(model)
        else:
            model.food_name = entry.food_name
            model.calories = entry.calories
            model.protein_g = entry.protein_g
            model.fat_g = entry.fat_g
            model.carbs_g = entry.carbs_g
            model.order_index = entry.order_index
            model.updated_at = entry.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, entry_id: UUID) -> None:
        model = await self._session.get(DietEntryModel, entry_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()
