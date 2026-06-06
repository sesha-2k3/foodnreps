"""
Super admin service — application/services/super_admin_service.py
"""

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

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
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)
from domain.interfaces.services import IAssignmentService, ISuperAdminService

# Prescription fields that carry Decimal values in the domain entity.
# JSON delivers them as float — convert before calling dataclasses.replace().
_DECIMAL_FIELDS = frozenset({"prescribed_load_kg", "prescribed_rpe"})


class SuperAdminService(ISuperAdminService):
    def __init__(
        self,
        user_repo: IUserRepository,
        token_repo: IRefreshTokenRepository,
        workout_repo: IWorkoutProgramRepository,
        diet_repo: IDietPlanRepository,
        plan_version_repo: IPlanVersionRepository,
        activity_log_repo: IPlanActivityLogRepository,
        assignment_service: IAssignmentService,
        prescription_repo: IWorkoutPrescriptionRepository,  # NEW
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._workout_repo = workout_repo
        self._diet_repo = diet_repo
        self._version_repo = plan_version_repo
        self._activity_repo = activity_log_repo
        self._assignment_service = assignment_service
        self._prescription_repo = prescription_repo

    # ── User lifecycle ────────────────────────────────────────────────────────

    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: str,
    ) -> User:
        try:
            user_role = UserRole(role)
        except ValueError:
            raise ValidationError(f"Invalid role: {role!r}")

        now = datetime.now(tz=timezone.utc)
        user = User(
            id=uuid4(),
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=user_role,
            is_active=True,
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        return await self._user_repo.save(user)

    async def deactivate_user(self, user_id: UUID) -> None:
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        now = datetime.now(tz=timezone.utc)
        updated = replace(user, is_active=False, updated_at=now)
        await self._user_repo.save(updated)
        await self._token_repo.revoke_all_for_user(user_id, now)

    # ── Plan override ─────────────────────────────────────────────────────────

    async def override_workout_programme(
        self,
        program_id: UUID,
        override_reason: str,
        admin_id: UUID,
        changes: list[dict] | None = None,
    ) -> WorkoutProgram:
        """
        Apply an atomic admin override:
          1. Validate reason (non-empty — enforced here, not just at schema level).
          2. Apply each prescription patch via dataclasses.replace() + save().
          3. Stamp override_reason on the programme.
          4. Write one PlanVersion snapshot covering all changes.
          5. Write one PlanActivityLog entry.

        All five steps run in the caller's session — committed or rolled back
        together by the session dependency in get_session().
        """
        if not override_reason.strip():
            raise ValidationError("A reason for the override is required.")

        program = await self._workout_repo.get_by_id(program_id)
        if program is None:
            raise NotFoundError(f"Programme {program_id} not found")

        now = datetime.now(tz=timezone.utc)
        applied: list[dict] = []

        for change in changes or []:
            pid = change.get("prescription_id")
            if not pid:
                continue
            prescription = await self._prescription_repo.get_by_id(UUID(str(pid)))
            if prescription is None:
                continue

            # Build patch dict — skip None values and the id key itself.
            # Convert float → Decimal for domain fields that require it.
            patch: dict = {}
            for field, value in change.items():
                if field == "prescription_id" or value is None:
                    continue
                if field in _DECIMAL_FIELDS:
                    patch[field] = Decimal(str(value))
                else:
                    patch[field] = value

            if not patch:
                continue

            patch["updated_at"] = now
            updated_prescription = replace(prescription, **patch)
            await self._prescription_repo.save(updated_prescription)
            applied.append({"prescription_id": str(pid), **patch})

        # Stamp the programme
        updated_program = replace(
            program,
            override_reason=override_reason,
            last_modified_by=admin_id,
            last_modified_at=now,
            updated_at=now,
        )
        saved = await self._workout_repo.save(updated_program)

        # Append-only audit records
        await self._version_repo.save(
            PlanVersion(
                id=uuid4(),
                plan_type=PlanType.WORKOUT,
                plan_id=program_id,
                snapshot={
                    "override_reason": override_reason,
                    "changes_count": len(applied),
                    "changes": [{k: str(v) for k, v in c.items()} for c in applied],
                },
                modified_by=admin_id,
                modified_at=now,
                change_reason=override_reason,
            )
        )

        await self._activity_repo.save(
            PlanActivityLog(
                id=uuid4(),
                plan_type=PlanType.WORKOUT,
                plan_id=program_id,
                actor_id=admin_id,
                action=ActivityAction.OVERRIDE_APPLIED,
                metadata={"reason": override_reason, "changes_count": len(applied)},
                occurred_at=now,
            )
        )

        return saved
