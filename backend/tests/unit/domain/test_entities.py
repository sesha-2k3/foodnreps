"""
Domain entity unit tests.

These tests verify:
1. Enum string values match the PostgreSQL enum strings in the schema exactly.
2. Computed @property methods return correct values.
3. __post_init__ validation catches business rule violations.
4. frozen=True prevents mutation (immutability guarantee).
5. Edge cases (None values, boundary conditions).

Design choice — no database, no FastAPI, no fixtures:
    Every test constructs entities directly with dataclasses.
    This is what "zero external dependencies" in the domain layer enables.
    The entire suite runs in milliseconds with `pytest tests/unit/domain/`.
"""

import dataclasses
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest

from domain.entities.assignment import ClientStaffAssignment
from domain.entities.diet import DietEntry, DietPlan
from domain.entities.enums import (
    ActivityAction,
    ExperienceLevel,
    FitnessGoal,
    PlanType,
    StaffRole,
    UserRole,
    VideoSource,
)
from domain.entities.profile import BodyMetric, IntakeProfile
from domain.entities.user import RefreshToken, User
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutLog,
    WorkoutPrescription,
    WorkoutProgram,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

NOW = datetime(2025, 4, 8, 12, 0, 0, tzinfo=timezone.utc)
TODAY = date(2025, 4, 8)


def make_user(**kwargs: Any) -> User:
    defaults: dict[str, Any] = {
        "id": uuid4(), "email": "test@example.com",
        "password_hash": "$2b$12$...", "full_name": "Test User",
        "role": UserRole.CLIENT, "is_active": True,
        "is_deleted": False, "deleted_at": None,
        "created_at": NOW, "updated_at": NOW,
    }
    return User(**{**defaults, **kwargs})


def make_prescription(**kwargs: Any) -> WorkoutPrescription:
    defaults: dict[str, Any] = {
        "id": uuid4(), "day_id": uuid4(), "order_index": 1,
        "exercise_name": "Squat", "warmup_sets": 2, "working_sets": 4,
        "reps_min": 6, "reps_max": 8, "reps_note": None,
        "prescribed_load_kg": Decimal("70"), "prescribed_load_text": None,
        "prescribed_rpe": None, "prescribed_rir": None, "rest_seconds": 180,
        "instructions": None, "created_at": NOW, "updated_at": NOW,
    }
    return WorkoutPrescription(**{**defaults, **kwargs})


def make_log(**kwargs: Any) -> WorkoutLog:
    defaults: dict[str, Any] = {
        "id": uuid4(), "prescription_id": uuid4(), "client_id": uuid4(),
        "exercise_name": None, "logged_at": TODAY,
        "actual_sets": 4, "actual_reps": 6, "actual_load_kg": Decimal("70"),
        "actual_rpe": Decimal("8.0"), "readiness": 8,
        "time_taken_seconds": 2580, "client_notes": None,
        "video_url": None, "video_source": None, "created_at": NOW,
    }
    return WorkoutLog(**{**defaults, **kwargs})


def make_diet_entry(**kwargs: Any) -> DietEntry:
    defaults: dict[str, Any] = {
        "id": uuid4(), "plan_id": uuid4(), "food_name": "Chicken breast",
        "calories": Decimal("165"), "protein_g": Decimal("31"),
        "fat_g": Decimal("3.6"), "carbs_g": Decimal("0"),
        "order_index": 10, "created_at": NOW, "updated_at": NOW,
    }
    return DietEntry(**{**defaults, **kwargs})


# ── Enum string values match PostgreSQL schema exactly ────────────────────────

