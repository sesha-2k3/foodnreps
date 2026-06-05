"""
SQLAlchemy ORM models — the storage schema for Food 'n' Reps.

CRITICAL DISTINCTION: These models are NOT the domain entities.
    ORM models  → how data is stored (columns, types, constraints, indexes)
    Domain entities → what data means (business rules, invariants, properties)
    Repositories → translate between the two

Design choice — SQLAlchemy 2.0 new-style mapped_column + Mapped[T]:
    The new API (`Mapped[T]`, `mapped_column()`) is type-safe and integrates
    with mypy natively. The old API (`Column(Type)`) still works but loses
    type inference. Since we run mypy --strict, the new API is required.

Design choice — model fields repeat entity fields, with storage-specific additions:
    server_default, onupdate, ForeignKey, Index, CheckConstraint — these are
    storage concerns that do not belong in the domain entity. The model is the
    right place for them.

Design choice — SAEnum with Python enum classes:
    `SAEnum(UserRole, name="user_role")` maps to a PostgreSQL native enum type.
    The `name` argument matches the PostgreSQL enum type name defined in the schema.
    SQLAlchemy stores the string value (e.g., "client") and reconstructs the
    Python enum member on read. This is correct because our enums use `str, Enum`.

Design choice — Partial unique indexes via Index with postgresql_where:
    The business rules "one active fitness_trainer per client" etc. are enforced
    at two levels: AssignmentService (application) and partial unique indexes (DB).
    The DB level is the safety net — it makes violations structurally impossible
    even if service code has a bug.

Design choice — CASCADE behaviour matches schema document:
    workout_prescriptions → program_days: CASCADE (prescriptions die with their day)
    workout_logs.prescription_id → workout_prescriptions: SET NULL (logs outlive prescriptions)
    diet_entries → diet_plans: CASCADE (entries die with their plan)
    The asymmetry is intentional — training history is precious, structural containers are not.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy import Computed
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from domain.entities.enums import (
    ActivityAction,
    ExperienceLevel,
    FitnessGoal,
    PlanType,
    StaffRole,
    UserRole,
    VideoSource,
)
from infrastructure.db.base import Base


def _sa_enum(enum_cls: type, name: str) -> SAEnum:
    """
    PostgreSQL enum using string VALUES not member NAMES.

    SAEnum(StaffRole) by default uses names: 'FITNESS_TRAINER', 'MASTER_COACH'.
    Our str,Enum classes define values: 'fitness_trainer', 'master_coach'.
    values_callable ensures the PostgreSQL type stores what we actually want.
    """
    return SAEnum(
        enum_cls,
        name=name,
        values_callable=lambda x: [e.value for e in x],
    )


# ── Identity & Auth ───────────────────────────────────────────────────────────


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        _sa_enum(UserRole, "user_role"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_users_role", "role"),
        Index(
            "idx_users_active", "is_active", postgresql_where=text("is_deleted = false")
        ),
    )


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), nullable=False, unique=True
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_rt_token_id", "token_id"),
        Index("idx_rt_user_id", "user_id"),
        Index(
            "idx_rt_active", "expires_at", postgresql_where=text("is_revoked = false")
        ),
    )


# ── Coaching relationships ────────────────────────────────────────────────────


class ClientStaffAssignmentModel(Base):
    __tablename__ = "client_staff_assignments"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    staff_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    staff_role: Mapped[StaffRole] = mapped_column(
        _sa_enum(StaffRole, "staff_role_enum"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    assigned_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        # Business rules: one active assignment per role per client
        Index(
            "uq_one_active_trainer",
            "client_id",
            unique=True,
            postgresql_where=text(
                "ended_at IS NULL AND staff_role = 'fitness_trainer'"
            ),
        ),
        Index(
            "uq_one_active_nutritionist",
            "client_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL AND staff_role = 'nutritionist'"),
        ),
        Index(
            "uq_one_active_master_coach",
            "client_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL AND staff_role = 'master_coach'"),
        ),
        Index(
            "idx_assignments_staff_active",
            "staff_id",
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index("idx_assignments_client", "client_id"),
    )


# ── Client profile ────────────────────────────────────────────────────────────


class IntakeProfileModel(Base):
    __tablename__ = "intake_profiles"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True
    )
    fitness_goal: Mapped[FitnessGoal] = mapped_column(
        _sa_enum(FitnessGoal, "fitness_goal_enum"), nullable=False
    )
    experience_level: Mapped[ExperienceLevel] = mapped_column(
        _sa_enum(ExperienceLevel, "experience_level_enum"), nullable=False
    )
    injuries: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default=text("'{}'")
    )
    equipment: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default=text("'{}'")
    )
    dietary_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    current_weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class BodyMetricModel(Base):
    __tablename__ = "body_metrics"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    recorded_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    muscle_mass_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "weight_kg IS NOT NULL OR body_fat_pct IS NOT NULL OR muscle_mass_kg IS NOT NULL",
            name="chk_at_least_one_metric",
        ),
        Index("idx_body_metrics_user_time", "user_id", "recorded_at"),
    )


# ── Workout programme hierarchy ───────────────────────────────────────────────


class WorkoutProgramModel(Base):
    __tablename__ = "workout_programs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_personal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_template: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    coach_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    last_modified_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    last_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    override_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        # One active non-template programme per owner
        Index(
            "uq_one_active_workout_program",
            "owner_id",
            unique=True,
            postgresql_where=text("is_active = true AND is_template = false"),
        ),
        Index("idx_workout_programs_owner", "owner_id"),
    )


class ProgramWeekModel(Base):
    __tablename__ = "program_weeks"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    program_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workout_programs.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    label: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default=text("'Week'")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("uq_program_week", "program_id", "week_number", unique=True),
        Index("idx_program_weeks_ord", "program_id", "week_number"),
    )


class ProgramDayModel(Base):
    __tablename__ = "program_days"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    week_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("program_weeks.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    label: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default=text("'Day'")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("uq_week_day", "week_id", "day_number", unique=True),
        Index("idx_program_days_ord", "week_id", "day_number"),
    )


class WorkoutPrescriptionModel(Base):
    """
    The BLUE side of the spreadsheet — coach-authored exercise prescriptions.

    Design choice — order_index as integer, rendered as A/B/C in the UI:
        Storing as integer keeps the DB schema clean and sort operations trivial.
        chr(64 + order_index) converts 1→A, 2→B in the presentation layer.
    """

    __tablename__ = "workout_prescriptions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    day_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("program_days.id", ondelete="CASCADE"),
        nullable=False,
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    exercise_name: Mapped[str] = mapped_column(String(255), nullable=False)
    warmup_sets: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    working_sets: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    reps_min: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    reps_max: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    reps_note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    prescribed_load_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    prescribed_load_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prescribed_rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    prescribed_rir: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "reps_min IS NOT NULL OR reps_note IS NOT NULL",
            name="chk_reps_defined",
        ),
        Index("uq_day_exercise_order", "day_id", "order_index", unique=True),
        Index("idx_prescriptions_day_ord", "day_id", "order_index"),
    )


class WorkoutLogModel(Base):
    """
    The RED side of the spreadsheet — client performance records.

    Design choice — tonnage_kg as GENERATED ALWAYS AS STORED column:
        The database computes tonnage = sets × reps × load automatically on
        every write. It cannot get out of sync (unlike a manually-maintained column).
        The domain entity's @property computes the same value from the same
        source fields — both are correct by construction.

    Design choice — ON DELETE SET NULL on prescription_id:
        If a coach restructures a programme and deletes a day or prescription,
        the client's training logs must survive. SET NULL preserves the log row
        but unlinks it from the now-deleted prescription.
    """

    __tablename__ = "workout_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    prescription_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workout_prescriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    client_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    exercise_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logged_at: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    actual_sets: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    actual_reps: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    actual_load_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    actual_rpe: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    readiness: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tonnage_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        Computed(
            "CASE WHEN actual_load_kg IS NOT NULL "
            "THEN CAST(actual_sets AS NUMERIC) * actual_reps * actual_load_kg "
            "ELSE NULL END",
            persisted=True,
        ),
        nullable=True,
    )
    video_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    video_source: Mapped[VideoSource | None] = mapped_column(
        _sa_enum(VideoSource, "video_source_enum"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "prescription_id IS NOT NULL OR exercise_name IS NOT NULL",
            name="chk_exercise_reference",
        ),
        Index("idx_workout_logs_client_date", "client_id", "logged_at"),
        Index(
            "idx_workout_logs_prescription",
            "prescription_id",
            postgresql_where=text("prescription_id IS NOT NULL"),
        ),
    )


# ── Diet plan ─────────────────────────────────────────────────────────────────


class DietPlanModel(Base):
    """Mirrors WorkoutProgramModel in structure — see schema rationale for why they are separate tables."""

    __tablename__ = "diet_plans"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    owner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_personal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_template: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    coach_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    last_modified_by: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    last_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    override_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "uq_one_active_diet_plan",
            "owner_id",
            unique=True,
            postgresql_where=text("is_active = true AND is_template = false"),
        ),
        Index("idx_diet_plans_owner", "owner_id"),
    )


class DietEntryModel(Base):
    __tablename__ = "diet_entries"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    plan_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("diet_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    calories: Mapped[Decimal] = mapped_column(Numeric(7, 2), nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("calories >= 0", name="chk_calories_non_negative"),
        CheckConstraint("protein_g >= 0", name="chk_protein_non_negative"),
        CheckConstraint("fat_g >= 0", name="chk_fat_non_negative"),
        CheckConstraint("carbs_g >= 0", name="chk_carbs_non_negative"),
        Index("idx_diet_entries_plan_ord", "plan_id", "order_index"),
    )


# ── Plan cross-cutting ────────────────────────────────────────────────────────


class PlanVersionModel(Base):
    """
    Append-only JSONB snapshots of plan state.

    Design choice — plan_id has no ForeignKey constraint:
        Version history must outlive the plan it references. If a plan is
        ever hard-deleted by a DBA, the version history survives as a
        legal and coaching record. Referential integrity is enforced at
        the application layer (services always verify the plan exists
        before writing a version row).
    """

    __tablename__ = "plan_versions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    plan_type: Mapped[PlanType] = mapped_column(
        _sa_enum(PlanType, "plan_type_enum"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    modified_by: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_plan_versions_lookup", "plan_type", "plan_id", "modified_at"),
    )


class PlanCommentModel(Base):
    """Soft-deleted coaching comments. plan_id is a soft reference — no FK constraint."""

    __tablename__ = "plan_comments"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    plan_type: Mapped[PlanType] = mapped_column(
        _sa_enum(PlanType, "plan_type_enum"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    author_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "idx_plan_comments_lookup",
            "plan_type",
            "plan_id",
            "created_at",
            postgresql_where=text("is_deleted = false"),
        ),
    )


class PlanActivityLogModel(Base):
    """Append-only event feed for cross-domain visibility. plan_id is a soft reference."""

    __tablename__ = "plan_activity_log"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    plan_type: Mapped[PlanType] = mapped_column(
        _sa_enum(PlanType, "plan_type_enum"), nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    action: Mapped[ActivityAction] = mapped_column(
        _sa_enum(ActivityAction, "activity_action_enum"), nullable=False
    )
    log_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_activity_log_plan", "plan_type", "plan_id", "occurred_at"),
        Index("idx_activity_log_actor", "actor_id", "occurred_at"),
    )
