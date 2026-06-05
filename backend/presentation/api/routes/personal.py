"""
Personal plan routes — available to every authenticated role.

The guard is Depends(get_current_user) with no role restriction.
A client in orphan mode, a fitness trainer managing their own training,
a super admin — all use these routes identically.

PersonalPlanService is role-agnostic: it only checks that owner_id matches
the current user's id, preventing a user from managing another user's
personal plans.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from application.services.personal_plan_service import PersonalPlanService
from infrastructure.repositories.diet_repository import DietEntryRepository
from infrastructure.repositories.workout_repository import (
    ProgramDayRepository,
    ProgramWeekRepository,
    WorkoutPrescriptionRepository,
)
from presentation.api.dependencies import (
    get_day_repo,
    get_entry_repo,
    get_personal_plan_service,
    get_prescription_repo,
    get_week_repo,
)
from presentation.api.schemas.diet_schema import (
    CreateDietPlanRequest,
    DietPlanResponse,
)
from presentation.api.schemas.workout_schema import (
    AddDayRequest,
    AddWeekRequest,
    CreateProgrammeRequest,
    ProgramDayResponse,
    ProgramWeekResponse,
    WorkoutProgramResponse,
)
from presentation.middleware.auth_guard import CurrentUser, get_current_user

router = APIRouter()


# ── Personal workout ───────────────────────────────────────────────────────────


@router.get(
    "/workout",
    response_model=WorkoutProgramResponse,
    summary="Get your personal workout programme",
)
async def get_personal_workout(
    current_user: CurrentUser = Depends(get_current_user),
    service: PersonalPlanService = Depends(get_personal_plan_service),
    week_repo: ProgramWeekRepository = Depends(get_week_repo),
    day_repo: ProgramDayRepository = Depends(get_day_repo),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
) -> WorkoutProgramResponse:
    program = await service.get_personal_workout(current_user.id)
    if program is None:
        raise HTTPException(
            404,
            detail="No personal workout programme found. POST /personal/workout to create one.",
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
    "/workout",
    response_model=WorkoutProgramResponse,
    status_code=201,
    summary="Create a personal workout programme",
)
async def create_personal_workout(
    body: CreateProgrammeRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PersonalPlanService = Depends(get_personal_plan_service),
) -> WorkoutProgramResponse:
    program = await service.create_personal_workout(
        owner_id=current_user.id,
        name=body.name,
        coach_notes=body.coach_notes,
    )
    return WorkoutProgramResponse.from_entity(program)


@router.post(
    "/workout/{program_id}/weeks",
    response_model=dict,
    status_code=201,
    summary="Add a week to your personal workout programme",
)
async def add_week_to_personal_workout(
    program_id: UUID,
    body: AddWeekRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PersonalPlanService = Depends(get_personal_plan_service),
) -> dict:
    week = await service.add_week_to_personal_workout(
        owner_id=current_user.id,
        program_id=program_id,
        week_number=body.week_number,
        label=body.label,
        notes=body.notes,
    )
    return {"id": str(week.id), "week_number": week.week_number, "label": week.label}


@router.post(
    "/workout/weeks/{week_id}/days",
    response_model=dict,
    status_code=201,
    summary="Add a training day to a week in your personal programme",
)
async def add_day_to_personal_workout(
    week_id: UUID,
    body: AddDayRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PersonalPlanService = Depends(get_personal_plan_service),
) -> dict:
    day = await service.add_day_to_week(
        week_id=week_id,
        day_number=body.day_number,
        label=body.label,
        notes=body.notes,
    )
    return {"id": str(day.id), "day_number": day.day_number, "label": day.label}


# ── Personal diet ─────────────────────────────────────────────────────────────


@router.get(
    "/diet",
    response_model=DietPlanResponse,
    summary="Get your personal diet plan",
)
async def get_personal_diet(
    current_user: CurrentUser = Depends(get_current_user),
    service: PersonalPlanService = Depends(get_personal_plan_service),
    entry_repo: DietEntryRepository = Depends(get_entry_repo),
) -> DietPlanResponse:
    plan = await service.get_personal_diet(current_user.id)
    if plan is None:
        raise HTTPException(
            404,
            detail="No personal diet plan found. POST /personal/diet to create one.",
        )
    entries = await entry_repo.list_by_plan(plan.id)
    return DietPlanResponse.from_entity(plan, entries)


@router.post(
    "/diet",
    response_model=DietPlanResponse,
    status_code=201,
    summary="Create a personal diet plan",
)
async def create_personal_diet(
    body: CreateDietPlanRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: PersonalPlanService = Depends(get_personal_plan_service),
) -> DietPlanResponse:
    plan = await service.create_personal_diet(
        owner_id=current_user.id,
        name=body.name,
        coach_notes=body.coach_notes,
    )
    return DietPlanResponse.from_entity(plan)
