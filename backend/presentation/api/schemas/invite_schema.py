"""
Invite Pydantic schemas.
Place at: presentation/api/schemas/invite_schema.py
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator

# ── Responses ─────────────────────────────────────────────────────────────────

class InviteResponse(BaseModel):
    id: UUID
    code: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CoachInfoResponse(BaseModel):
    id: UUID
    full_name: str
    email: str
    role: str
    assigned_at: str


class ClientCoachesResponse(BaseModel):
    trainer:      CoachInfoResponse | None
    nutritionist: CoachInfoResponse | None
    coach:        CoachInfoResponse | None


# ── Requests ──────────────────────────────────────────────────────────────────

class ConnectWithCoachRequest(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def normalise_code(cls, v: str) -> str:
        """Accept "qrt-k4p", "QRT K4P", "qrtk4p" — normalise to "QRT-K4P"."""
        cleaned = v.upper().strip().replace(" ", "").replace("_", "")
        # Insert hyphen if missing (user typed "QRTK4P" instead of "QRT-K4P")
        if "-" not in cleaned and len(cleaned) == 6:
            cleaned = f"{cleaned[:3]}-{cleaned[3:]}"
        return cleaned
