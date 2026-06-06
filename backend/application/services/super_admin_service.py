"""
Super admin service — application/services/super_admin_service.py
"""

from dataclasses import replace
from datetime import datetime, timezone
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
    IWorkoutProgramRepository,
)
from domain.interfaces.services import IAssignmentService, ISuperAdminService


class SuperAdminService(ISuperAdminService):
    def __init__(
        self,
        user_repo: IUserRepository,
        token_repo: IRefreshTokenRepository,
        workout_repo: IWorkoutProgramRepository,
        diet_repo: IDietPlanRepository,
        plan_version_repo: IPlanVersionRepository,  # matches dependencies.py
        activity_log_repo: IPlanActivityLogRepository,  # matches dependencies.py
        assignment_service: IAssignmentService,  # matches dependencies.py
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._workout_repo = workout_repo
        self._diet_repo = diet_repo
        self._version_repo = plan_version_repo
        self._activity_repo = activity_log_repo
        self._assignment_service = assignment_service

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

    async def override_workout_programme(
        self,
        program_id: UUID,
        override_reason: str,
        admin_id: UUID,
    ) -> WorkoutProgram:
        if not override_reason.strip():
            raise ValidationError("A reason for the override is required.")

        program = await self._workout_repo.get_by_id(program_id)
        if program is None:
            raise NotFoundError(f"Programme {program_id} not found")

        now = datetime.now(tz=timezone.utc)
        updated = replace(
            program,
            override_reason=override_reason,
            last_modified_by=admin_id,
            last_modified_at=now,
            updated_at=now,
        )
        saved = await self._workout_repo.save(updated)

        await self._version_repo.save(
            PlanVersion(
                id=uuid4(),
                plan_type=PlanType.WORKOUT,
                plan_id=program_id,
                snapshot={"override_reason": override_reason},
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
                metadata={"reason": override_reason},
                occurred_at=now,
            )
        )

        return saved
