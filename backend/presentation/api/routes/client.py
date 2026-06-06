"""
Client routes — reading assigned plans and logging workouts.

All routes require role=client. This is the most restrictive guard:
coaches do not use these routes even to check their own work. A fitness
trainer viewing their own training plan uses /personal/workout, not
/client/workout. This keeps role routing unambiguous.

Design choice — GET workout returns 404 when no programme is assigned:
    A client with no coach has no assigned programme. The route returns
    404 (not 200 with an empty body) because "no assigned programme" is
    a meaningful absence. The frontend uses 404 to redirect the client
    to their personal plan (orphan mode) rather than showing an empty screen.

Design choice — hierarchical response assembled in the route handler:
    The service returns a WorkoutProgram entity (top level only). The route
    handler fetches weeks → days → prescriptions via injected repo dependencies.
    This is read-only data assembly — no business logic. The N+1 pattern is
    a Phase 1 pragmatism noted in the architecture doc under P1.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from application.services.client_service import ClientService
from domain.entities.enums import UserRole
from infrastructure.repositories.diet_repository import DietEntryRepository
from infrastructure.repositories.workout_repository import (
    ProgramDayRepository,
    ProgramWeekRepository,
    WorkoutLogRepository,
    WorkoutPrescriptionRepository,
)
from presentation.api.dependencies import (
    get_client_service,
    get_day_repo,
    get_entry_repo,
    get_log_repo,
    get_prescription_repo,
    get_week_repo,
)
from presentation.api.schemas.diet_schema import DietPlanResponse
from presentation.api.schemas.workout_schema import (
    LogWorkoutRequest,
    ProgramDayResponse,
    ProgramWeekResponse,
    UpdateWorkoutLogRequest,
    WorkoutLogResponse,
    WorkoutProgramResponse,
)
from presentation.middleware.auth_guard import CurrentUser, require_role

router = APIRouter()

_require_client = Depends(require_role(UserRole.CLIENT))


# ── Workout plan ──────────────────────────────────────────────────────────────


@router.get(
    "/workout",
    response_model=WorkoutProgramResponse,
    summary="Get the assigned workout programme (full hierarchy)",
)
async def get_assigned_workout(
    current_user: CurrentUser = _require_client,
    service: ClientService = Depends(get_client_service),
    week_repo: ProgramWeekRepository = Depends(get_week_repo),
    day_repo: ProgramDayRepository = Depends(get_day_repo),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
    log_repo: WorkoutLogRepository = Depends(get_log_repo),  # ← add this
) -> WorkoutProgramResponse:
    program = await service.get_assigned_workout(current_user.id)
    if program is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No assigned workout programme found. "
                "If you are self-managing, use GET /personal/workout instead."
            ),
        )
    weeks = await week_repo.list_by_program(program.id)
    week_responses = []
    for week in weeks:
        days = await day_repo.list_by_week(week.id)
        day_responses = []
        for day in days:
            prescriptions = await prescription_repo.list_by_day(day.id)
            # Fetch logs per prescription and build lookup dict
            logs_by_prescription = {}
            for prescription in prescriptions:
                logs = await log_repo.list_by_prescription(prescription.id)
                logs_by_prescription[prescription.id] = logs
            day_responses.append(
                ProgramDayResponse.from_entities(
                    day, prescriptions, logs_by_prescription
                )
            )
        week_responses.append(ProgramWeekResponse.from_entities(week, day_responses))
    return WorkoutProgramResponse.from_entity(program, week_responses)


# ── Diet plan ─────────────────────────────────────────────────────────────────


@router.get(
    "/diet",
    response_model=DietPlanResponse,
    summary="Get the assigned diet plan with all food entries",
)
async def get_assigned_diet(
    current_user: CurrentUser = _require_client,
    service: ClientService = Depends(get_client_service),
    entry_repo: DietEntryRepository = Depends(get_entry_repo),
) -> DietPlanResponse:
    plan = await service.get_assigned_diet(current_user.id)
    if plan is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No assigned diet plan found. "
                "If you are self-managing, use GET /personal/diet instead."
            ),
        )
    entries = await entry_repo.list_by_plan(plan.id)
    return DietPlanResponse.from_entity(plan, entries)


# ── Workout log ───────────────────────────────────────────────────────────────


@router.post(
    "/workout-logs",
    response_model=WorkoutLogResponse,
    status_code=201,
    summary="Log actual workout performance (RED side of the spreadsheet)",
)
async def log_workout(
    body: LogWorkoutRequest,
    current_user: CurrentUser = _require_client,
    service: ClientService = Depends(get_client_service),
) -> WorkoutLogResponse:
    log = await service.log_workout(
        client_id=current_user.id,
        prescription_id=body.prescription_id,
        exercise_name=body.exercise_name,
        actual_sets=body.actual_sets,
        actual_reps=body.actual_reps,
        actual_load_kg=body.actual_load_kg,
        actual_rpe=body.actual_rpe,
        readiness=body.readiness,
        time_taken_seconds=body.time_taken_seconds,
        client_notes=body.client_notes,
        logged_at=body.logged_at,
    )
    return WorkoutLogResponse.from_entity(log)


@router.patch(
    "/workout-logs/{log_id}",
    response_model=WorkoutLogResponse,
    status_code=200,
    summary="Update an existing workout log entry",
)
async def update_workout_log(
    log_id: UUID,
    body: UpdateWorkoutLogRequest,
    current_user: CurrentUser = _require_client,
    service: ClientService = Depends(get_client_service),
) -> WorkoutLogResponse:
    log = await service.update_log(
        client_id=current_user.id,
        log_id=log_id,
        actual_sets=body.actual_sets,
        actual_reps=body.actual_reps,
        actual_load_kg=body.actual_load_kg,
        actual_rpe=body.actual_rpe,
        readiness=body.readiness,
        time_taken_seconds=body.time_taken_seconds,
        client_notes=body.client_notes,
        logged_at=body.logged_at,
    )
    return WorkoutLogResponse.from_entity(log)
