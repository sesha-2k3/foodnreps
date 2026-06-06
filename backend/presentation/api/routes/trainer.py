"""
Fitness trainer routes.

Trainers write workout programmes and read diet plans (read-only cross-domain).
The structural absence of any diet POST/DELETE route is the enforcement mechanism
— not a runtime role check inside shared handlers.

All mutations are gated by the trainer's active assignment to the client via
FitnessTrainerService._verify_trainer_for_client(), called internally.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from application.services.fitness_trainer_service import FitnessTrainerService
from domain.entities.enums import UserRole
from infrastructure.repositories.diet_repository import DietEntryRepository
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.workout_repository import (
    ProgramDayRepository,
    ProgramWeekRepository,
    WorkoutLogRepository,
    WorkoutPrescriptionRepository,
)
from presentation.api.dependencies import (
    get_day_repo,
    get_entry_repo,
    get_log_repo,
    get_prescription_repo,
    get_trainer_service,
    get_user_repo,
    get_week_repo,
)
from presentation.api.schemas.diet_schema import DietPlanResponse
from presentation.api.schemas.user_schema import UserResponse
from presentation.api.schemas.workout_schema import (
    AddDayRequest,
    AddPrescriptionRequest,
    AddWeekRequest,
    CreateProgrammeRequest,
    ProgramDayResponse,
    ProgramWeekResponse,
    WorkoutProgramResponse,
)
from presentation.middleware.auth_guard import CurrentUser, require_role

router = APIRouter()

_require_trainer = Depends(require_role(UserRole.FITNESS_TRAINER))


@router.get(
    "/clients", response_model=list[UserResponse], summary="List assigned clients"
)
async def list_clients(
    current_user: CurrentUser = _require_trainer,
    service: FitnessTrainerService = Depends(get_trainer_service),
    user_repo: UserRepository = Depends(get_user_repo),
) -> list[UserResponse]:
    client_ids = await service.list_assigned_clients(current_user.id)
    users = [await user_repo.get_by_id(cid) for cid in client_ids]
    return [UserResponse.from_entity(u) for u in users if u is not None]


@router.get(
    "/clients/{client_id}/workout",
    response_model=WorkoutProgramResponse,
    summary="Get a client's active workout programme",
)
async def get_client_workout(
    client_id: UUID,
    current_user: CurrentUser = _require_trainer,
    service: FitnessTrainerService = Depends(get_trainer_service),
    week_repo: ProgramWeekRepository = Depends(get_week_repo),
    day_repo: ProgramDayRepository = Depends(get_day_repo),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
    log_repo: WorkoutLogRepository = Depends(get_log_repo),
) -> WorkoutProgramResponse:
    program = await service.get_client_programme(current_user.id, client_id)
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


@router.post(
    "/clients/{client_id}/workout",
    response_model=WorkoutProgramResponse,
    status_code=201,
    summary="Create a new workout programme for a client",
)
async def create_client_workout(
    client_id: UUID,
    body: CreateProgrammeRequest,
    current_user: CurrentUser = _require_trainer,
    service: FitnessTrainerService = Depends(get_trainer_service),
) -> WorkoutProgramResponse:
    program = await service.create_programme_for_client(
        trainer_id=current_user.id,
        client_id=client_id,
        name=body.name,
        coach_notes=body.coach_notes,
    )
    return WorkoutProgramResponse.from_entity(program)


@router.post(
    "/clients/{client_id}/workout/weeks",
    response_model=dict,
    status_code=201,
    summary="Add a training week to a client's programme",
)
async def add_week(
    client_id: UUID,
    body: AddWeekRequest,
    current_user: CurrentUser = _require_trainer,
    service: FitnessTrainerService = Depends(get_trainer_service),
) -> dict:
    week = await service.add_week(
        trainer_id=current_user.id,
        client_id=client_id,
        week_number=body.week_number,
        label=body.label,
        notes=body.notes,
    )
    return {"id": str(week.id), "week_number": week.week_number, "label": week.label}


@router.post(
    "/clients/{client_id}/workout/weeks/{week_id}/days",
    response_model=dict,
    status_code=201,
    summary="Add a training day to a week",
)
async def add_day(
    client_id: UUID,
    week_id: UUID,
    body: AddDayRequest,
    current_user: CurrentUser = _require_trainer,
    service: FitnessTrainerService = Depends(get_trainer_service),
) -> dict:
    day = await service.add_day(
        trainer_id=current_user.id,
        client_id=client_id,
        week_id=week_id,
        day_number=body.day_number,
        label=body.label,
        notes=body.notes,
    )
    return {"id": str(day.id), "day_number": day.day_number, "label": day.label}


@router.post(
    "/clients/{client_id}/workout/days/{day_id}/prescriptions",
    response_model=dict,
    status_code=201,
    summary="Add an exercise prescription to a day (BLUE side)",
)
async def add_prescription(
    client_id: UUID,
    day_id: UUID,
    body: AddPrescriptionRequest,
    current_user: CurrentUser = _require_trainer,
    service: FitnessTrainerService = Depends(get_trainer_service),
) -> dict:
    rx = await service.add_prescription(
        trainer_id=current_user.id,
        client_id=client_id,
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
    return {
        "id": str(rx.id),
        "exercise_name": rx.exercise_name,
        "exercise_label": rx.exercise_label,
    }


@router.delete(
    "/clients/{client_id}/workout/prescriptions/{prescription_id}",
    status_code=204,
    summary="Remove a prescription from a client's programme",
)
async def delete_prescription(
    client_id: UUID,
    prescription_id: UUID,
    current_user: CurrentUser = _require_trainer,
    service: FitnessTrainerService = Depends(get_trainer_service),
) -> None:
    await service.delete_prescription(
        trainer_id=current_user.id,
        client_id=client_id,
        prescription_id=prescription_id,
    )


@router.get(
    "/clients/{client_id}/diet",
    response_model=DietPlanResponse,
    summary="Read a client's diet plan (read-only cross-domain view)",
)
async def get_client_diet(
    client_id: UUID,
    current_user: CurrentUser = _require_trainer,
    service: FitnessTrainerService = Depends(get_trainer_service),
    entry_repo: DietEntryRepository = Depends(get_entry_repo),
) -> DietPlanResponse:
    plan = await service.get_client_diet_plan(current_user.id, client_id)
    if plan is None:
        raise HTTPException(404, detail=f"No active diet plan for client {client_id}")
    entries = await entry_repo.list_by_plan(plan.id)
    return DietPlanResponse.from_entity(plan, entries)
