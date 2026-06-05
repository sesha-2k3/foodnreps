"""
User and assignment request/response schemas.

Design choice — UserResponse excludes password_hash:
    The domain User entity carries password_hash for the auth flow.
    The response schema explicitly omits it — it must never appear in
    any JSON response regardless of what the entity carries.

Design choice — role exposed as a plain string value, not the enum name:
    UserRole.FITNESS_TRAINER.value == "fitness_trainer". The frontend
    receives "fitness_trainer", not "FITNESS_TRAINER". The str, StrEnum
    base class makes UserRole JSON-serialisable as its value automatically.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from domain.entities.assignment import ClientStaffAssignment
from domain.entities.enums import StaffRole, UserRole
from domain.entities.user import User


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str  # validated as UserRole in SuperAdminService.create_user()


class AssignStaffRequest(BaseModel):
    staff_id: UUID
    staff_role: (
        str  # validated as StaffRole in SuperAdminService.assign_staff_to_client()
    )


class EndAssignmentRequest(BaseModel):
    reason: str = "removed by admin"


class AssignmentResponse(BaseModel):
    id: UUID
    client_id: UUID
    staff_id: UUID
    staff_role: StaffRole
    assigned_at: datetime
    ended_at: datetime | None
    ended_reason: str | None

    @classmethod
    def from_entity(cls, assignment: ClientStaffAssignment) -> "AssignmentResponse":
        return cls(
            id=assignment.id,
            client_id=assignment.client_id,
            staff_id=assignment.staff_id,
            staff_role=assignment.staff_role,
            assigned_at=assignment.assigned_at,
            ended_at=assignment.ended_at,
            ended_reason=assignment.ended_reason,
        )


class OverrideWorkoutRequest(BaseModel):
    program_id: UUID
    override_reason: str


class PaginatedUsersResponse(BaseModel):
    data: list[UserResponse]
    total: int
    limit: int
    offset: int
