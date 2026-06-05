"""
SuperAdminService — platform management, user lifecycle, and plan overrides.

This is the only service that calls AssignmentService. Every other service
checks assignment ownership via repository queries directly. Super admin is
the only actor who manipulates assignments — creating, replacing, and
ending coaching relationships.

Design choice — override requires a non-empty reason string:
    An administrative override of a client's plan is a significant action
    that bypasses the normal coaching relationship. The reason is mandatory
    at the service layer (not just a database NOT NULL) so the error is a
    domain ValidationError with a clear message, not a DB constraint violation.

Design choice — override writes a PlanVersion snapshot before modifying:
    The version snapshot is written BEFORE the plan is changed. If the plan
    save fails, the snapshot still exists — it represents the state
    immediately before the intended override. This is slightly more
    conservative than writing after (which would capture the new state),
    but aligns with the audit intent: "here is what existed before the
    admin changed it."

Design choice — deactivate_user revokes all refresh tokens immediately:
    A deactivated user should not be able to use existing sessions. The
    revoke_all_for_user call invalidates every refresh token in the DB.
    Active access tokens (15 min) continue to work until expiry — this is
    acceptable given the short lifetime. Revoking access tokens would
    require stateful access token storage, which defeats the JWT scalability
    benefit.

Design choice — list_clients uses in-memory pagination (limit/offset):
    IUserRepository.list_clients() returns all clients. Pagination is applied
    in the service by slicing the list. This is correct for Phase 1 with
    hundreds of clients. When the client list grows to thousands, push
    limit/offset into the repository interface and SQL query (a future
    sprint improvement documented in the architecture doc under P2).
"""

import dataclasses
from datetime import UTC, datetime
from uuid import UUID, uuid4

from application.services.assignment_service import AssignmentService
from core.exceptions import NotFoundError, ValidationError
from core.security import hash_password
from domain.entities.enums import ActivityAction, PlanType, UserRole
from domain.entities.plan import PlanActivityLog, PlanVersion
from domain.entities.user import User
from domain.entities.workout import WorkoutProgram
from domain.interfaces.repositories import (
    IDietPlanRepository,
    IPlanActivityLogRepository,
    IPlanVersionRepository,
    IRefreshTokenRepository,
    IUserRepository,
    IWorkoutProgramRepository,
)
from domain.interfaces.services import ISuperAdminService


