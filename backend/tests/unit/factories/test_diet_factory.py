"""
Unit tests for DietFactory.

No database. No async. Pure synchronous factory validation.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from application.factories.diet_factory import DietFactory
from core.exceptions import ValidationError


@pytest.fixture
def factory() -> DietFactory:
    return DietFactory()


# ── create_plan ───────────────────────────────────────────────────────────────


class TestCreatePlan:
    def test_creates_plan_with_correct_fields(self, factory: DietFactory) -> None:
        owner = uuid4()
        creator = uuid4()
        plan = factory.create_plan(
            owner_id=owner, created_by_id=creator, name="Cutting Phase"
        )

        assert plan.owner_id == owner
        assert plan.created_by_id == creator
        assert plan.name == "Cutting Phase"
        assert plan.is_active is True
        assert plan.is_personal is False
        assert plan.is_template is False
        assert plan.version == 1
        assert plan.last_modified_by is None
        assert plan.override_reason is None

    def test_strips_whitespace_from_name(self, factory: DietFactory) -> None:
        plan = factory.create_plan(uuid4(), uuid4(), name="  Muscle Gain  ")
        assert plan.name == "Muscle Gain"

    def test_blank_name_raises(self, factory: DietFactory) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            factory.create_plan(uuid4(), uuid4(), name="   ")

    def test_empty_name_raises(self, factory: DietFactory) -> None:
        with pytest.raises(ValidationError):
            factory.create_plan(uuid4(), uuid4(), name="")

    def test_personal_flag_propagates(self, factory: DietFactory) -> None:
        plan = factory.create_plan(uuid4(), uuid4(), name="My Diet", is_personal=True)
        assert plan.is_personal is True

    def test_each_call_generates_unique_id(self, factory: DietFactory) -> None:
        p1 = factory.create_plan(uuid4(), uuid4(), name="Plan A")
        p2 = factory.create_plan(uuid4(), uuid4(), name="Plan B")
        assert p1.id != p2.id

    def test_deactivate_plan_sets_is_active_false(self, factory: DietFactory) -> None:
        plan = factory.create_plan(uuid4(), uuid4(), name="Plan")
        deactivated = factory.deactivate_plan(plan)
        assert deactivated.is_active is False
        assert deactivated.id == plan.id  # same plan entity

    def test_deactivate_updates_updated_at(self, factory: DietFactory) -> None:
        plan = factory.create_plan(uuid4(), uuid4(), name="Plan")
        deactivated = factory.deactivate_plan(plan)
        assert deactivated.updated_at >= plan.updated_at


# ── create_entry ──────────────────────────────────────────────────────────────


class TestCreateEntry:
    def test_creates_entry_with_correct_macros(self, factory: DietFactory) -> None:
        plan_id = uuid4()
        entry = factory.create_entry(
            plan_id=plan_id,
            food_name="Chicken Breast",
            calories=Decimal("165"),
            protein_g=Decimal("31"),
            fat_g=Decimal("3.6"),
            carbs_g=Decimal("0"),
            order_index=1,
        )
        assert entry.plan_id == plan_id
        assert entry.food_name == "Chicken Breast"
        assert entry.calories == Decimal("165")
        assert entry.protein_g == Decimal("31")
        assert entry.fat_g == Decimal("3.6")
        assert entry.carbs_g == Decimal("0")
        assert entry.order_index == 1

    def test_strips_whitespace_from_food_name(self, factory: DietFactory) -> None:
        entry = factory.create_entry(
            uuid4(),
            "  Oats  ",
            Decimal("350"),
            Decimal("12"),
            Decimal("6"),
            Decimal("60"),
            1,
        )
        assert entry.food_name == "Oats"

    def test_blank_food_name_raises(self, factory: DietFactory) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            factory.create_entry(
                uuid4(),
                "  ",
                Decimal("100"),
                Decimal("10"),
                Decimal("5"),
                Decimal("10"),
                1,
            )

    def test_negative_calories_raises(self, factory: DietFactory) -> None:
        with pytest.raises(ValidationError, match="calories"):
            factory.create_entry(
                uuid4(),
                "Bad Food",
                Decimal("-10"),
                Decimal("10"),
                Decimal("5"),
                Decimal("10"),
                1,
            )

    def test_negative_protein_raises(self, factory: DietFactory) -> None:
        with pytest.raises(ValidationError, match="protein_g"):
            factory.create_entry(
                uuid4(),
                "Bad Macro",
                Decimal("100"),
                Decimal("-5"),
                Decimal("5"),
                Decimal("10"),
                1,
            )

    def test_negative_fat_raises(self, factory: DietFactory) -> None:
        with pytest.raises(ValidationError, match="fat_g"):
            factory.create_entry(
                uuid4(),
                "Bad Macro",
                Decimal("100"),
                Decimal("10"),
                Decimal("-1"),
                Decimal("10"),
                1,
            )

    def test_negative_carbs_raises(self, factory: DietFactory) -> None:
        with pytest.raises(ValidationError, match="carbs_g"):
            factory.create_entry(
                uuid4(),
                "Bad Macro",
                Decimal("100"),
                Decimal("10"),
                Decimal("5"),
                Decimal("-2"),
                1,
            )

    def test_zero_order_index_raises(self, factory: DietFactory) -> None:
        with pytest.raises(ValidationError, match="positive integer"):
            factory.create_entry(
                uuid4(),
                "Food",
                Decimal("100"),
                Decimal("10"),
                Decimal("5"),
                Decimal("20"),
                0,
            )

    def test_zero_macros_are_valid(self, factory: DietFactory) -> None:
        """Zero-calorie / zero-macro entries are valid (e.g. water, diet drinks)."""
        entry = factory.create_entry(
            uuid4(),
            "Sparkling Water",
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
            1,
        )
        assert entry.calories == Decimal("0")

    def test_macro_derived_calories_property(self, factory: DietFactory) -> None:
        """Verify the @property on the entity computes correctly."""
        entry = factory.create_entry(
            uuid4(),
            "Rice",
            Decimal("200"),
            Decimal("4"),
            Decimal("0"),
            Decimal("45"),
            1,
        )
        # protein×4 + fat×9 + carbs×4 = 4×4 + 0×9 + 45×4 = 16 + 0 + 180 = 196
        assert entry.macro_derived_calories == Decimal("196")
