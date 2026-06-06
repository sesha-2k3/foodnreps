"""
InviteService — manages coaching invite code lifecycle.
Place at: application/services/invite_service.py

Design choice — InviteService delegates assignment creation to AssignmentService:
    InviteService owns the invite code lifecycle (generate, validate, mark used).
    AssignmentService owns all coaching conflict rules and assignment creation.
    InviteService calls AssignmentService.assign_staff() after validating the
    invite code — it does not bypass conflict rules or create assignments directly.

Design choice — assigned_by is set to the staff member's own UUID:
    The original architecture required a super_admin UUID as assigned_by.
    Invite-based assignment relaxes this: the staff member initiated the
    invite, the client accepted it — the staff member is the correct
    initiator for the audit trail. No super_admin involvement is needed
    for a self-service connection that the coaching staff member explicitly
    set up.

Design choice — max 20 active invites per staff member:
    Without a cap, a staff member could flood the invite table. 20 active
    invites is generous for onboarding new clients while preventing abuse.
    Attempting to generate when at the limit raises ValidationError.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    SelfAssignmentError,
    ValidationError,
)
from domain.entities.enums import StaffRole, UserRole
from domain.entities.invite import CoachingInvite, generate_invite_code
from domain.interfaces.repositories import (
    IClientStaffAssignmentRepository,
    ICoachingInviteRepository,
    IUserRepository,
)
from domain.interfaces.services import IAssignmentService

_MAX_ACTIVE_INVITES = 20
_DEFAULT_EXPIRY_DAYS = 7


class InviteService:
    def __init__(
        self,
        invite_repo: ICoachingInviteRepository,
        assignment_service: IAssignmentService,
        assignment_repo: IClientStaffAssignmentRepository,
        user_repo: IUserRepository,
    ) -> None:
        self._invite_repo = invite_repo
        self._assignment_service = assignment_service
        self._assignment_repo = assignment_repo
        self._user_repo = user_repo

    # ── Staff-facing operations ───────────────────────────────────────────────

    async def generate_invite(
        self,
        staff_id: UUID,
        staff_role: StaffRole,
        expires_in_days: int = _DEFAULT_EXPIRY_DAYS,
    ) -> CoachingInvite:
        """
        Generate a new invite code for this staff member.
        Raises ValidationError if the staff member already has MAX_ACTIVE_INVITES.
        """
        active = await self._invite_repo.list_active_by_staff(staff_id)
        if len(active) >= _MAX_ACTIVE_INVITES:
            raise ValidationError(
                f"You already have {_MAX_ACTIVE_INVITES} active invite codes. "
                "Revoke some before generating new ones."
            )

        # Generate a unique code — collision is astronomically unlikely
        # but we loop defensively
        code = generate_invite_code()
        while await self._invite_repo.get_by_code(code):
            code = generate_invite_code()

        now = datetime.now(tz=UTC)
        invite = CoachingInvite(
            id=uuid4(),
            staff_id=staff_id,
            staff_role=staff_role,
            code=code,
            expires_at=now + timedelta(days=expires_in_days),
            used_at=None,
            used_by=None,
            created_at=now,
        )
        return await self._invite_repo.save(invite)

    async def list_active_invites(self, staff_id: UUID) -> list[CoachingInvite]:
        return await self._invite_repo.list_active_by_staff(staff_id)

    async def revoke_invite(self, invite_id: UUID, staff_id: UUID) -> None:
        """
        Hard-delete an unused invite.
        Only the staff member who created it can revoke it.
        """
        invite = await self._invite_repo.get_by_id(invite_id)
        if not invite:
            raise NotFoundError("Invite not found.")
        if invite.staff_id != staff_id:
            raise ForbiddenError("You can only revoke your own invites.")
        if invite.is_used:
            raise ConflictError("Cannot revoke an invite that has already been used.")
        await self._invite_repo.delete(invite_id)

    # ── Client-facing operations ──────────────────────────────────────────────

    async def accept_invite(
        self,
        code: str,
        client_id: UUID,
    ) -> CoachingInvite:
        """
        Accept an invite code. Creates the ClientStaffAssignment.

        Raises:
            NotFoundError        — code doesn't exist
            ValidationError      — code has expired
            ConflictError        — code already used, or assignment conflict
            SelfAssignmentError  — client and staff member are the same user
        """
        invite = await self._invite_repo.get_by_code(code)
        if not invite:
            raise NotFoundError(
                "Invite code not found. Check the code and try again."
            )

        if invite.is_expired:
            raise ValidationError(
                "This invite code has expired. Ask your coach for a new one."
            )

        if invite.is_used:
            raise ConflictError(
                "This invite code has already been used."
            )

        if invite.staff_id == client_id:
            raise SelfAssignmentError(
                "You cannot connect with yourself."
            )

        # Validate the accepting user is actually a client
        client = await self._user_repo.get_by_id(client_id)
        if not client or client.role != UserRole.CLIENT:
            raise ForbiddenError(
                "Only clients can accept invite codes."
            )

        # Delegate conflict validation + assignment creation to AssignmentService.
        # assigned_by = staff_id: the staff member initiated this via their invite.
        await self._assignment_service.assign_staff(
            client_id=client_id,
            staff_id=invite.staff_id,
            staff_role=invite.staff_role,
            assigned_by=invite.staff_id,
        )

        # Mark the invite as used
        now = datetime.now(tz=UTC)
        await self._invite_repo.mark_used(
            invite_id=invite.id,
            used_by=client_id,
            used_at=now,
        )

        # Return the updated invite (with used_at/used_by populated)
        updated = await self._invite_repo.get_by_id(invite.id)
        return updated  # type: ignore[return-value]

    async def get_client_coaches(self, client_id: UUID) -> dict[str, dict | None]:
        """
        Return current active coaching staff for a client.
        Shape: { "trainer": {...user info} | null, "nutritionist": ..., "coach": ... }
        """
        assignments = await self._assignment_repo.get_active_for_client(client_id)

        result: dict[str, dict | None] = {
            "trainer": None,
            "nutritionist": None,
            "coach": None,
        }

        role_to_key = {
            StaffRole.FITNESS_TRAINER: "trainer",
            StaffRole.NUTRITIONIST: "nutritionist",
            StaffRole.MASTER_COACH: "coach",
        }

        for assignment in assignments:
            key = role_to_key.get(assignment.staff_role)
            if key:
                staff = await self._user_repo.get_by_id(assignment.staff_id)
                if staff:
                    result[key] = {
                        "id": str(staff.id),
                        "full_name": staff.full_name,
                        "email": staff.email,
                        "role": assignment.staff_role.value,
                        "assigned_at": assignment.assigned_at.isoformat(),
                    }

        return result