class TestEnumValues:
    """
    Critical: these string values are stored in the database.
    If they differ from the PostgreSQL enum definition, INSERTs fail.

    Design: We compare using .value (the stored string) rather than
    comparing the enum member directly to a string literal. mypy strict
    mode flags direct enum-to-string equality as a non-overlapping type
    check — technically correct because they are different literal types
    even though str,Enum makes them equal at runtime. Using .value is
    both mypy-safe and more explicit about what we are testing.
    """

    def test_user_role_values(self) -> None:
        assert UserRole.CLIENT.value          == "client"
        assert UserRole.FITNESS_TRAINER.value == "fitness_trainer"
        assert UserRole.NUTRITIONIST.value    == "nutritionist"
        assert UserRole.MASTER_COACH.value    == "master_coach"
        assert UserRole.SUPER_ADMIN.value     == "super_admin"

    def test_staff_role_values(self) -> None:
        assert StaffRole.FITNESS_TRAINER.value == "fitness_trainer"
        assert StaffRole.NUTRITIONIST.value    == "nutritionist"
        assert StaffRole.MASTER_COACH.value    == "master_coach"

    def test_staff_role_is_subset_of_user_role(self) -> None:
        """StaffRole values must all exist in UserRole."""
        user_role_values = {r.value for r in UserRole}
        for staff_role in StaffRole:
            assert staff_role.value in user_role_values, (
                f"{staff_role.value!r} is in StaffRole but not UserRole"
            )

    def test_fitness_goal_values(self) -> None:
        assert FitnessGoal.WEIGHT_LOSS.value        == "weight_loss"
        assert FitnessGoal.MUSCLE_GAIN.value        == "muscle_gain"
        assert FitnessGoal.ENDURANCE.value          == "endurance"
        assert FitnessGoal.BODY_RECOMPOSITION.value == "body_recomposition"
        assert FitnessGoal.GENERAL_HEALTH.value     == "general_health"

    def test_plan_type_values(self) -> None:
        assert PlanType.WORKOUT.value == "workout"
        assert PlanType.DIET.value    == "diet"

    def test_activity_action_values(self) -> None:
        assert ActivityAction.CREATED.value          == "created"
        assert ActivityAction.UPDATED.value          == "updated"
        assert ActivityAction.ENTRY_ADDED.value      == "entry_added"
        assert ActivityAction.ENTRY_REMOVED.value    == "entry_removed"
        assert ActivityAction.ENTRY_UPDATED.value    == "entry_updated"
        assert ActivityAction.COMMENTED.value        == "commented"
        assert ActivityAction.ACTIVATED.value        == "activated"
        assert ActivityAction.DEACTIVATED.value      == "deactivated"
        assert ActivityAction.OVERRIDE_APPLIED.value == "override_applied"

    def test_video_source_values(self) -> None:
        assert VideoSource.EXTERNAL_LINK.value == "external_link"
        assert VideoSource.UPLOAD.value        == "upload"

    def test_enums_are_str_subclass(self) -> None:
        """
        str,Enum means every member IS a str instance.
        isinstance() is the mypy-safe way to verify this —
        it avoids the comparison-overlap false positive while
        still confirming the runtime behaviour we rely on.
        """
        assert isinstance(UserRole.CLIENT, str)
        assert isinstance(StaffRole.FITNESS_TRAINER, str)
        assert isinstance(PlanType.WORKOUT, str)


# ── User entity ───────────────────────────────────────────────────────────────

class TestUserEntity:

    def test_client_is_not_staff(self) -> None:
        user = make_user(role=UserRole.CLIENT)
        assert user.is_staff is False
        assert user.is_coach is False

    def test_fitness_trainer_is_staff_not_coach(self) -> None:
        user = make_user(role=UserRole.FITNESS_TRAINER)
        assert user.is_staff is True
        assert user.is_coach is False

    def test_master_coach_is_staff_and_coach(self) -> None:
        user = make_user(role=UserRole.MASTER_COACH)
        assert user.is_staff is True
        assert user.is_coach is True

    def test_can_write_workout_plans(self) -> None:
        trainer = make_user(role=UserRole.FITNESS_TRAINER)
        coach   = make_user(role=UserRole.MASTER_COACH)
        nutri   = make_user(role=UserRole.NUTRITIONIST)
        client  = make_user(role=UserRole.CLIENT)

        assert trainer.can_write_workout_plans is True
        assert coach.can_write_workout_plans   is True
        assert nutri.can_write_workout_plans   is False
        assert client.can_write_workout_plans  is False

    def test_can_write_diet_plans(self) -> None:
        nutri   = make_user(role=UserRole.NUTRITIONIST)
        coach   = make_user(role=UserRole.MASTER_COACH)
        trainer = make_user(role=UserRole.FITNESS_TRAINER)
        client  = make_user(role=UserRole.CLIENT)

        assert nutri.can_write_diet_plans   is True
        assert coach.can_write_diet_plans   is True
        assert trainer.can_write_diet_plans is False
        assert client.can_write_diet_plans  is False

    def test_user_is_frozen(self) -> None:
        user = make_user()
        with pytest.raises(dataclasses.FrozenInstanceError):
            user.email = "hacked@evil.com"  # type: ignore[misc]


