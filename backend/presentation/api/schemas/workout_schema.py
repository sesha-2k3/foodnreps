"""
Workout request/response schemas.

Design choice — both raw and display fields on WorkoutPrescriptionResponse:
    The client view uses reps_display ("6–8") and load_display ("70 kg").
    The coach edit view needs the raw values (reps_min, reps_max,
    prescribed_load_kg) to populate editable table cells.
    Both sets of fields are included in the same response so a single
    endpoint serves both views without a separate coach-specific schema.

Design choice — logs nested under prescriptions:
    The frontend renders the prescription table (blue) and log table (amber)
    per day. Nesting logs under their prescription avoids a separate
    GET /logs endpoint and a second network round-trip on every page load.
    The N+1 query (one log fetch per prescription) is a known Phase 1
    limitation — the fix is selectinload in the repository, which requires
    no change to these schemas.

Design choice — Decimal → float at this boundary:
    Domain entities use Decimal for monetary-precision arithmetic.
    JSON has no Decimal type. Schemas expose these as float | None.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutLog,
    WorkoutPrescription,
    WorkoutProgram,
)


# ── Display helpers ────────────────────────────────────────────────────────────


def _format_load(prescription: WorkoutPrescription) -> str | None:
    kg = prescription.prescribed_load_kg
    text = prescription.prescribed_load_text
    if kg is not None and text:
        return f"{kg:g} kg ({text})"
    if kg is not None:
        return f"{kg:g} kg"
    return text


# ── Workout log (RED side) ─────────────────────────────────────────────────────


class WorkoutLogResponse(BaseModel):
    id: UUID
    prescription_id: UUID | None
    exercise_name: str | None
    logged_at: date
    actual_sets: int
    actual_reps: int
    actual_load_kg: float | None
    actual_rpe: float | None
    readiness: int | None
    time_taken_seconds: int | None
    client_notes: str | None
    tonnage_kg: float | None

    @classmethod
    def from_entity(cls, log: WorkoutLog) -> "WorkoutLogResponse":
        return cls(
            id=log.id,
            prescription_id=log.prescription_id,
            exercise_name=log.exercise_name,
            logged_at=log.logged_at,
            actual_sets=log.actual_sets,
            actual_reps=log.actual_reps,
            actual_load_kg=float(log.actual_load_kg)
            if log.actual_load_kg is not None
            else None,
            actual_rpe=float(log.actual_rpe) if log.actual_rpe is not None else None,
            readiness=log.readiness,
            time_taken_seconds=log.time_taken_seconds,
            client_notes=log.client_notes,
            tonnage_kg=float(log.tonnage_kg) if log.tonnage_kg is not None else None,
        )


# ── Prescription (BLUE side) ───────────────────────────────────────────────────


class WorkoutPrescriptionResponse(BaseModel):
    id: UUID
    order_index: int
    exercise_label: str  # "A", "B", "C"
    exercise_name: str
    warmup_sets: int | None
    working_sets: int | None

    # Raw reps fields — needed by coach edit view
    reps_min: int | None
    reps_max: int | None
    reps_note: str | None

    # Derived display — needed by client read view
    reps_display: str  # "6–8", "5", "max reps"

    # Raw load fields — needed by coach edit view
    prescribed_load_kg: float | None
    prescribed_load_text: str | None

    # Derived display — needed by client read view
    load_display: str | None  # "70 kg", "BW"

    prescribed_rpe: float | None
    prescribed_rir: int | None
    rest_seconds: int | None
    instructions: str | None

    # Nested logs — needed by client log table
    logs: list[WorkoutLogResponse] = []

    @classmethod
    def from_entity(
        cls,
        p: WorkoutPrescription,
        logs: list[WorkoutLog] | None = None,
    ) -> "WorkoutPrescriptionResponse":
        return cls(
            id=p.id,
            order_index=p.order_index,
            exercise_label=p.exercise_label,
            exercise_name=p.exercise_name,
            warmup_sets=p.warmup_sets,
            working_sets=p.working_sets,
            reps_min=p.reps_min,
            reps_max=p.reps_max,
            reps_note=p.reps_note,
            reps_display=p.reps_display,
            prescribed_load_kg=float(p.prescribed_load_kg)
            if p.prescribed_load_kg is not None
            else None,
            prescribed_load_text=p.prescribed_load_text,
            load_display=_format_load(p),
            prescribed_rpe=float(p.prescribed_rpe)
            if p.prescribed_rpe is not None
            else None,
            prescribed_rir=p.prescribed_rir,
            rest_seconds=p.rest_seconds,
            instructions=p.instructions,
            logs=[WorkoutLogResponse.from_entity(log) for log in (logs or [])],
        )


class AddPrescriptionRequest(BaseModel):
    order_index: int
    exercise_name: str
    warmup_sets: int | None = None
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


class UpdatePrescriptionRequest(BaseModel):
    exercise_name: str | None = None
    warmup_sets: int | None = None
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


# ── Programme day ──────────────────────────────────────────────────────────────


class ProgramDayResponse(BaseModel):
    id: UUID
    day_number: int
    label: str
    notes: str | None
    prescriptions: list[WorkoutPrescriptionResponse]

    @classmethod
    def from_entities(
        cls,
        day: ProgramDay,
        prescriptions: list[WorkoutPrescription],
        logs_by_prescription: dict[UUID, list[WorkoutLog]] | None = None,
    ) -> "ProgramDayResponse":
        logs_map = logs_by_prescription or {}
        return cls(
            id=day.id,
            day_number=day.day_number,
            label=day.label,
            notes=day.notes,
            prescriptions=[
                WorkoutPrescriptionResponse.from_entity(p, logs_map.get(p.id, []))
                for p in prescriptions
            ],
        )


class AddDayRequest(BaseModel):
    day_number: int
    label: str = "Day"
    notes: str | None = None


# ── Programme week ─────────────────────────────────────────────────────────────


class ProgramWeekResponse(BaseModel):
    id: UUID
    week_number: int
    label: str
    notes: str | None
    days: list[ProgramDayResponse]

    @classmethod
    def from_entities(
        cls,
        week: ProgramWeek,
        days: list[ProgramDayResponse],
    ) -> "ProgramWeekResponse":
        return cls(
            id=week.id,
            week_number=week.week_number,
            label=week.label,
            notes=week.notes,
            days=days,
        )


class AddWeekRequest(BaseModel):
    week_number: int
    label: str = "Week"
    notes: str | None = None


# ── Programme (top level) ──────────────────────────────────────────────────────


class WorkoutProgramResponse(BaseModel):
    id: UUID
    name: str
    is_active: bool
    is_personal: bool
    is_template: bool
    coach_notes: str | None
    owner_id: UUID
    created_by_id: UUID
    version: int
    override_reason: str | None
    created_at: datetime
    updated_at: datetime
    weeks: list[ProgramWeekResponse] = []

    @classmethod
    def from_entity(
        cls,
        program: WorkoutProgram,
        weeks: list[ProgramWeekResponse] | None = None,
    ) -> "WorkoutProgramResponse":
        return cls(
            id=program.id,
            name=program.name,
            is_active=program.is_active,
            is_personal=program.is_personal,
            is_template=program.is_template,
            coach_notes=program.coach_notes,
            owner_id=program.owner_id,
            created_by_id=program.created_by_id,
            version=program.version,
            override_reason=program.override_reason,
            created_at=program.created_at,
            updated_at=program.updated_at,
            weeks=weeks or [],
        )


class CreateProgrammeRequest(BaseModel):
    name: str
    coach_notes: str | None = None


# ── Workout log request ────────────────────────────────────────────────────────


class LogWorkoutRequest(BaseModel):
    prescription_id: UUID | None = None
    exercise_name: str | None = None
    actual_sets: int
    actual_reps: int
    actual_load_kg: Decimal | None = None
    actual_rpe: Decimal | None = None
    readiness: int | None = None
    time_taken_seconds: int | None = None
    client_notes: str | None = None
    logged_at: date | None = None
