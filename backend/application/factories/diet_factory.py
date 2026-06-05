"""
DietFactory — the single construction point for diet domain entities.

Mirrors WorkoutFactory in design rationale. See workout_factory.py for
the full design explanation. The summary:
- Factory enforces construction-time business invariants.
- Factory raises ValidationError (domain exception) not ValueError.
- Factory generates uuid4() — services never call it directly.
- deactivate_plan() produces a new frozen entity via dataclasses.replace().
"""

import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from core.exceptions import ValidationError
from domain.entities.diet import DietEntry, DietPlan


class DietFactory:
    """Creates and transforms diet domain entities."""

    # ── Plan ──────────────────────────────────────────────────────────────────

    def create_plan(
        self,
        owner_id: UUID,
        created_by_id: UUID,
        name: str,
        is_personal: bool = False,
        is_template: bool = False,
        coach_notes: str | None = None,
    ) -> DietPlan:
        """
        Create a new DietPlan entity.

        Validates: name is not blank after stripping whitespace.

        Defaults:
        - is_active=True, version=1, audit fields all None.
        """
        stripped = name.strip()
        if not stripped:
            raise ValidationError("Diet plan name cannot be empty")
        now = datetime.now(tz=UTC)
        return DietPlan(
            id=uuid4(),
            owner_id=owner_id,
            created_by_id=created_by_id,
            name=stripped,
            is_active=True,
            is_personal=is_personal,
            is_template=is_template,
            coach_notes=coach_notes,
            version=1,
            last_modified_by=None,
            last_modified_at=None,
            override_reason=None,
            created_at=now,
            updated_at=now,
        )

    def deactivate_plan(self, plan: DietPlan) -> DietPlan:
        """
        Return a deactivated copy of an existing plan.
        Called before creating a new active diet plan for the same owner.
        """
        return dataclasses.replace(
            plan,
            is_active=False,
            updated_at=datetime.now(tz=UTC),
        )

    # ── Entry ─────────────────────────────────────────────────────────────────

    def create_entry(
        self,
        plan_id: UUID,
        food_name: str,
        calories: Decimal,
        protein_g: Decimal,
        fat_g: Decimal,
        carbs_g: Decimal,
        order_index: int,
    ) -> DietEntry:
        """
        Create a DietEntry entity.

        Validates (mirrors DB CHECK constraints):
        - food_name is not blank.
        - calories >= 0 (mirrors CHECK (calories >= 0))
        - protein_g >= 0 (mirrors CHECK (protein_g >= 0))
        - fat_g >= 0 (mirrors CHECK (fat_g >= 0))
        - carbs_g >= 0 (mirrors CHECK (carbs_g >= 0))
        - order_index >= 1

        Design note — calories stored separately from macros:
            The nutritionist specifies the calorie target explicitly.
            It is not recomputed from protein×4 + fat×9 + carbs×4 because
            that algebraic approximation does not always match food label
            values (due to fibre, alcohol, and rounding). The entity's
            macro_derived_calories property shows the estimate as a
            validation hint — it never overrides the stored value.
        """
        stripped = food_name.strip()
        if not stripped:
            raise ValidationError("Food name cannot be empty")
        if calories < Decimal("0"):
            raise ValidationError(f"calories cannot be negative, got {calories}")
        if protein_g < Decimal("0"):
            raise ValidationError(f"protein_g cannot be negative, got {protein_g}")
        if fat_g < Decimal("0"):
            raise ValidationError(f"fat_g cannot be negative, got {fat_g}")
        if carbs_g < Decimal("0"):
            raise ValidationError(f"carbs_g cannot be negative, got {carbs_g}")
        if order_index < 1:
            raise ValidationError(
                f"order_index must be a positive integer, got {order_index}"
            )
        now = datetime.now(tz=UTC)
        return DietEntry(
            id=uuid4(),
            plan_id=plan_id,
            food_name=stripped,
            calories=calories,
            protein_g=protein_g,
            fat_g=fat_g,
            carbs_g=carbs_g,
            order_index=order_index,
            created_at=now,
            updated_at=now,
        )