# ── ClientStaffAssignment entity ──────────────────────────────────────────────

class TestAssignmentEntity:

    def test_is_active_when_ended_at_is_none(self) -> None:
        assignment = ClientStaffAssignment(
            id=uuid4(), client_id=uuid4(), staff_id=uuid4(),
            staff_role=StaffRole.FITNESS_TRAINER,
            assigned_at=NOW, ended_at=None, ended_reason=None,
            assigned_by=uuid4(),
        )
        assert assignment.is_active is True

    def test_is_not_active_when_ended_at_is_set(self) -> None:
        assignment = ClientStaffAssignment(
            id=uuid4(), client_id=uuid4(), staff_id=uuid4(),
            staff_role=StaffRole.FITNESS_TRAINER,
            assigned_at=NOW, ended_at=NOW, ended_reason="replaced",
            assigned_by=uuid4(),
        )
        assert assignment.is_active is False


# ── WorkoutPrescription entity ────────────────────────────────────────────────

class TestWorkoutPrescriptionEntity:

    def test_exercise_label_a_for_order_1(self) -> None:
        p = make_prescription(order_index=1)
        assert p.exercise_label == "A"

    def test_exercise_label_e_for_order_5(self) -> None:
        p = make_prescription(order_index=5)
        assert p.exercise_label == "E"

    def test_reps_display_fixed(self) -> None:
        p = make_prescription(reps_min=5, reps_max=5, reps_note=None)
        assert p.reps_display == "5"

    def test_reps_display_range(self) -> None:
        p = make_prescription(reps_min=6, reps_max=8, reps_note=None)
        assert p.reps_display == "6–8"

    def test_reps_display_open_note(self) -> None:
        p = make_prescription(
            reps_min=None, reps_max=None,
            reps_note="max reps — stop when speed drops"
        )
        assert p.reps_display == "max reps — stop when speed drops"

    def test_reps_display_minimum_with_plus(self) -> None:
        p = make_prescription(reps_min=12, reps_max=None, reps_note=None)
        assert p.reps_display == "12+"

    def test_requires_reps_min_or_reps_note(self) -> None:
        with pytest.raises(ValueError, match="reps_min or reps_note"):
            make_prescription(reps_min=None, reps_max=None, reps_note=None)

    def test_valid_with_only_reps_note(self) -> None:
        p = make_prescription(reps_min=None, reps_max=None, reps_note="AMRAP")
        assert p.reps_display == "AMRAP"


# ── WorkoutLog entity — tonnage ───────────────────────────────────────────────

class TestWorkoutLogTonnage:
    """
    Verified against the sample spreadsheet data:
        Bench:       4 sets × 6 reps × 70kg  = 1,680 kg
        Pendlay Rows: 4 sets × 7 reps × 70kg = 1,960 kg
        Leg Curls:   3 sets × 12 reps × 36kg = 1,296 kg
        Calf Raises: 3 sets × 18 reps × 50kg = 2,700 kg
        Deadlift:    6 sets × 5 reps × 110kg = 3,300 kg
    """

    def test_bench_press_tonnage(self) -> None:
        log = make_log(actual_sets=4, actual_reps=6, actual_load_kg=Decimal("70"))
        assert log.tonnage_kg == Decimal("1680")

    def test_pendlay_rows_tonnage(self) -> None:
        log = make_log(actual_sets=4, actual_reps=7, actual_load_kg=Decimal("70"))
        assert log.tonnage_kg == Decimal("1960")

    def test_leg_curls_tonnage(self) -> None:
        log = make_log(actual_sets=3, actual_reps=12, actual_load_kg=Decimal("36"))
        assert log.tonnage_kg == Decimal("1296")

    def test_calf_raises_tonnage(self) -> None:
        log = make_log(actual_sets=3, actual_reps=18, actual_load_kg=Decimal("50"))
        assert log.tonnage_kg == Decimal("2700")

    def test_bodyweight_tonnage_is_none(self) -> None:
        log = make_log(actual_load_kg=None)
        assert log.tonnage_kg is None

    def test_is_self_logged_when_no_prescription(self) -> None:
        log = make_log(
            prescription_id=None,
            exercise_name="Burpees",
        )
        assert log.is_self_logged is True

    def test_is_not_self_logged_when_prescription_exists(self) -> None:
        log = make_log(prescription_id=uuid4())
        assert log.is_self_logged is False

    def test_requires_exercise_name_when_no_prescription(self) -> None:
        with pytest.raises(ValueError, match="exercise_name"):
            make_log(prescription_id=None, exercise_name=None)

    def test_valid_self_logged_with_exercise_name(self) -> None:
        log = make_log(prescription_id=None, exercise_name="Burpees")
        assert log.exercise_name == "Burpees"


