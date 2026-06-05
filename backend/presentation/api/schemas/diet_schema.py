"""
Diet plan request/response schemas.

Design choice — macro_derived_calories exposed alongside calories:
    The stored calories field is set explicitly by the nutritionist (food
    labels don't always match the algebraic approximation protein×4+fat×9+carbs×4).
    The response exposes both: calories (the stored value the nutritionist set)
    and macro_derived_calories (the computed estimate from the entity @property).
    The frontend can display both and flag large discrepancies as a data-entry
    warning — without the domain entity ever needing display logic.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from domain.entities.diet import DietEntry, DietPlan


class DietEntryResponse(BaseModel):
    id: UUID
    food_name: str
    calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    macro_derived_calories: float  # derived from entity @property
    order_index: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, entry: DietEntry) -> "DietEntryResponse":
        return cls(
            id=entry.id,
            food_name=entry.food_name,
            calories=float(entry.calories),
            protein_g=float(entry.protein_g),
            fat_g=float(entry.fat_g),
            carbs_g=float(entry.carbs_g),
            macro_derived_calories=float(entry.macro_derived_calories),
            order_index=entry.order_index,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )


class AddDietEntryRequest(BaseModel):
    food_name: str
    calories: Decimal
    protein_g: Decimal
    fat_g: Decimal
    carbs_g: Decimal
    order_index: int


class DietPlanResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool
    is_personal: bool
    is_template: bool
    coach_notes: str | None
    owner_id: UUID
    created_by_id: UUID
    version: int
    override_reason: str | None
    created_at: datetime
    updated_at: datetime
    entries: list[DietEntryResponse] = []

    @classmethod
    def from_entity(
        cls,
        plan: DietPlan,
        entries: list[DietEntry] | None = None,
    ) -> "DietPlanResponse":
        return cls(
            id=plan.id,
            name=plan.name,
            is_active=plan.is_active,
            is_personal=plan.is_personal,
            is_template=plan.is_template,
            coach_notes=plan.coach_notes,
            owner_id=plan.owner_id,
            created_by_id=plan.created_by_id,
            version=plan.version,
            override_reason=plan.override_reason,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
            entries=[DietEntryResponse.from_entity(e) for e in (entries or [])],
        )


class CreateDietPlanRequest(BaseModel):
    name: str
    coach_notes: str | None = None
