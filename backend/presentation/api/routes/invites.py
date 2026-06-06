"""
Invite routes.
Place at: presentation/api/routes/invites.py

Register in main.py:
    from presentation.api.routes.invites import router as invites_router
    app.include_router(invites_router, tags=["Invites"])

Add these to presentation/api/dependencies.py:
    from infrastructure.repositories.invite_repository import CoachingInviteRepository
    from application.services.invite_service import InviteService

    async def get_invite_service(session: AsyncSession = Depends(get_session)) -> InviteService:
        return InviteService(
            invite_repo=CoachingInviteRepository(session),
            assignment_service=AssignmentService(
                assignment_repo=ClientStaffAssignmentRepository(session),
                user_repo=UserRepository(session),
            ),
            assignment_repo=ClientStaffAssignmentRepository(session),
            user_repo=UserRepository(session),
        )
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from application.services.invite_service import InviteService
from core.exceptions import ForbiddenError
from domain.entities.enums import StaffRole, UserRole
from domain.entities.user import User
from presentation.api.dependencies import get_invite_service
from presentation.api.schemas.invite_schema import (
    ClientCoachesResponse,
    ConnectWithCoachRequest,
    InviteResponse,
)
from presentation.middleware.auth_guard import get_current_user

# from presentation.api.dependencies import get_invite_service  ← add this dep

router = APIRouter()


# ── Helper: assert role ───────────────────────────────────────────────────────


def _require_staff_role(user: User, expected: StaffRole) -> None:
    role_map = {
        StaffRole.FITNESS_TRAINER: UserRole.FITNESS_TRAINER,
        StaffRole.NUTRITIONIST: UserRole.NUTRITIONIST,
        StaffRole.MASTER_COACH: UserRole.MASTER_COACH,
    }
    if user.role != role_map[expected]:
        raise ForbiddenError(f"This endpoint requires the {expected.value} role.")


# ── Trainer invite routes ─────────────────────────────────────────────────────


@router.post("/trainer/invites", response_model=InviteResponse, status_code=201)
async def trainer_generate_invite(
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(
        get_invite_service
    ),  # ← replace with get_invite_service dep
) -> InviteResponse:
    """Generate a new invite code. Share with the client who should connect."""
    _require_staff_role(current_user, StaffRole.FITNESS_TRAINER)
    invite = await invite_service.generate_invite(
        staff_id=current_user.id,
        staff_role=StaffRole.FITNESS_TRAINER,
    )
    return InviteResponse.model_validate(invite)


@router.get("/trainer/invites", response_model=list[InviteResponse])
async def trainer_list_invites(
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> list[InviteResponse]:
    _require_staff_role(current_user, StaffRole.FITNESS_TRAINER)
    invites = await invite_service.list_active_invites(current_user.id)
    return [InviteResponse.model_validate(i) for i in invites]


@router.delete("/trainer/invites/{invite_id}", status_code=204)
async def trainer_revoke_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> None:
    _require_staff_role(current_user, StaffRole.FITNESS_TRAINER)
    await invite_service.revoke_invite(invite_id, current_user.id)


# ── Nutritionist invite routes ────────────────────────────────────────────────


@router.post("/nutritionist/invites", response_model=InviteResponse, status_code=201)
async def nutritionist_generate_invite(
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> InviteResponse:
    _require_staff_role(current_user, StaffRole.NUTRITIONIST)
    invite = await invite_service.generate_invite(
        staff_id=current_user.id,
        staff_role=StaffRole.NUTRITIONIST,
    )
    return InviteResponse.model_validate(invite)


@router.get("/nutritionist/invites", response_model=list[InviteResponse])
async def nutritionist_list_invites(
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> list[InviteResponse]:
    _require_staff_role(current_user, StaffRole.NUTRITIONIST)
    return [
        InviteResponse.model_validate(i)
        for i in await invite_service.list_active_invites(current_user.id)
    ]


@router.delete("/nutritionist/invites/{invite_id}", status_code=204)
async def nutritionist_revoke_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> None:
    _require_staff_role(current_user, StaffRole.NUTRITIONIST)
    await invite_service.revoke_invite(invite_id, current_user.id)


# ── Master coach invite routes ────────────────────────────────────────────────


@router.post("/coach/invites", response_model=InviteResponse, status_code=201)
async def coach_generate_invite(
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> InviteResponse:
    _require_staff_role(current_user, StaffRole.MASTER_COACH)
    invite = await invite_service.generate_invite(
        staff_id=current_user.id,
        staff_role=StaffRole.MASTER_COACH,
    )
    return InviteResponse.model_validate(invite)


@router.get("/coach/invites", response_model=list[InviteResponse])
async def coach_list_invites(
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> list[InviteResponse]:
    _require_staff_role(current_user, StaffRole.MASTER_COACH)
    return [
        InviteResponse.model_validate(i)
        for i in await invite_service.list_active_invites(current_user.id)
    ]


@router.delete("/coach/invites/{invite_id}", status_code=204)
async def coach_revoke_invite(
    invite_id: UUID,
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> None:
    _require_staff_role(current_user, StaffRole.MASTER_COACH)
    await invite_service.revoke_invite(invite_id, current_user.id)


# ── Client connection routes ──────────────────────────────────────────────────


@router.post("/client/connect", status_code=200)
async def client_connect(
    body: ConnectWithCoachRequest,
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> dict:
    """
    Accept an invite code. Creates the coaching assignment.
    The code validator in ConnectWithCoachRequest normalises spacing/casing.
    """
    if current_user.role.value != "client":
        raise ForbiddenError("Only clients can accept invite codes.")
    await invite_service.accept_invite(
        code=body.code,
        client_id=current_user.id,
    )
    return {"message": "Connected successfully."}


@router.get("/client/coaches", response_model=ClientCoachesResponse)
async def client_get_coaches(
    current_user: User = Depends(get_current_user),
    invite_service: InviteService = Depends(get_invite_service),
) -> ClientCoachesResponse:
    """Return the client's current coaching staff."""
    coaches = await invite_service.get_client_coaches(current_user.id)
    return ClientCoachesResponse(
        trainer=coaches["trainer"],
        nutritionist=coaches["nutritionist"],
        coach=coaches["coach"],
    )