# ── DietEntry entity ──────────────────────────────────────────────────────────

class TestDietEntryEntity:

    def test_macro_derived_calories_protein_heavy(self) -> None:
        """protein×4 + fat×9 + carbs×4"""
        entry = make_diet_entry(
            protein_g=Decimal("30"),
            fat_g=Decimal("10"),
            carbs_g=Decimal("40"),
        )
        # 30×4 + 10×9 + 40×4 = 120 + 90 + 160 = 370
        assert entry.macro_derived_calories == Decimal("370")

    def test_macro_derived_calories_zero_carbs(self) -> None:
        entry = make_diet_entry(
            protein_g=Decimal("31"),
            fat_g=Decimal("3.6"),
            carbs_g=Decimal("0"),
        )
        # 31×4 + 3.6×9 + 0×4 = 124 + 32.4 + 0 = 156.4
        assert entry.macro_derived_calories == Decimal("156.4")

    def test_stored_calories_independent_of_macro_derivation(self) -> None:
        """Coach can set calories different from the macro-derived value."""
        entry = make_diet_entry(
            calories=Decimal("165"),    # what the label says
            protein_g=Decimal("31"),
            fat_g=Decimal("3.6"),
            carbs_g=Decimal("0"),
        )
        # Stored value from coach input
        assert entry.calories == Decimal("165")
        # Derived value (may differ from label due to fibre, rounding)
        assert entry.macro_derived_calories == Decimal("156.4")


# ── BodyMetric entity ─────────────────────────────────────────────────────────

class TestBodyMetricEntity:

    def test_valid_with_weight_only(self) -> None:
        metric = BodyMetric(
            id=uuid4(), user_id=uuid4(), recorded_by=uuid4(),
            recorded_at=NOW, weight_kg=Decimal("73.5"),
            body_fat_pct=None, muscle_mass_kg=None,
            notes=None, created_at=NOW,
        )
        assert metric.weight_kg == Decimal("73.5")

    def test_valid_with_all_measurements(self) -> None:
        metric = BodyMetric(
            id=uuid4(), user_id=uuid4(), recorded_by=uuid4(),
            recorded_at=NOW, weight_kg=Decimal("73.5"),
            body_fat_pct=Decimal("18.5"), muscle_mass_kg=Decimal("35.2"),
            notes="DEXA scan result", created_at=NOW,
        )
        assert metric.body_fat_pct == Decimal("18.5")

    def test_rejects_all_none_measurements(self) -> None:
        with pytest.raises(ValueError, match="at least one measurement"):
            BodyMetric(
                id=uuid4(), user_id=uuid4(), recorded_by=uuid4(),
                recorded_at=NOW, weight_kg=None,
                body_fat_pct=None, muscle_mass_kg=None,
                notes=None, created_at=NOW,
            )


# ── IntakeProfile — tuple immutability ────────────────────────────────────────

class TestIntakeProfileEntity:

    def test_injuries_stored_as_tuple(self) -> None:
        profile = IntakeProfile(
            id=uuid4(), client_id=uuid4(),
            fitness_goal=FitnessGoal.MUSCLE_GAIN,
            experience_level=ExperienceLevel.INTERMEDIATE,
            injuries=("lower_back", "left_knee"),
            equipment=("barbell", "pull_up_bar"),
            dietary_notes=None, target_weight_kg=None,
            current_weight_kg=Decimal("82.0"),
            completed_at=NOW, updated_at=NOW,
        )
        assert isinstance(profile.injuries, tuple)
        assert "lower_back" in profile.injuries

    def test_empty_injuries_is_valid(self) -> None:
        profile = IntakeProfile(
            id=uuid4(), client_id=uuid4(),
            fitness_goal=FitnessGoal.GENERAL_HEALTH,
            experience_level=ExperienceLevel.BEGINNER,
            injuries=(), equipment=(),
            dietary_notes=None, target_weight_kg=None,
            current_weight_kg=None,
            completed_at=NOW, updated_at=NOW,
        )
        assert profile.injuries == ()