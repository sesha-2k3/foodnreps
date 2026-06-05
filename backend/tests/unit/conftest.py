"""
Shared fixtures and entity builder helpers for Sprint 3 unit tests.

The env vars below must be set before any module imports so that
pydantic-settings can instantiate core.config.Settings at import time
without finding a .env file (which does not exist in the unit test
environment).
"""

import os

# Set required env vars BEFORE any application module is imported.
# pydantic-settings reads these at module import time when Settings() runs.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_db",
)
os.environ.setdefault(
    "JWT_SECRET",
    "unit-test-secret-exactly-32-chars!!",
)
os.environ.setdefault(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_db_test",
)

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from domain.entities.assignment import ClientStaffAssignment
from domain.entities.diet import DietEntry, DietPlan
from domain.entities.enums import StaffRole, UserRole
from domain.entities.user import RefreshToken, User
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutPrescription,
    WorkoutProgram,
)

# ── Timestamp helper ──────────────────────────────────────────────────────────


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


# ── Entity builder helpers ────────────────────────────────────────────────────
# These are plain functions (not fixtures) so they can be called with custom
# arguments from within fixture bodies and test functions.


def make_user(
    role: UserRole = UserRole.CLIENT,
    is_active: bool = True,
    is_deleted: bool = False,
    **overrides: object,
) -> User:
    now = utcnow()
    return User(
        id=overrides.pop("id", uuid4()),  # type: ignore[arg-type]
        email=overrides.pop("email", f"user-{uuid4().hex[:8]}@example.com"),  # type: ignore[arg-type]
        password_hash=overrides.pop("password_hash", "$2b$12$fakehashfortest"),  # type: ignore[arg-type]
        full_name=overrides.pop("full_name", "Test User"),  # type: ignore[arg-type]
        role=role,
        is_active=is_active,
        is_deleted=is_deleted,
        deleted_at=None,
        created_at=now,
        updated_at=now,
    )


def make_assignment(
    client_id: UUID,
    staff_id: UUID,
    staff_role: StaffRole = StaffRole.FITNESS_TRAINER,
    ended_at: datetime | None = None,
    **overrides: object,
) -> ClientStaffAssignment:
    return ClientStaffAssignment(
        id=overrides.pop("id", uuid4()),  # type: ignore[arg-type]
        client_id=client_id,
        staff_id=staff_id,
        staff_role=staff_role,
        assigned_at=utcnow(),
        ended_at=ended_at,
        ended_reason=None if ended_at is None else "replaced",
        assigned_by=overrides.pop("assigned_by", uuid4()),  # type: ignore[arg-type]
    )


def make_workout_program(
    owner_id: UUID,
    created_by_id: UUID | None = None,
    is_active: bool = True,
    is_personal: bool = False,
    is_template: bool = False,
    **overrides: object,
) -> WorkoutProgram:
    now = utcnow()
    return WorkoutProgram(
        id=overrides.pop("id", uuid4()),  # type: ignore[arg-type]
        owner_id=owner_id,
        created_by_id=created_by_id or owner_id,
        name=overrides.pop("name", "Test Programme"),  # type: ignore[arg-type]
        is_active=is_active,
        is_personal=is_personal,
        is_template=is_template,
        coach_notes=None,
        version=overrides.pop("version", 1),  # type: ignore[arg-type]
        last_modified_by=None,
        last_modified_at=None,
        override_reason=None,
        created_at=now,
        updated_at=now,
    )


def make_diet_plan(
    owner_id: UUID,
    created_by_id: UUID | None = None,
    is_active: bool = True,
    is_personal: bool = False,
    **overrides: object,
) -> DietPlan:
    now = utcnow()
    return DietPlan(
        id=overrides.pop("id", uuid4()),  # type: ignore[arg-type]
        owner_id=owner_id,
        created_by_id=created_by_id or owner_id,
        name=overrides.pop("name", "Test Diet Plan"),  # type: ignore[arg-type]
        is_active=is_active,
        is_personal=is_personal,
        is_template=False,
        coach_notes=None,
        version=1,
        last_modified_by=None,
        last_modified_at=None,
        override_reason=None,
        created_at=now,
        updated_at=now,
    )


def make_program_week(
    program_id: UUID,
    week_number: int = 1,
    **overrides: object,
) -> ProgramWeek:
    return ProgramWeek(
        id=overrides.pop("id", uuid4()),  # type: ignore[arg-type]
        program_id=program_id,
        week_number=week_number,
        label=overrides.pop("label", f"Week {week_number}"),  # type: ignore[arg-type]
        notes=None,
        created_at=utcnow(),
    )


def make_program_day(
    week_id: UUID,
    day_number: int = 1,
    **overrides: object,
) -> ProgramDay:
    return ProgramDay(
        id=overrides.pop("id", uuid4()),  # type: ignore[arg-type]
        week_id=week_id,
        day_number=day_number,
        label=overrides.pop("label", f"Day {day_number}"),  # type: ignore[arg-type]
        notes=None,
        created_at=utcnow(),
    )


def make_prescription(
    day_id: UUID,
    order_index: int = 1,
    **overrides: object,
) -> WorkoutPrescription:
    now = utcnow()
    return WorkoutPrescription(
        id=overrides.pop("id", uuid4()),  # type: ignore[arg-type]
        day_id=day_id,
        order_index=order_index,
        exercise_name=overrides.pop("exercise_name", "Bench Press"),  # type: ignore[arg-type]
        warmup_sets=None,
        working_sets=4,
        reps_min=6,
        reps_max=8,
        reps_note=None,
        prescribed_load_kg=Decimal("70.00"),
        prescribed_load_text=None,
        prescribed_rpe=None,
        prescribed_rir=None,
        rest_seconds=180,
        instructions=None,
        created_at=now,
        updated_at=now,
    )


def make_refresh_token(
    user_id: UUID,
    is_revoked: bool = False,
    **overrides: object,
) -> RefreshToken:
    from datetime import timedelta

    return RefreshToken(
        id=overrides.pop("id", uuid4()),  # type: ignore[arg-type]
        user_id=user_id,
        token_id=overrides.pop("token_id", uuid4()),  # type: ignore[arg-type]
        is_revoked=is_revoked,
        expires_at=utcnow() + timedelta(days=7),
        revoked_at=None,
        created_at=utcnow(),
    )


def make_diet_entry(
    plan_id: UUID,
    order_index: int = 1,
    **overrides: object,
) -> DietEntry:
    now = utcnow()
    return DietEntry(
        id=overrides.pop("id", uuid4()),  # type: ignore[arg-type]
        plan_id=plan_id,
        food_name=overrides.pop("food_name", "Chicken Breast"),  # type: ignore[arg-type]
        calories=Decimal("165"),
        protein_g=Decimal("31"),
        fat_g=Decimal("3.6"),
        carbs_g=Decimal("0"),
        order_index=order_index,
        created_at=now,
        updated_at=now,
    )
