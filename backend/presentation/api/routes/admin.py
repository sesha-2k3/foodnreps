"""
Admin routes — presentation/api/routes/admin.py
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.super_admin_service import SuperAdminService
from core.exceptions import ForbiddenError, NotFoundError
from domain.entities.enums import StaffRole, UserRole
from domain.entities.user import User
from infrastructure.repositories.assignment_repository import (
    ClientStaffAssignmentRepository,
)
from infrastructure.repositories.diet_repository import (
    DietEntryRepository,
    DietPlanRepository,
)
from infrastructure.repositories.workout_repository import (
    ProgramDayRepository,
    ProgramWeekRepository,
    WorkoutLogRepository,
    WorkoutPrescriptionRepository,
    WorkoutProgramRepository,
)
from presentation.api.dependencies import (
    get_assignment_service,
    get_db,
    get_super_admin_service,
    get_user_repo,
)
from presentation.api.schemas.admin_schema import (
    AssignStaffRequest,
    AssignmentResponse,
    ClientAssignmentsResponse,
    CreateUserRequest,
    EndAssignmentRequest,
    OverrideReasonRequest,
    UserListResponse,
    UserResponse,
)
from presentation.middleware.auth_guard import get_current_user

router = APIRouter()


# ── Role guard ────────────────────────────────────────────────────────────────


async def require_super_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise ForbiddenError("Super admin access required.")
    return current_user


# ── User management ───────────────────────────────────────────────────────────


@router.get("/users", response_model=UserListResponse)
async def list_users(
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_super_admin),
    user_repo=Depends(get_user_repo),
) -> UserListResponse:
    users, total = await user_repo.list_all(
        role=role, is_active=is_active, limit=limit, offset=offset
    )
    return UserListResponse(
        users=[UserResponse.model_validate(u, from_attributes=True) for u in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    body: CreateUserRequest,
    admin: User = Depends(require_super_admin),
    svc: SuperAdminService = Depends(get_super_admin_service),
) -> UserResponse:
    user = await svc.create_user(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        role=body.role,
    )
    return UserResponse.model_validate(user, from_attributes=True)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    _admin: User = Depends(require_super_admin),
    user_repo=Depends(get_user_repo),
) -> UserResponse:
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return UserResponse.model_validate(user, from_attributes=True)


@router.post("/users/{user_id}/deactivate", status_code=204)
async def deactivate_user(
    user_id: UUID,
    _admin: User = Depends(require_super_admin),
    svc: SuperAdminService = Depends(get_super_admin_service),
) -> None:
    await svc.deactivate_user(user_id)


# ── Assignment management ─────────────────────────────────────────────────────


@router.get("/users/{client_id}/assignments", response_model=ClientAssignmentsResponse)
async def get_client_assignments(
    client_id: UUID,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> ClientAssignmentsResponse:
    repo = ClientStaffAssignmentRepository(session)
    active = await repo.get_active_for_client(client_id)
    by_role: dict[str, AssignmentResponse] = {
        a.staff_role: AssignmentResponse.model_validate(a, from_attributes=True)
        for a in active
    }
    return ClientAssignmentsResponse(
        fitness_trainer=by_role.get(StaffRole.FITNESS_TRAINER),
        nutritionist=by_role.get(StaffRole.NUTRITIONIST),
        master_coach=by_role.get(StaffRole.MASTER_COACH),
    )


@router.post(
    "/users/{client_id}/assignments", response_model=AssignmentResponse, status_code=201
)
async def assign_staff(
    client_id: UUID,
    body: AssignStaffRequest,
    admin: User = Depends(require_super_admin),
    assignment_svc=Depends(get_assignment_service),
) -> AssignmentResponse:
    assignment = await assignment_svc.assign_staff(
        client_id=client_id,
        staff_id=body.staff_id,
        staff_role=StaffRole(body.staff_role),
        assigned_by=admin.id,
    )
    return AssignmentResponse.model_validate(assignment, from_attributes=True)


@router.delete("/assignments/{assignment_id}", status_code=204)
async def end_assignment(
    assignment_id: UUID,
    body: EndAssignmentRequest,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    repo = ClientStaffAssignmentRepository(session)
    await repo.end_assignment(
        assignment_id=assignment_id,
        ended_at=datetime.now(tz=timezone.utc),
        ended_reason=body.ended_reason,
    )


# ── Plan read ─────────────────────────────────────────────────────────────────


@router.get("/clients/{client_id}/workout")
async def get_client_workout(
    client_id: UUID,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from presentation.api.schemas.workout_schema import (
        ProgramDayResponse,
        ProgramWeekResponse,
        WorkoutProgramResponse,
    )

    prog_repo = WorkoutProgramRepository(session)
    week_repo = ProgramWeekRepository(session)
    day_repo = ProgramDayRepository(session)
    pres_repo = WorkoutPrescriptionRepository(session)
    log_repo = WorkoutLogRepository(session)

    program = await prog_repo.get_active_assigned_by_owner(client_id)
    if program is None:
        raise NotFoundError(f"No active programme for client {client_id}")

    weeks = await week_repo.list_by_program(program.id)
    week_responses = []
    for week in weeks:
        days = await day_repo.list_by_week(week.id)
        day_responses = []
        for day in days:
            prescriptions = await pres_repo.list_by_day(day.id)
            logs_by_pres = {
                p.id: await log_repo.list_by_prescription(p.id) for p in prescriptions
            }
            day_responses.append(
                ProgramDayResponse.from_entities(day, prescriptions, logs_by_pres)
            )
        week_responses.append(ProgramWeekResponse.from_entities(week, day_responses))

    return WorkoutProgramResponse.from_entity(program, week_responses).model_dump()


@router.get("/clients/{client_id}/diet")
async def get_client_diet(
    client_id: UUID,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    from presentation.api.schemas.diet_schema import DietPlanResponse

    plan_repo = DietPlanRepository(session)
    entry_repo = DietEntryRepository(session)

    plan = await plan_repo.get_active_by_owner(client_id)
    if plan is None:
        raise NotFoundError(f"No active diet plan for client {client_id}")

    entries = await entry_repo.list_by_plan(plan.id)
    return DietPlanResponse.from_entities(plan, entries).model_dump()


# ── Plan override ─────────────────────────────────────────────────────────────


@router.post("/clients/{client_id}/workout/override")
async def override_workout(
    client_id: UUID,
    body: OverrideReasonRequest,
    admin: User = Depends(require_super_admin),
    svc: SuperAdminService = Depends(get_super_admin_service),
    session: AsyncSession = Depends(get_db),
) -> dict:
    program = await WorkoutProgramRepository(session).get_active_assigned_by_owner(
        client_id
    )
    if program is None:
        raise NotFoundError(f"No active programme for client {client_id}")
    saved = await svc.override_workout_programme(
        program_id=program.id,
        override_reason=body.override_reason,
        admin_id=admin.id,
    )
    return {"id": str(saved.id), "override_reason": saved.override_reason}
