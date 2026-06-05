"""
Unit tests for WorkoutFactory.

No database. No async. The factory is a pure synchronous class.
Tests verify: correct entity construction, all validation rules, and
that invalid inputs raise ValidationError (not raw ValueError).
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from application.factories.workout_factory import WorkoutFactory
from core.exceptions import ValidationError


@pytest.fixture
def factory() -> WorkoutFactory:
    return WorkoutFactory()


# ── create_program ────────────────────────────────────────────────────────────


class TestCreateProgram:
    def test_creates_programme_with_correct_fields(
        self, factory: WorkoutFactory
    ) -> None:
        owner = uuid4()
        creator = uuid4()
        p = factory.create_program(
            owner_id=owner, created_by_id=creator, name="12-Week Strength"
        )

        assert p.owner_id == owner
        assert p.created_by_id == creator
        assert p.name == "12-Week Strength"
        assert p.is_active is True
        assert p.is_personal is False
        assert p.is_template is False
        assert p.version == 1
        assert p.last_modified_by is None
        assert p.last_modified_at is None
        assert p.override_reason is None

    def test_strips_whitespace_from_name(self, factory: WorkoutFactory) -> None:
        p = factory.create_program(uuid4(), uuid4(), name="  Hypertrophy Phase  ")
        assert p.name == "Hypertrophy Phase"

    def test_blank_name_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            factory.create_program(uuid4(), uuid4(), name="   ")

    def test_empty_name_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError):
            factory.create_program(uuid4(), uuid4(), name="")

    def test_personal_flag_propagates(self, factory: WorkoutFactory) -> None:
        p = factory.create_program(uuid4(), uuid4(), name="My Plan", is_personal=True)
        assert p.is_personal is True

    def test_template_flag_propagates(self, factory: WorkoutFactory) -> None:
        p = factory.create_program(uuid4(), uuid4(), name="Template", is_template=True)
        assert p.is_template is True

    def test_each_call_generates_unique_id(self, factory: WorkoutFactory) -> None:
        p1 = factory.create_program(uuid4(), uuid4(), name="Plan A")
        p2 = factory.create_program(uuid4(), uuid4(), name="Plan B")
        assert p1.id != p2.id

    def test_deactivate_program_sets_is_active_false(
        self, factory: WorkoutFactory
    ) -> None:
        p = factory.create_program(uuid4(), uuid4(), name="Plan")
        deactivated = factory.deactivate_program(p)
        assert deactivated.is_active is False
        assert deactivated.id == p.id  # same programme, just deactivated


# ── create_week ───────────────────────────────────────────────────────────────


class TestCreateWeek:
    def test_creates_week_with_correct_fields(self, factory: WorkoutFactory) -> None:
        program_id = uuid4()
        w = factory.create_week(program_id=program_id, week_number=1, label="Week 1")
        assert w.program_id == program_id
        assert w.week_number == 1
        assert w.label == "Week 1"

    def test_default_label_when_blank(self, factory: WorkoutFactory) -> None:
        w = factory.create_week(uuid4(), week_number=1, label="  ")
        assert w.label == "Week"

    def test_week_number_zero_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="positive integer"):
            factory.create_week(uuid4(), week_number=0)

    def test_negative_week_number_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError):
            factory.create_week(uuid4(), week_number=-1)

    def test_week_number_one_is_valid(self, factory: WorkoutFactory) -> None:
        w = factory.create_week(uuid4(), week_number=1)
        assert w.week_number == 1


# ── create_day ────────────────────────────────────────────────────────────────


class TestCreateDay:
    def test_creates_day_with_correct_fields(self, factory: WorkoutFactory) -> None:
        week_id = uuid4()
        d = factory.create_day(week_id=week_id, day_number=2, label="Upper Body")
        assert d.week_id == week_id
        assert d.day_number == 2
        assert d.label == "Upper Body"

    def test_default_label_when_blank(self, factory: WorkoutFactory) -> None:
        d = factory.create_day(uuid4(), day_number=1, label="")
        assert d.label == "Day"

    def test_day_number_zero_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="positive integer"):
            factory.create_day(uuid4(), day_number=0)


# ── create_prescription ───────────────────────────────────────────────────────


class TestCreatePrescription:
    def test_creates_prescription_fixed_reps(self, factory: WorkoutFactory) -> None:
        day_id = uuid4()
        p = factory.create_prescription(
            day_id=day_id,
            order_index=1,
            exercise_name="Squat",
            working_sets=5,
            reps_min=5,
            reps_max=5,
        )
        assert p.day_id == day_id
        assert p.exercise_name == "Squat"
        assert p.reps_min == 5
        assert p.reps_max == 5
        assert p.exercise_label == "A"

    def test_creates_prescription_with_reps_note(self, factory: WorkoutFactory) -> None:
        p = factory.create_prescription(
            day_id=uuid4(),
            order_index=2,
            exercise_name="Pull-ups",
            reps_note="max reps",
        )
        assert p.reps_note == "max reps"
        assert p.exercise_label == "B"

    def test_strips_whitespace_from_exercise_name(
        self, factory: WorkoutFactory
    ) -> None:
        p = factory.create_prescription(
            day_id=uuid4(), order_index=1, exercise_name="  Deadlift  ", reps_min=3
        )
        assert p.exercise_name == "Deadlift"

    def test_empty_exercise_name_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="cannot be empty"):
            factory.create_prescription(
                day_id=uuid4(), order_index=1, exercise_name="  ", reps_min=5
            )

    def test_no_reps_info_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="reps_min or reps_note"):
            factory.create_prescription(
                day_id=uuid4(), order_index=1, exercise_name="Bench Press"
            )

    def test_reps_max_less_than_min_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="reps_max"):
            factory.create_prescription(
                day_id=uuid4(),
                order_index=1,
                exercise_name="Bench",
                reps_min=8,
                reps_max=6,  # invalid
            )

    def test_order_index_zero_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="positive integer"):
            factory.create_prescription(
                day_id=uuid4(), order_index=0, exercise_name="Squat", reps_min=5
            )

    def test_rpe_out_of_range_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="prescribed_rpe"):
            factory.create_prescription(
                day_id=uuid4(),
                order_index=1,
                exercise_name="Squat",
                reps_min=5,
                prescribed_rpe=Decimal("11.0"),
            )

    def test_valid_rpe_boundary_accepted(self, factory: WorkoutFactory) -> None:
        p = factory.create_prescription(
            day_id=uuid4(),
            order_index=1,
            exercise_name="Squat",
            reps_min=5,
            prescribed_rpe=Decimal("10.0"),
        )
        assert p.prescribed_rpe == Decimal("10.0")

    def test_negative_warmup_sets_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="warmup_sets"):
            factory.create_prescription(
                day_id=uuid4(),
                order_index=1,
                exercise_name="Squat",
                reps_min=5,
                warmup_sets=-1,
            )

    def test_zero_working_sets_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="working_sets"):
            factory.create_prescription(
                day_id=uuid4(),
                order_index=1,
                exercise_name="Squat",
                reps_min=5,
                working_sets=0,
            )

    def test_negative_rest_seconds_raises(self, factory: WorkoutFactory) -> None:
        with pytest.raises(ValidationError, match="rest_seconds"):
            factory.create_prescription(
                day_id=uuid4(),
                order_index=1,
                exercise_name="Squat",
                reps_min=5,
                rest_seconds=-30,
            )

    def test_load_kg_and_text_both_accepted(self, factory: WorkoutFactory) -> None:
        p = factory.create_prescription(
            day_id=uuid4(),
            order_index=1,
            exercise_name="Squat",
            reps_min=5,
            prescribed_load_kg=Decimal("100.0"),
            prescribed_load_text="70% of 1RM",
        )
        assert p.prescribed_load_kg == Decimal("100.0")
        assert p.prescribed_load_text == "70% of 1RM"

    def test_bodyweight_prescription_no_load_kg(self, factory: WorkoutFactory) -> None:
        p = factory.create_prescription(
            day_id=uuid4(),
            order_index=1,
            exercise_name="Pull-ups",
            reps_note="max reps",
            prescribed_load_text="BW",
        )
        assert p.prescribed_load_kg is None
        assert p.prescribed_load_text == "BW"
