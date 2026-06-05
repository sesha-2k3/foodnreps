"""
Domain entities public interface.

Consumers import from here, not from individual entity modules:

    from domain.entities import User, UserRole, WorkoutProgram, DietPlan

This hides the internal file organisation — if a class moves to a different
module, only this __init__.py changes, not every import across the codebase.
"""

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
from domain.entities.plan import PlanActivityLog, PlanComment, PlanVersion
from domain.entities.profile import BodyMetric, IntakeProfile
from domain.entities.user import RefreshToken, User
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutLog,
    WorkoutPrescription,
    WorkoutProgram,
)

__all__ = [
    # Enums
    "UserRole",
    "StaffRole",
    "FitnessGoal",
    "ExperienceLevel",
    "PlanType",
    "ActivityAction",
    "VideoSource",
    # User
    "User",
    "RefreshToken",
    # Assignment
    "ClientStaffAssignment",
    # Profile
    "IntakeProfile",
    "BodyMetric",
    # Workout
    "WorkoutProgram",
    "ProgramWeek",
    "ProgramDay",
    "WorkoutPrescription",
    "WorkoutLog",
    # Diet
    "DietPlan",
    "DietEntry",
    # Plan cross-cutting
    "PlanVersion",
    "PlanComment",
    "PlanActivityLog",
]
