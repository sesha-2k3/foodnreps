"""
Super admin routes — user lifecycle and plan overrides.

All routes require role=super_admin. Two conceptually distinct capabilities:

1. User management: create accounts, list users, deactivate, manage assignments.
2. Plan overrides: read any client's plan (bypassing assignment check) and apply
   an administrative override with a mandatory reason string.

Design choice — override view uses repos directly, bypassing service assignment check:
    FitnessTrainerService and MasterCoachService both check their assignment before
    any read. Super admin has no assignment — they bypass the check by calling the
    repo directly. This is not a layering violation: reading data for display is a
    presentation-layer orchestration concern, not business logic. The actual override
    write goes through SuperAdminService, which enforces the mandatory reason.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from application.services.super_admin_service import SuperAdminService
from domain.entities.enums import UserRole
from infrastructure.repositories.diet_repository import (
    DietEntryRepository,
    DietPlanRepository,
)
from infrastructure.repositories.workout_repository import (
    ProgramDayRepository,
    ProgramWeekRepository,
    WorkoutPrescriptionRepository,
    WorkoutProgramRepository,
)
from presentation.api.dependencies import (
    get_day_repo,
    get_diet_repo,
    get_entry_repo,
    get_prescription_repo,
    get_super_admin_service,
    get_week_repo,
    get_workout_repo,
)
from presentation.api.schemas.diet_schema import DietPlanResponse
from presentation.api.schemas.user_schema import (
    AssignmentResponse,
    AssignStaffRequest,
    CreateUserRequest,
    OverrideWorkoutRequest,
    PaginatedUsersResponse,
    UserResponse,
)
from presentation.api.schemas.workout_schema import (
    ProgramDayResponse,
    ProgramWeekResponse,
    WorkoutProgramResponse,
)
from presentation.middleware.auth_guard import CurrentUser, require_role

router = APIRouter()

_require_admin = Depends(require_role(UserRole.SUPER_ADMIN))


# ── User management ───────────────────────────────────────────────────────────


@router.get("/users", response_model=PaginatedUsersResponse, summary="List all clients")
async def list_clients(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = _require_admin,
    service: SuperAdminService = Depends(get_super_admin_service),
) -> PaginatedUsersResponse:
    clients = await service.list_clients(limit=limit, offset=offset)
    all_clients = await service._user_repo.list_clients()
    return PaginatedUsersResponse(
        data=[UserResponse.from_entity(u) for u in clients],
        total=len(all_clients),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/staff", response_model=list[UserResponse], summary="List all coaching staff"
)
async def list_staff(
    current_user: CurrentUser = _require_admin,
    service: SuperAdminService = Depends(get_super_admin_service),
) -> list[UserResponse]:
    staff = await service.list_staff()
    return [UserResponse.from_entity(u) for u in staff]


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    summary="Create a new user account",
)
async def create_user(
    body: CreateUserRequest,
    current_user: CurrentUser = _require_admin,
    service: SuperAdminService = Depends(get_super_admin_service),
) -> UserResponse:
    user = await service.create_user(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
    )
    return UserResponse.from_entity(user)


@router.get("/users/{user_id}", response_model=UserResponse, summary="Get a user by ID")
async def get_user(
    user_id: UUID,
    current_user: CurrentUser = _require_admin,
    service: SuperAdminService = Depends(get_super_admin_service),
) -> UserResponse:
    user = await service.get_user(user_id)
    return UserResponse.from_entity(user)


@router.post(
    "/users/{user_id}/deactivate",
    status_code=204,
    summary="Deactivate a user account and revoke all sessions",
)
async def deactivate_user(
    user_id: UUID,
    current_user: CurrentUser = _require_admin,
    service: SuperAdminService = Depends(get_super_admin_service),
) -> None:
    await service.deactivate_user(user_id)


# ── Assignment management ──────────────────────────────────────────────────────


@router.post(
    "/users/{client_id}/assignments",
    response_model=AssignmentResponse,
    status_code=201,
    summary="Assign a coaching staff member to a client",
)
async def assign_staff(
    client_id: UUID,
    body: AssignStaffRequest,
    current_user: CurrentUser = _require_admin,
    service: SuperAdminService = Depends(get_super_admin_service),
) -> AssignmentResponse:
    assignment = await service.assign_staff_to_client(
        client_id=client_id,
        staff_id=body.staff_id,
        staff_role=body.staff_role,
        admin_id=current_user.id,
    )
    return AssignmentResponse.from_entity(assignment)  # type: ignore[arg-type]


@router.delete(
    "/assignments/{assignment_id}",
    status_code=204,
    summary="End an active coaching assignment",
)
async def end_assignment(
    assignment_id: UUID,
    reason: str = Query(default="removed by admin"),
    current_user: CurrentUser = _require_admin,
    service: SuperAdminService = Depends(get_super_admin_service),
) -> None:
    await service.end_staff_assignment(
        assignment_id=assignment_id,
        reason=reason,
    )


# ── Override views ─────────────────────────────────────────────────────────────


@router.get(
    "/clients/{client_id}/workout",
    response_model=WorkoutProgramResponse,
    summary="Read any client's workout programme (admin override view)",
)
async def get_client_workout_override_view(
    client_id: UUID,
    current_user: CurrentUser = _require_admin,
    workout_repo: WorkoutProgramRepository = Depends(get_workout_repo),
    week_repo: ProgramWeekRepository = Depends(get_week_repo),
    day_repo: ProgramDayRepository = Depends(get_day_repo),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
) -> WorkoutProgramResponse:
    program = await workout_repo.get_active_by_owner(client_id)
    if program is None:
        raise HTTPException(
            404, detail=f"No active workout programme for client {client_id}"
        )
    weeks = await week_repo.list_by_program(program.id)
    week_responses = []
    for week in weeks:
        days = await day_repo.list_by_week(week.id)
        day_responses = []
        for day in days:
            prescriptions = await prescription_repo.list_by_day(day.id)
            day_responses.append(ProgramDayResponse.from_entities(day, prescriptions))
        week_responses.append(ProgramWeekResponse.from_entities(week, day_responses))
    return WorkoutProgramResponse.from_entity(program, week_responses)


@router.post(
    "/clients/{client_id}/workout/override",
    response_model=WorkoutProgramResponse,
    summary="Apply an administrative override to a client's workout programme",
)
async def override_workout(
    client_id: UUID,
    body: OverrideWorkoutRequest,
    current_user: CurrentUser = _require_admin,
    service: SuperAdminService = Depends(get_super_admin_service),
) -> WorkoutProgramResponse:
    """
    Record a super-admin override. Requires a non-empty reason string.
    Writes a PlanVersion snapshot and an OVERRIDE_APPLIED activity log entry.
    """
    program = await service.override_workout_programme(
        program_id=body.program_id,
        override_reason=body.override_reason,
        admin_id=current_user.id,
    )
    return WorkoutProgramResponse.from_entity(program)


@router.get(
    "/clients/{client_id}/diet",
    response_model=DietPlanResponse,
    summary="Read any client's diet plan (admin override view)",
)
async def get_client_diet_override_view(
    client_id: UUID,
    current_user: CurrentUser = _require_admin,
    diet_repo: DietPlanRepository = Depends(get_diet_repo),
    entry_repo: DietEntryRepository = Depends(get_entry_repo),
) -> DietPlanResponse:
    plan = await diet_repo.get_active_by_owner(client_id)
    if plan is None:
        raise HTTPException(404, detail=f"No active diet plan for client {client_id}")
    entries = await entry_repo.list_by_plan(plan.id)
    return DietPlanResponse.from_entity(plan, entries)
