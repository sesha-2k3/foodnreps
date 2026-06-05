"""
Workout domain entities: WorkoutProgram → ProgramWeek → ProgramDay →
WorkoutPrescription → WorkoutLog.

These five entities model the complete workout hierarchy, from the top-level
named programme a coach creates, down to an individual client log entry for
one exercise on one day.

The hierarchy mirrors the schema structure exactly:
    WorkoutProgram (1) → (many) ProgramWeek
    ProgramWeek    (1) → (many) ProgramDay
    ProgramDay     (1) → (many) WorkoutPrescription  ← coach fills (BLUE)
    WorkoutPrescription (1) → (many) WorkoutLog      ← client fills (RED)
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from domain.entities.enums import VideoSource


# ── Programme container ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class WorkoutProgram:
    """
    A named, structured workout programme.
    Maps to `workout_programs`. Replaces the former `workout_plans`.

    Design choice — 'programme' not 'plan':
        A plan implies a flat list. A programme has temporal structure
        (weeks, days). The name communicates this hierarchy.

    Design choice — is_personal vs is_template:
        is_personal: owner built it for themselves (no coach involved).
        is_template: a coach blueprint not yet assigned to any client.
        These two flags are independent. A coach can have a personal
        programme (is_personal=True, is_template=False) AND a template
        (is_personal=False, is_template=True) at the same time.

    Design choice — version for optimistic locking:
        Two coaches editing the same client's programme simultaneously
        would silently overwrite each other without this. The repository
        checks WHERE id = ? AND version = ? before updating. If the
        version has changed, it raises PlanVersionConflictError.
    """
    id:               UUID
    owner_id:         UUID
    created_by_id:    UUID
    name:             str
    is_active:        bool
    is_personal:      bool
    is_template:      bool
    coach_notes:      str | None
    version:          int
    last_modified_by: UUID | None
    last_modified_at: datetime | None
    override_reason:  str | None    # populated only for super_admin writes
    created_at:       datetime
    updated_at:       datetime


# ── Structural containers ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ProgramWeek:
    """
    A named week within a programme.
    Maps to `program_weeks`.

    Design choice — week_number not week_date:
        Weeks are relative positions, not calendar dates. Week 3 means
        "the third training week" regardless of when the client starts.
        The UI computes calendar dates from the client's programme start
        date at render time.
    """
    id:          UUID
    program_id:  UUID
    week_number: int
    label:       str            # "Week 1", "Deload Week", "Peak Week"
    notes:       str | None
    created_at:  datetime


@dataclass(frozen=True)
class ProgramDay:
    """
    A named training day within a week.
    Maps to `program_days`.

    Design choice — day_number not day_of_week:
        "Day 1" means "the first session of this week", not "Monday".
        A client training Tuesday/Thursday/Saturday runs Day 1 on Tuesday.
        Storing day_of_week would encode a calendar assumption that breaks
        for non-standard schedules.
    """
    id:         UUID
    week_id:    UUID
    day_number: int
    label:      str             # "Day 1", "Upper Body", "Pull Day"
    notes:      str | None
    created_at: datetime


# ── Prescription (BLUE — coach fills) ────────────────────────────────────────

@dataclass(frozen=True)
class WorkoutPrescription:
    """
    The coach's prescription for one exercise within a day.
    This is the BLUE side of the spreadsheet.
    Maps to `workout_prescriptions`.

    Design choice — reps as (reps_min, reps_max, reps_note):
        Reps in strength programming are not always a single integer:
        - Fixed:   reps_min=5, reps_max=5, reps_note=None
        - Range:   reps_min=6, reps_max=8, reps_note=None
        - Open:    reps_min=None, reps_max=None, reps_note="max reps, stop when speed drops"
        Storing "6-8" as a string violates 1NF (two facts in one column).

    Design choice — load as (prescribed_load_kg, prescribed_load_text):
        Load can be numeric ("75kg"), bodyweight ("BW"), or qualitative
        ("Strict form"). Two columns handle all cases without coercion.

    Design choice — __post_init__ enforces reps constraint:
        At least reps_min or reps_note must be provided. Mirrors the DB
        CHECK constraint and catches the violation before any DB call.
    """
    id:                   UUID
    day_id:               UUID
    order_index:          int            # 1, 2, 3... → rendered as A, B, C in UI
    exercise_name:        str
    warmup_sets:          int | None
    working_sets:         int | None
    reps_min:             int | None
    reps_max:             int | None
    reps_note:            str | None
    prescribed_load_kg:   Decimal | None
    prescribed_load_text: str | None     # "BW", "Strict", "70% of 1RM"
    prescribed_rpe:       Decimal | None # e.g. 8.0, 8.5
    prescribed_rir:       int | None     # Reps In Reserve
    rest_seconds:         int | None
    instructions:         str | None
    created_at:           datetime
    updated_at:           datetime

    def __post_init__(self) -> None:
        """
        Reps specification: at least reps_min or reps_note is required.
        Mirrors: CHECK (reps_min IS NOT NULL OR reps_note IS NOT NULL)
        """
        if self.reps_min is None and self.reps_note is None:
            raise ValueError(
                "WorkoutPrescription requires either reps_min or reps_note. "
                "Provide reps_min for numeric prescriptions or reps_note "
                "for open-ended prescriptions (e.g. 'max reps')."
            )

    @property
    def reps_display(self) -> str:
        """
        Human-readable reps string for the UI.
        Examples: "6–8", "5", "max reps — stop when speed drops"
        """
        if self.reps_note and self.reps_min is None:
            return self.reps_note
        if self.reps_min == self.reps_max:
            return str(self.reps_min)
        if self.reps_max is None:
            return f"{self.reps_min}+"
        return f"{self.reps_min}–{self.reps_max}"

    @property
    def exercise_label(self) -> str:
        """
        Alphabetic label: order_index 1 → "A", 2 → "B", 3 → "C".
        This is a presentation concern computed here so it is available
        wherever the entity is used — not just in the route layer.
        """
        return chr(64 + self.order_index)   # chr(65) == "A"


# ── Log (RED — client fills) ──────────────────────────────────────────────────

@dataclass(frozen=True)
class WorkoutLog:
    """
    The client's actual performance record for one exercise in one session.
    This is the RED side of the spreadsheet.
    Maps to `workout_logs`.

    Design choice — prescription_id nullable:
        When prescription_id is set, the log is linked to a coach prescription.
        When None, the client is self-logging a custom exercise (orphan mode).
        The __post_init__ constraint enforces that self-logged entries provide
        exercise_name directly.

    Design choice — tonnage_kg as @property:
        tonnage = sets × reps × load. In the database this is a
        GENERATED ALWAYS AS column (cannot get out of sync). In the domain
        entity, it is a @property (also cannot get out of sync, computed
        from the same source values). This mirrors the GENERATED column
        semantics in pure Python.

    Design choice — logged_at is date, not datetime:
        A client logs "I trained on April 8th", not "at 14:32:17".
        Using date reflects the actual semantics, avoids timezone edge
        cases, and makes grouping by day/week/month trivially clean.
    """
    id:                 UUID
    prescription_id:    UUID | None
    client_id:          UUID
    exercise_name:      str | None     # required when prescription_id is None
    logged_at:          date
    actual_sets:        int
    actual_reps:        int            # reps per set (not total)
    actual_load_kg:     Decimal | None # None for bodyweight exercises
    actual_rpe:         Decimal | None # 1.0 – 10.0 in 0.5 increments
    readiness:          int | None     # 1–10, how fresh the client felt
    time_taken_seconds: int | None
    client_notes:       str | None
    video_url:          str | None     # Phase 2
    video_source:       VideoSource | None  # Phase 2
    created_at:         datetime

    def __post_init__(self) -> None:
        """
        Self-logged entries must carry exercise_name directly.
        Mirrors: CHECK (prescription_id IS NOT NULL OR exercise_name IS NOT NULL)
        """
        if self.prescription_id is None and self.exercise_name is None:
            raise ValueError(
                "WorkoutLog without a prescription_id must provide exercise_name. "
                "exercise_name is required for self-managed (orphan) workout logs."
            )

    @property
    def tonnage_kg(self) -> Decimal | None:
        """
        Total training volume for this exercise: sets × reps × load.
        Returns None for bodyweight exercises (actual_load_kg is None).

        Verified against spreadsheet data:
            4 sets × 6 reps × 70 kg = 1,680 kg  ✓
            3 sets × 18 reps × 50 kg = 2,700 kg  ✓
        """
        if self.actual_load_kg is None:
            return None
        return (
            Decimal(self.actual_sets)
            * Decimal(self.actual_reps)
            * self.actual_load_kg
        )

    @property
    def is_self_logged(self) -> bool:
        """True when the client logged this independently (no prescription)."""
        return self.prescription_id is None
