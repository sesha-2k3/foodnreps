"""
FastAPI dependency injection wiring.

Every service and repository is assembled here via Depends(). Nothing in
this file contains business logic — it is purely a wiring file.

Design choice — one get_db that wraps get_session:
    get_session() in infrastructure/db/session.py is the actual async generator
    (commit/rollback on success/failure). We import and re-expose it here as
    get_db so that route handlers have a single consistent import point for
    their session dependency, and so that the infrastructure layer's function
    name can change without touching route files.

Design choice — factories as simple callables, not yielded:
    WorkoutFactory and DietFactory are stateless. Their dependency functions
    return a new instance per request. This is slightly less efficient than
    a module-level singleton but keeps the dependency graph uniform and makes
    every dependency replaceable via app.dependency_overrides in tests.

Design choice — all repos share the same session per request:
    FastAPI caches Depends() results within a request. Every repository that
    depends on get_db receives the SAME AsyncSession instance. All repository
    writes in one request are in one transaction — committed together on
    success, rolled back together on exception.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.factories.diet_factory import DietFactory
from application.factories.workout_factory import WorkoutFactory
from application.services.assignment_service import AssignmentService
from application.services.auth_service import AuthService
from application.services.client_service import ClientService
from application.services.fitness_trainer_service import FitnessTrainerService
from application.services.invite_service import InviteService
from application.services.master_coach_service import MasterCoachService
from application.services.nutritionist_service import NutritionistService
from application.services.personal_plan_service import PersonalPlanService
from application.services.super_admin_service import SuperAdminService
from infrastructure.db.session import get_session
from infrastructure.repositories.assignment_repository import (
    ClientStaffAssignmentRepository,
)
from infrastructure.repositories.diet_repository import (
    DietEntryRepository,
    DietPlanRepository,
)
from infrastructure.repositories.invite_repository import CoachingInviteRepository
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

# ── Session ───────────────────────────────────────────────────────────────────


def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:  # noqa: B008
    """
    Re-export of get_session under a stable presentation-layer name.
    Route files import from here, not from infrastructure.db.session directly.
    FastAPI unwraps the async generator from get_session automatically;
    get_db receives the already-yielded AsyncSession and simply returns it.
    """
    return session


# ── Repositories ──────────────────────────────────────────────────────────────


def get_user_repo(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(session)


def get_token_repo(session: AsyncSession = Depends(get_db)) -> RefreshTokenRepository:
    return RefreshTokenRepository(session)


def get_assignment_repo(
    session: AsyncSession = Depends(get_db),
) -> ClientStaffAssignmentRepository:
    return ClientStaffAssignmentRepository(session)


def get_workout_repo(
    session: AsyncSession = Depends(get_db),
) -> WorkoutProgramRepository:
    return WorkoutProgramRepository(session)


def get_week_repo(session: AsyncSession = Depends(get_db)) -> ProgramWeekRepository:
    return ProgramWeekRepository(session)


def get_day_repo(session: AsyncSession = Depends(get_db)) -> ProgramDayRepository:
    return ProgramDayRepository(session)


def get_prescription_repo(
    session: AsyncSession = Depends(get_db),
) -> WorkoutPrescriptionRepository:
    return WorkoutPrescriptionRepository(session)


def get_log_repo(session: AsyncSession = Depends(get_db)) -> WorkoutLogRepository:
    return WorkoutLogRepository(session)


def get_diet_repo(session: AsyncSession = Depends(get_db)) -> DietPlanRepository:
    return DietPlanRepository(session)


def get_entry_repo(session: AsyncSession = Depends(get_db)) -> DietEntryRepository:
    return DietEntryRepository(session)


def get_plan_version_repo(
    session: AsyncSession = Depends(get_db),
) -> PlanVersionRepository:
    return PlanVersionRepository(session)


def get_plan_comment_repo(
    session: AsyncSession = Depends(get_db),
) -> PlanCommentRepository:
    return PlanCommentRepository(session)


def get_activity_log_repo(
    session: AsyncSession = Depends(get_db),
) -> PlanActivityLogRepository:
    return PlanActivityLogRepository(session)


def get_intake_profile_repo(
    session: AsyncSession = Depends(get_db),
) -> IntakeProfileRepository:
    return IntakeProfileRepository(session)


def get_body_metric_repo(
    session: AsyncSession = Depends(get_db),
) -> BodyMetricRepository:
    return BodyMetricRepository(session)


# ── Factories ─────────────────────────────────────────────────────────────────


def get_workout_factory() -> WorkoutFactory:
    return WorkoutFactory()


def get_diet_factory() -> DietFactory:
    return DietFactory()


# ── Services ──────────────────────────────────────────────────────────────────


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    token_repo: RefreshTokenRepository = Depends(get_token_repo),
) -> AuthService:
    return AuthService(user_repo=user_repo, token_repo=token_repo)


def get_assignment_service(
    assignment_repo: ClientStaffAssignmentRepository = Depends(get_assignment_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> AssignmentService:
    return AssignmentService(assignment_repo=assignment_repo, user_repo=user_repo)


def get_personal_plan_service(
    workout_repo: WorkoutProgramRepository = Depends(get_workout_repo),
    diet_repo: DietPlanRepository = Depends(get_diet_repo),
    week_repo: ProgramWeekRepository = Depends(get_week_repo),
    day_repo: ProgramDayRepository = Depends(get_day_repo),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
    activity_log_repo: PlanActivityLogRepository = Depends(get_activity_log_repo),
    workout_factory: WorkoutFactory = Depends(get_workout_factory),
    diet_factory: DietFactory = Depends(get_diet_factory),
) -> PersonalPlanService:
    return PersonalPlanService(
        workout_repo=workout_repo,
        diet_repo=diet_repo,
        week_repo=week_repo,
        day_repo=day_repo,
        prescription_repo=prescription_repo,
        activity_log_repo=activity_log_repo,
        workout_factory=workout_factory,
        diet_factory=diet_factory,
    )


def get_client_service(
    workout_repo: WorkoutProgramRepository = Depends(get_workout_repo),
    diet_repo: DietPlanRepository = Depends(get_diet_repo),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
    log_repo: WorkoutLogRepository = Depends(get_log_repo),
    activity_log_repo: PlanActivityLogRepository = Depends(get_activity_log_repo),
) -> ClientService:
    return ClientService(
        workout_repo=workout_repo,
        diet_repo=diet_repo,
        prescription_repo=prescription_repo,
        log_repo=log_repo,
        activity_log_repo=activity_log_repo,
    )


def get_trainer_service(
    assignment_repo: ClientStaffAssignmentRepository = Depends(get_assignment_repo),
    workout_repo: WorkoutProgramRepository = Depends(get_workout_repo),
    week_repo: ProgramWeekRepository = Depends(get_week_repo),
    day_repo: ProgramDayRepository = Depends(get_day_repo),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
    diet_repo: DietPlanRepository = Depends(get_diet_repo),
    activity_log_repo: PlanActivityLogRepository = Depends(get_activity_log_repo),
    workout_factory: WorkoutFactory = Depends(get_workout_factory),
) -> FitnessTrainerService:
    return FitnessTrainerService(
        assignment_repo=assignment_repo,
        workout_repo=workout_repo,
        week_repo=week_repo,
        day_repo=day_repo,
        prescription_repo=prescription_repo,
        diet_repo=diet_repo,
        activity_log_repo=activity_log_repo,
        workout_factory=workout_factory,
    )


def get_nutritionist_service(
    assignment_repo: ClientStaffAssignmentRepository = Depends(get_assignment_repo),
    diet_repo: DietPlanRepository = Depends(get_diet_repo),
    entry_repo: DietEntryRepository = Depends(get_entry_repo),
    workout_repo: WorkoutProgramRepository = Depends(get_workout_repo),
    activity_log_repo: PlanActivityLogRepository = Depends(get_activity_log_repo),
    diet_factory: DietFactory = Depends(get_diet_factory),
) -> NutritionistService:
    return NutritionistService(
        assignment_repo=assignment_repo,
        diet_repo=diet_repo,
        entry_repo=entry_repo,
        workout_repo=workout_repo,
        activity_log_repo=activity_log_repo,
        diet_factory=diet_factory,
    )


def get_coach_service(
    assignment_repo: ClientStaffAssignmentRepository = Depends(get_assignment_repo),
    workout_repo: WorkoutProgramRepository = Depends(get_workout_repo),
    week_repo: ProgramWeekRepository = Depends(get_week_repo),
    day_repo: ProgramDayRepository = Depends(get_day_repo),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
    diet_repo: DietPlanRepository = Depends(get_diet_repo),
    entry_repo: DietEntryRepository = Depends(get_entry_repo),
    activity_log_repo: PlanActivityLogRepository = Depends(get_activity_log_repo),
    workout_factory: WorkoutFactory = Depends(get_workout_factory),
    diet_factory: DietFactory = Depends(get_diet_factory),
) -> MasterCoachService:
    return MasterCoachService(
        assignment_repo=assignment_repo,
        workout_repo=workout_repo,
        week_repo=week_repo,
        day_repo=day_repo,
        prescription_repo=prescription_repo,
        diet_repo=diet_repo,
        entry_repo=entry_repo,
        activity_log_repo=activity_log_repo,
        workout_factory=workout_factory,
        diet_factory=diet_factory,
    )


def get_super_admin_service(
    user_repo: UserRepository = Depends(get_user_repo),
    token_repo: RefreshTokenRepository = Depends(get_token_repo),
    workout_repo: WorkoutProgramRepository = Depends(get_workout_repo),
    diet_repo: DietPlanRepository = Depends(get_diet_repo),
    plan_version_repo: PlanVersionRepository = Depends(get_plan_version_repo),
    activity_log_repo: PlanActivityLogRepository = Depends(get_activity_log_repo),
    assignment_service: AssignmentService = Depends(get_assignment_service),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
) -> SuperAdminService:
    return SuperAdminService(
        user_repo=user_repo,
        token_repo=token_repo,
        workout_repo=workout_repo,
        diet_repo=diet_repo,
        plan_version_repo=plan_version_repo,
        activity_log_repo=activity_log_repo,
        assignment_service=assignment_service,
        prescription_repo=prescription_repo,
    )


async def get_invite_service(
    session: AsyncSession = Depends(get_session),
) -> InviteService:
    return InviteService(
        invite_repo=CoachingInviteRepository(session),
        assignment_service=AssignmentService(
            assignment_repo=ClientStaffAssignmentRepository(session),
            user_repo=UserRepository(session),
        ),
        assignment_repo=ClientStaffAssignmentRepository(session),
        user_repo=UserRepository(session),
    )
