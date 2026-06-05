"""
Food 'n' Reps — application enums.

Design choice — str, Enum (not plain Enum):
    All enums inherit from both str and Enum. This means:
    - Each value IS a string: UserRole.CLIENT == "client" is True.
    - JSON-serializable by default (FastAPI / Pydantic handle str subclasses natively).
    - Comparable with raw strings: no need to call .value everywhere.
    - SQLAlchemy stores and retrieves the string value directly.

Design choice — values must match PostgreSQL enum strings exactly:
    These strings are what go into the database. The SQLAlchemy ORM models
    (Sprint 2) will map these Python enums to PostgreSQL enums using the same
    string values. If a value here differs from the PostgreSQL enum, inserts
    fail at the DB level. The unit tests in test_entities.py verify this
    alignment explicitly.

Design choice — StaffRole is a subset of UserRole:
    StaffRole contains only the three roles that can be assigned to clients.
    Having a separate enum (rather than reusing UserRole) makes function
    signatures explicit: a parameter typed as StaffRole cannot accidentally
    receive UserRole.CLIENT or UserRole.SUPER_ADMIN.
"""

from enum import StrEnum


class UserRole(StrEnum):
    """Role of a user in the platform. Stored in users.role."""

    CLIENT = "client"
    FITNESS_TRAINER = "fitness_trainer"
    NUTRITIONIST = "nutritionist"
    MASTER_COACH = "master_coach"
    SUPER_ADMIN = "super_admin"


class StaffRole(StrEnum):
    """
    Subset of UserRole — only roles that can be assigned to a client.
    Stored in client_staff_assignments.staff_role.

    Design: A separate enum prevents accidentally assigning a CLIENT or
    SUPER_ADMIN as coaching staff to another client.
    """

    FITNESS_TRAINER = "fitness_trainer"
    NUTRITIONIST = "nutritionist"
    MASTER_COACH = "master_coach"


class FitnessGoal(StrEnum):
    """Client's primary fitness objective. Stored in intake_profiles.fitness_goal."""

    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    ENDURANCE = "endurance"
    BODY_RECOMPOSITION = "body_recomposition"
    GENERAL_HEALTH = "general_health"


class ExperienceLevel(StrEnum):
    """Client's self-reported training experience. Stored in intake_profiles.experience_level."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class PlanType(StrEnum):
    """
    Discriminator for polymorphic plan references.
    Used in plan_versions, plan_comments, plan_activity_log.

    Design: These three tables use (plan_type, plan_id) to reference either
    workout_programs or diet_plans without two nullable FK columns.
    """

    WORKOUT = "workout"
    DIET = "diet"


class ActivityAction(StrEnum):
    """
    Actions recorded in plan_activity_log.
    Enables filtering ("show me all entry_added events"), aggregation,
    and UI icon selection without parsing free-text descriptions.
    """

    CREATED = "created"
    UPDATED = "updated"
    ENTRY_ADDED = "entry_added"
    ENTRY_REMOVED = "entry_removed"
    ENTRY_UPDATED = "entry_updated"
    COMMENTED = "commented"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    OVERRIDE_APPLIED = "override_applied"


class VideoSource(StrEnum):
    """
    How the video was attached to a workout log (Phase 2 field).
    Stored in workout_logs.video_source.
    Needed to render the correct player (embedded link vs internal upload).
    """

    EXTERNAL_LINK = "external_link"
    UPLOAD = "upload"
