"""
Diet domain entities: DietPlan and DietEntry.

Design choice — Concrete Table Inheritance (mirroring workout_programs):
    DietPlan and WorkoutProgram share the same structural columns but are
    separate tables and separate domain entities. They may diverge in
    future fields (DietPlan may gain allergen_flags, WorkoutProgram may
    gain periodization_style). A single Plan entity with a plan_type
    discriminator would force a shared structure that prevents this divergence.

    The shared structure (owner_id, created_by_id, name, is_active,
    is_personal, is_template, coach_notes, version, ...) is maintained
    by convention: any structural change is applied to both entities and
    both ORM models in the same Sprint.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class DietPlan:
    """
    A named diet plan owned by a user.
    Maps to `diet_plans`. Mirrors WorkoutProgram in structure.

    Design choice — name is required:
        Nutritionists create multiple plans over a coaching relationship:
        "Cutting Phase", "Maintenance", "Muscle Gain Protocol".
        Without a name, distinguishing plans requires reading created_at.
    """
    id:               UUID
    owner_id:         UUID
    created_by_id:    UUID
    name:             str
    is_active:        bool
    is_personal:      bool
    is_template:      bool
    coach_notes:      str | None
    version:          int
    last_modified_by: UUID | None
    last_modified_at: datetime | None
    override_reason:  str | None
    created_at:       datetime
    updated_at:       datetime


@dataclass(frozen=True)
class DietEntry:
    """
    A single food item within a diet plan.
    Maps to `diet_entries`.

    Design choice — Decimal for all macros, not float:
        Floating-point arithmetic accumulates errors across rows.
        Summing 6 diet entries in float produces values like 183.9000000000002g.
        Decimal(6,2) stores exact values. The difference is clinically relevant
        in a cutting phase where 5g of protein matters.

    Design choice — calories stored separately from macros:
        The algebraic approximation is protein×4 + fat×9 + carbs×4.
        In practice, calorie values from food labels don't always match
        (due to fibre, alcohol, rounding). The nutritionist sets the
        calorie target explicitly. macro_derived_calories is a @property
        that shows the approximation as a validation hint — not a GENERATED
        column that overrides the coach's input.

    Design choice — order_index for display ordering:
        The nutritionist controls how food items appear in the FitnessTable.
        A planned meal structure (breakfast → lunch → dinner → snacks) is
        meaningful context for the client. Gaps are allowed (10, 20, 30) so
        reordering two items only requires updating two rows.
    """
    id:          UUID
    plan_id:     UUID
    food_name:   str
    calories:    Decimal
    protein_g:   Decimal
    fat_g:       Decimal
    carbs_g:     Decimal
    order_index: int
    created_at:  datetime
    updated_at:  datetime

    @property
    def macro_derived_calories(self) -> Decimal:
        """
        Algebraic calorie estimate: protein×4 + fat×9 + carbs×4 kcal/g.

        This is shown alongside the coach-specified calories in the UI as
        a validation hint. A large discrepancy signals a data entry error.
        It does NOT override the stored calories value.
        """
        return (
            (self.protein_g * Decimal(4))
            + (self.fat_g   * Decimal(9))
            + (self.carbs_g * Decimal(4))
        )
