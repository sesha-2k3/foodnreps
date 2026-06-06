"""
Admin request/response schemas — presentation/api/schemas/admin_schema.py
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

# ── User management ───────────────────────────────────────────────────────────


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str

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
    staff_role: str


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
    fitness_trainer: AssignmentResponse | None = None
    nutritionist: AssignmentResponse | None = None
    master_coach: AssignmentResponse | None = None


# ── Plan override ─────────────────────────────────────────────────────────────


class PrescriptionPatch(BaseModel):
    """
    One prescription's worth of changes.
    All fields except prescription_id are optional — only send what changed.
    Pydantic v2 coerces JSON floats to Decimal automatically.
    """

    prescription_id: UUID
    working_sets: int | None = None
    reps_min: int | None = None
    reps_max: int | None = None
    reps_note: str | None = None
    prescribed_load_kg: Decimal | None = None
    prescribed_load_text: str | None = None
    prescribed_rpe: Decimal | None = None
    prescribed_rir: int | None = None
    rest_seconds: int | None = None
    instructions: str | None = None


class OverrideWorkoutRequest(BaseModel):
    """
    Atomic override: reason + all prescription patches submitted together.
    The reason is stored in plan_versions.change_reason and
    workout_programs.override_reason. Changes are applied before the
    version record is written so the snapshot reflects the post-override state.
    """

    override_reason: str
    changes: list[PrescriptionPatch] = []

    @field_validator("override_reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Override reason cannot be empty")
        return v
