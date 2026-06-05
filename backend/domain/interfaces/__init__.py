"""
Domain interfaces public exports.

Repository interfaces — implemented by infrastructure/repositories/.
Service interfaces   — implemented by application/services/.
"""

from domain.interfaces.repositories import (
    IBodyMetricRepository,
    IClientStaffAssignmentRepository,
    IDietEntryRepository,
    IDietPlanRepository,
    IIntakeProfileRepository,
    IPlanActivityLogRepository,
    IPlanCommentRepository,
    IPlanVersionRepository,
    IProgramDayRepository,
    IProgramWeekRepository,
    IRefreshTokenRepository,
    IUserRepository,
    IWorkoutLogRepository,
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)
from domain.interfaces.services import (
    IAssignmentService,
    IAuthService,
    IClientService,
    IDietService,
    IPersonalPlanService,
    ISuperAdminService,
    IWorkoutService,
)

__all__ = [
    # Repositories
    "IUserRepository",
    "IRefreshTokenRepository",
    "IClientStaffAssignmentRepository",
    "IIntakeProfileRepository",
    "IBodyMetricRepository",
    "IWorkoutProgramRepository",
    "IProgramWeekRepository",
    "IProgramDayRepository",
    "IWorkoutPrescriptionRepository",
    "IWorkoutLogRepository",
    "IDietPlanRepository",
    "IDietEntryRepository",
    "IPlanVersionRepository",
    "IPlanCommentRepository",
    "IPlanActivityLogRepository",
    # Services
    "IAuthService",
    "IAssignmentService",
    "IPersonalPlanService",
    "IClientService",
    "IWorkoutService",
    "IDietService",
    "ISuperAdminService",
]
