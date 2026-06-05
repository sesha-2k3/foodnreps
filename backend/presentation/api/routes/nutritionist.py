"""
Nutritionist routes.

Nutritionists write diet plans and read workout programmes (read-only).
Structural mirror of trainer.py — the same patterns apply, with diet and
workout domains swapped.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from application.services.nutritionist_service import NutritionistService
from domain.entities.enums import UserRole
from infrastructure.repositories.diet_repository import DietEntryRepository
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.workout_repository import (
    ProgramDayRepository,
    ProgramWeekRepository,
    WorkoutPrescriptionRepository,
)
from presentation.api.dependencies import (
    get_day_repo,
    get_entry_repo,
    get_nutritionist_service,
    get_prescription_repo,
    get_user_repo,
    get_week_repo,
)
from presentation.api.schemas.diet_schema import (
    AddDietEntryRequest,
    CreateDietPlanRequest,
    DietPlanResponse,
)
from presentation.api.schemas.user_schema import UserResponse
from presentation.api.schemas.workout_schema import (
    ProgramDayResponse,
    ProgramWeekResponse,
    WorkoutProgramResponse,
)
from presentation.middleware.auth_guard import CurrentUser, require_role

router = APIRouter()

_require_nutritionist = Depends(require_role(UserRole.NUTRITIONIST))


@router.get(
    "/clients", response_model=list[UserResponse], summary="List assigned clients"
)
async def list_clients(
    current_user: CurrentUser = _require_nutritionist,
    service: NutritionistService = Depends(get_nutritionist_service),
    user_repo: UserRepository = Depends(get_user_repo),
) -> list[UserResponse]:
    client_ids = await service.list_assigned_clients(current_user.id)
    users = [await user_repo.get_by_id(cid) for cid in client_ids]
    return [UserResponse.from_entity(u) for u in users if u is not None]


@router.get(
    "/clients/{client_id}/diet",
    response_model=DietPlanResponse,
    summary="Get a client's active diet plan",
)
async def get_client_diet(
    client_id: UUID,
    current_user: CurrentUser = _require_nutritionist,
    service: NutritionistService = Depends(get_nutritionist_service),
    entry_repo: DietEntryRepository = Depends(get_entry_repo),
) -> DietPlanResponse:
    plan = await service.get_client_diet_plan(current_user.id, client_id)
    if plan is None:
        raise HTTPException(404, detail=f"No active diet plan for client {client_id}")
    entries = await entry_repo.list_by_plan(plan.id)
    return DietPlanResponse.from_entity(plan, entries)


@router.post(
    "/clients/{client_id}/diet",
    response_model=DietPlanResponse,
    status_code=201,
    summary="Create a new diet plan for a client",
)
async def create_client_diet(
    client_id: UUID,
    body: CreateDietPlanRequest,
    current_user: CurrentUser = _require_nutritionist,
    service: NutritionistService = Depends(get_nutritionist_service),
) -> DietPlanResponse:
    plan = await service.create_plan_for_client(
        nutritionist_id=current_user.id,
        client_id=client_id,
        name=body.name,
        coach_notes=body.coach_notes,
    )
    return DietPlanResponse.from_entity(plan)


@router.post(
    "/clients/{client_id}/diet/entries",
    response_model=dict,
    status_code=201,
    summary="Add a food entry to a client's diet plan",
)
async def add_entry(
    client_id: UUID,
    body: AddDietEntryRequest,
    current_user: CurrentUser = _require_nutritionist,
    service: NutritionistService = Depends(get_nutritionist_service),
) -> dict:
    entry = await service.add_entry(
        nutritionist_id=current_user.id,
        client_id=client_id,
        food_name=body.food_name,
        calories=body.calories,
        protein_g=body.protein_g,
        fat_g=body.fat_g,
        carbs_g=body.carbs_g,
        order_index=body.order_index,
    )
    return {"id": str(entry.id), "food_name": entry.food_name}


@router.delete(
    "/clients/{client_id}/diet/entries/{entry_id}",
    status_code=204,
    summary="Remove a food entry from a client's diet plan",
)
async def delete_entry(
    client_id: UUID,
    entry_id: UUID,
    current_user: CurrentUser = _require_nutritionist,
    service: NutritionistService = Depends(get_nutritionist_service),
) -> None:
    await service.delete_entry(
        nutritionist_id=current_user.id,
        client_id=client_id,
        entry_id=entry_id,
    )


@router.get(
    "/clients/{client_id}/workout",
    response_model=WorkoutProgramResponse,
    summary="Read a client's workout programme (read-only cross-domain view)",
)
async def get_client_workout(
    client_id: UUID,
    current_user: CurrentUser = _require_nutritionist,
    service: NutritionistService = Depends(get_nutritionist_service),
    week_repo: ProgramWeekRepository = Depends(get_week_repo),
    day_repo: ProgramDayRepository = Depends(get_day_repo),
    prescription_repo: WorkoutPrescriptionRepository = Depends(get_prescription_repo),
) -> WorkoutProgramResponse:
    program = await service.get_client_workout_programme(current_user.id, client_id)
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
