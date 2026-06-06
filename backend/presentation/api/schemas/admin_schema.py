"""
Admin request/response schemas — presentation/api/schemas/admin_schema.py
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator


# ── User management ───────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str  # UserRole string value

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    limit: int
    offset: int


# ── Assignment management ─────────────────────────────────────────────────────

class AssignStaffRequest(BaseModel):
    staff_id: UUID
    staff_role: str  # StaffRole string value


class AssignmentResponse(BaseModel):
    id: UUID
    client_id: UUID
    staff_id: UUID
    staff_role: str
    assigned_at: datetime
    ended_at: datetime | None = None
    assigned_by: UUID

    model_config = {"from_attributes": True}


class EndAssignmentRequest(BaseModel):
    ended_reason: str


class ClientAssignmentsResponse(BaseModel):
    """All active assignments for a client, keyed by role."""
    fitness_trainer: AssignmentResponse | None = None
    nutritionist: AssignmentResponse | None = None
    master_coach: AssignmentResponse | None = None


# ── Plan override ─────────────────────────────────────────────────────────────

class OverrideReasonRequest(BaseModel):
    override_reason: str

    @field_validator("override_reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Override reason cannot be empty")
        return v
