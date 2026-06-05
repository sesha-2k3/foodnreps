"""
Infrastructure repository public interface.

Import from here, not from individual repository modules:
    from infrastructure.repositories import UserRepository, WorkoutProgramRepository
"""

from infrastructure.repositories.assignment_repository import (
    ClientStaffAssignmentRepository,
)
from infrastructure.repositories.diet_repository import (
    DietEntryRepository,
    DietPlanRepository,
)
from infrastructure.repositories.plan_repository import (
    PlanActivityLogRepository,
    PlanCommentRepository,
    PlanVersionRepository,
)
from infrastructure.repositories.profile_repository import (
    BodyMetricRepository,
    IntakeProfileRepository,
)
from infrastructure.repositories.user_repository import (
    RefreshTokenRepository,
    UserRepository,
)
from infrastructure.repositories.workout_repository import (
    ProgramDayRepository,
    ProgramWeekRepository,
    WorkoutLogRepository,
    WorkoutPrescriptionRepository,
    WorkoutProgramRepository,
)

__all__ = [
    "UserRepository",
    "RefreshTokenRepository",
    "ClientStaffAssignmentRepository",
    "IntakeProfileRepository",
    "BodyMetricRepository",
    "WorkoutProgramRepository",
    "ProgramWeekRepository",
    "ProgramDayRepository",
    "WorkoutPrescriptionRepository",
    "WorkoutLogRepository",
    "DietPlanRepository",
    "DietEntryRepository",
    "PlanVersionRepository",
    "PlanCommentRepository",
    "PlanActivityLogRepository",
]
