"""
Admin routes — presentation/api/routes/admin.py

Only the override endpoint changed from the previous version.
Everything else (user management, assignments, plan read) is unchanged.
"""

"""
Admin routes — presentation/api/routes/admin.py

Sprint 9 override: adds full workout programme CRUD endpoints so the
super admin can add/remove weeks, days, and prescriptions for any client.

These endpoints mirror the trainer/coach endpoints exactly but:
  - Require super_admin role (not staff assignment)
  - Skip every assignment ownership check
  - Use WorkoutFactory + repos directly (no service assignment guard)
"""

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.factories.workout_factory import WorkoutFactory
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
    get_workout_factory,
)
from presentation.api.schemas.admin_schema import (
    AssignmentResponse,
    AssignStaffRequest,
    ClientAssignmentsResponse,
    CreateUserRequest,
    EndAssignmentRequest,
    OverrideWorkoutRequest,
    UserListResponse,
    UserResponse,
)
from presentation.api.schemas.workout_schema import (
    AddDayRequest,
    AddPrescriptionRequest,
    AddWeekRequest,
    CreateProgrammeRequest,
    ProgramDayResponse,
    ProgramWeekResponse,
    UpdatePrescriptionRequest,
    WorkoutPrescriptionResponse,
    WorkoutProgramResponse,
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


# ── Plan override (reason + optional field patches) ───────────────────────────


@router.post("/clients/{client_id}/workout/override")
async def override_workout(
    client_id: UUID,
    body: OverrideWorkoutRequest,
    admin: User = Depends(require_super_admin),
    svc: SuperAdminService = Depends(get_super_admin_service),
    session: AsyncSession = Depends(get_db),
) -> dict:
    program = await WorkoutProgramRepository(session).get_active_assigned_by_owner(
        client_id
    )
    if program is None:
        raise NotFoundError(f"No active programme for client {client_id}")

    changes_as_dicts = [patch.model_dump(exclude_none=True) for patch in body.changes]

    saved = await svc.override_workout_programme(
        program_id=program.id,
        override_reason=body.override_reason,
        admin_id=admin.id,
        changes=changes_as_dicts,
    )
    return {
        "id": str(saved.id),
        "override_reason": saved.override_reason,
        "changes_applied": len(body.changes),
    }


# ── Programme builder CRUD ────────────────────────────────────────────────────
# These mirror the trainer/coach endpoints exactly but bypass assignment checks.
# The URL pattern /admin/clients/:id/workout/... is what useProgrammeMutations
# builds when rolePrefix === "admin".


@router.post("/clients/{client_id}/workout", response_model=dict, status_code=201)
async def create_programme(
    client_id: UUID,
    body: CreateProgrammeRequest,
    admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
    factory: WorkoutFactory = Depends(get_workout_factory),
) -> dict:
    repo = WorkoutProgramRepository(session)
    program = factory.create_programme(
        owner_id=client_id,
        created_by_id=admin.id,
        name=body.name,
        is_personal=False,
    )
    saved = await repo.save(program)
    return WorkoutProgramResponse.from_entity(saved, []).model_dump()


@router.post("/clients/{client_id}/workout/weeks", status_code=201)
async def add_week(
    client_id: UUID,
    body: AddWeekRequest,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
    factory: WorkoutFactory = Depends(get_workout_factory),
) -> dict:
    prog_repo = WorkoutProgramRepository(session)
    week_repo = ProgramWeekRepository(session)

    program = await prog_repo.get_active_assigned_by_owner(client_id)
    if program is None:
        raise NotFoundError(f"No active programme for client {client_id}")

    week = factory.create_week(
        program_id=program.id,
        week_number=body.week_number,
        label=body.label,
        notes=body.notes,
    )
    saved = await week_repo.save(week)
    return ProgramWeekResponse.from_entities(saved, []).model_dump()


@router.post("/clients/{client_id}/workout/weeks/{week_id}/days", status_code=201)
async def add_day(
    client_id: UUID,
    week_id: UUID,
    body: AddDayRequest,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
    factory: WorkoutFactory = Depends(get_workout_factory),
) -> dict:
    day_repo = ProgramDayRepository(session)
    day = factory.create_day(
        week_id=week_id,
        day_number=body.day_number,
        label=body.label,
        notes=body.notes,
    )
    saved = await day_repo.save(day)
    return ProgramDayResponse.from_entities(saved, [], {}).model_dump()


@router.post(
    "/clients/{client_id}/workout/days/{day_id}/prescriptions", status_code=201
)
async def add_prescription(
    client_id: UUID,
    day_id: UUID,
    body: AddPrescriptionRequest,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
    factory: WorkoutFactory = Depends(get_workout_factory),
) -> dict:
    repo = WorkoutPrescriptionRepository(session)
    prescription = factory.create_prescription(
        day_id=day_id,
        order_index=body.order_index,
        exercise_name=body.exercise_name,
        warmup_sets=body.warmup_sets,
        working_sets=body.working_sets,
        reps_min=body.reps_min,
        reps_max=body.reps_max,
        reps_note=body.reps_note,
        prescribed_load_kg=body.prescribed_load_kg,
        prescribed_load_text=body.prescribed_load_text,
        prescribed_rpe=body.prescribed_rpe,
        prescribed_rir=body.prescribed_rir,
        rest_seconds=body.rest_seconds,
        instructions=body.instructions,
    )
    saved = await repo.save(prescription)
    return WorkoutPrescriptionResponse.from_entity(saved, []).model_dump()


@router.patch("/clients/{client_id}/workout/prescriptions/{prescription_id}")
async def update_prescription(
    client_id: UUID,
    prescription_id: UUID,
    body: UpdatePrescriptionRequest,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    repo = WorkoutPrescriptionRepository(session)
    prescription = await repo.get_by_id(prescription_id)
    if prescription is None:
        raise NotFoundError(f"Prescription {prescription_id} not found")

    patch = {
        "updated_at": datetime.now(tz=timezone.utc),
        **body.model_dump(exclude_none=True),
    }
    saved = await repo.save(replace(prescription, **patch))
    return WorkoutPrescriptionResponse.from_entity(saved, []).model_dump()


@router.delete(
    "/clients/{client_id}/workout/prescriptions/{prescription_id}", status_code=204
)
async def delete_prescription(
    client_id: UUID,
    prescription_id: UUID,
    _admin: User = Depends(require_super_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    repo = WorkoutPrescriptionRepository(session)
    await repo.delete(prescription_id)