class SuperAdminService(ISuperAdminService):
    def __init__(
        self,
        user_repo: IUserRepository,
        token_repo: IRefreshTokenRepository,
        workout_repo: IWorkoutProgramRepository,
        diet_repo: IDietPlanRepository,
        plan_version_repo: IPlanVersionRepository,
        activity_log_repo: IPlanActivityLogRepository,
        assignment_service: AssignmentService,
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._workout_repo = workout_repo
        self._diet_repo = diet_repo
        self._plan_version_repo = plan_version_repo
        self._activity_log_repo = activity_log_repo
        self._assignment_service = assignment_service

    # ── User lifecycle ────────────────────────────────────────────────────────

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: str,
    ) -> User:
        """
        Create a new user account.

        role must be a valid UserRole string value ("client", "fitness_trainer",
        "nutritionist", "master_coach", "super_admin"). Raises ValidationError
        on an unrecognised role string.
        """
        try:
            user_role = UserRole(role)
        except ValueError:
            valid = [r.value for r in UserRole]
            raise ValidationError(
                f"'{role}' is not a valid role. Valid roles: {valid}"
            ) from None

        now = datetime.now(tz=UTC)
        new_user = User(
            id=uuid4(),
            email=email.strip().lower(),
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            role=user_role,
            is_active=True,
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        # ConflictError is raised by the repository on email duplicate
        return await self._user_repo.save(new_user)

    async def get_user(self, user_id: UUID) -> User:
        """Retrieve any user by ID. Raises NotFoundError if not found."""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def list_clients(self, limit: int = 20, offset: int = 0) -> list[User]:
        """
        Return a paginated list of all non-deleted clients.

        Note: pagination is applied in-memory (see module docstring).
        Push limit/offset to the repository in a future sprint.
        """
        all_clients = await self._user_repo.list_clients()
        return all_clients[offset : offset + limit]

    async def list_staff(self) -> list[User]:
        """Return all non-deleted coaching staff users."""
        return await self._user_repo.list_staff()

    async def deactivate_user(self, user_id: UUID) -> None:
        """
        Deactivate a user account and immediately revoke all their refresh tokens.

        The user's is_active flag is set to False. All existing refresh tokens
        are revoked so in-progress sessions cannot be refreshed. Active access
        tokens (15 min lifetime) continue until expiry — this is the accepted
        tradeoff for stateless JWTs.
        """
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        if not user.is_active:
            return  # idempotent — already deactivated

        deactivated = dataclasses.replace(
            user,
            is_active=False,
            updated_at=datetime.now(tz=UTC),
        )
        await self._user_repo.save(deactivated)
        await self._token_repo.revoke_all_for_user(
            user_id=user_id,
            revoked_at=datetime.now(tz=UTC),
        )

    # ── Plan overrides ────────────────────────────────────────────────────────

    async def override_workout_programme(
        self,
        program_id: UUID,
        override_reason: str,
        admin_id: UUID,
    ) -> WorkoutProgram:
        """
        Record an administrative override on a workout programme.

        This method is called to commit an override with a mandatory reason.
        The actual content changes (prescription edits) are made via the
        prescription repository in the Sprint 4 route handler before this
        method is called.

        Steps:
        1. Validate the reason is non-empty.
        2. Load the programme.
        3. Write a PlanVersion snapshot of the current state.
        4. Apply override metadata (last_modified_by, override_reason, version+1).
        5. Save the updated programme.
        6. Write an activity log entry.
        """
        if not override_reason.strip():
            raise ValidationError(
                "A reason is required for administrative overrides. "
                "Provide a clear explanation of what was changed and why."
            )

        program = await self._workout_repo.get_by_id(program_id)
        if program is None:
            raise NotFoundError(f"Workout programme {program_id} not found")

        # Snapshot the current state before modification
        snapshot: dict[str, object] = {
            "plan_id": str(program.id),
            "plan_type": "workout",
            "version": program.version,
            "name": program.name,
            "coach_notes": program.coach_notes,
            "is_active": program.is_active,
            "owner_id": str(program.owner_id),
            "created_by_id": str(program.created_by_id),
        }
        version_record = PlanVersion(
            id=uuid4(),
            plan_type=PlanType.WORKOUT,
            plan_id=program.id,
            snapshot=snapshot,
            modified_by=admin_id,
            modified_at=datetime.now(tz=UTC),
            change_reason=override_reason,
        )
        await self._plan_version_repo.save(version_record)

        # Apply override metadata — version increment handled by the repository
        now = datetime.now(tz=UTC)
        updated = dataclasses.replace(
            program,
            last_modified_by=admin_id,
            last_modified_at=now,
            override_reason=override_reason,
            updated_at=now,
        )
        saved = await self._workout_repo.save(updated)

        await self._log_activity(
            plan_type=PlanType.WORKOUT,
            plan_id=program.id,
            actor_id=admin_id,
            action=ActivityAction.OVERRIDE_APPLIED,
            metadata={
                "reason": override_reason,
                "modified_by_role": "super_admin",
            },
        )
        return saved

    # ── Assignment delegation ─────────────────────────────────────────────────

    async def assign_staff_to_client(
        self,
        client_id: UUID,
        staff_id: UUID,
        staff_role: str,
        admin_id: UUID,
    ) -> object:
        """
        Assign a coaching staff member to a client.
        Delegates conflict validation entirely to AssignmentService.
        """
        from domain.entities.enums import StaffRole

        try:
            role = StaffRole(staff_role)
        except ValueError:
            valid = [r.value for r in StaffRole]
            raise ValidationError(
                f"'{staff_role}' is not a valid staff role. Valid: {valid}"
            ) from None

        return await self._assignment_service.assign_staff(
            client_id=client_id,
            staff_id=staff_id,
            staff_role=role,
            assigned_by=admin_id,
        )

    async def end_staff_assignment(
        self, assignment_id: UUID, reason: str = "removed by admin"
    ) -> None:
        """End an active coaching assignment."""
        await self._assignment_service.end_assignment(
            assignment_id=assignment_id,
            ended_reason=reason,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _log_activity(
        self,
        plan_type: PlanType,
        plan_id: UUID,
        actor_id: UUID,
        action: ActivityAction,
        metadata: dict[str, object] | None = None,
    ) -> None:
        log = PlanActivityLog(
            id=uuid4(),
            plan_type=plan_type,
            plan_id=plan_id,
            actor_id=actor_id,
            action=action,
            metadata=metadata,
            occurred_at=datetime.now(tz=UTC),
        )
        await self._activity_log_repo.save(log)
