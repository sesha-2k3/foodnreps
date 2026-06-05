"""
WorkoutFactory — the single construction point for all workout hierarchy entities.

Design choice — factory enforces construction-time invariants:
    Every business rule that applies at the moment an entity comes into
    existence lives here. Without the factory, those rules would need to
    be duplicated in every service that creates a programme, week, day,
    or prescription. With it, every service calls the factory and trusts
    the result — an invalid entity cannot be produced by calling these methods.

    The factory raises ValidationError (our domain exception) rather than
    letting the entity's __post_init__ raise a raw ValueError. This means
    construction failures map cleanly to HTTP 422 in Sprint 4 without
    the presentation layer needing to catch ValueError.

Design choice — factory owns uuid4() calls:
    Services never call uuid4() directly when creating entities. The factory
    generates the id, which keeps entity construction deterministic from the
    service's perspective and makes tests simpler (pass inputs, verify fields).

Design choice — dataclasses.replace() for deactivation helpers:
    Deactivating a plan is a "create a modified copy" operation, not a
    mutation. dataclasses.replace() is the standard tool for this pattern
    with frozen dataclasses. The deactivate_* methods live on the factory
    (not on the entity) because they are construction-adjacent operations
    that produce new entity instances with specific field changes.
"""

import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from core.exceptions import ValidationError
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutPrescription,
    WorkoutProgram,
)


class WorkoutFactory:
    """Creates and transforms workout hierarchy domain entities."""

    # ── Programme ─────────────────────────────────────────────────────────────

    def create_program(
        self,
        owner_id: UUID,
        created_by_id: UUID,
        name: str,
        is_personal: bool = False,
        is_template: bool = False,
        coach_notes: str | None = None,
    ) -> WorkoutProgram:
        """
        Create a new WorkoutProgram entity.

        Validates:
        - name is not blank after stripping whitespace.

        Defaults:
        - is_active=True   — new programmes are immediately active.
        - version=1        — starting version for optimistic locking.
        - last_modified_by/at/override_reason all None — not yet modified.
        """
        stripped = name.strip()
        if not stripped:
            raise ValidationError("Programme name cannot be empty")
        now = datetime.now(tz=UTC)
        return WorkoutProgram(
            id=uuid4(),
            owner_id=owner_id,
            created_by_id=created_by_id,
            name=stripped,
            is_active=True,
            is_personal=is_personal,
            is_template=is_template,
            coach_notes=coach_notes,
            version=1,
            last_modified_by=None,
            last_modified_at=None,
            override_reason=None,
            created_at=now,
            updated_at=now,
        )

    def deactivate_program(self, program: WorkoutProgram) -> WorkoutProgram:
        """
        Return a deactivated copy of an existing programme.

        Called before creating a new active programme for the same owner.
        The partial unique index on the schema (WHERE is_active=true AND
        is_template=false) enforces one-active-per-owner at the DB level.
        This deactivation is the service-layer enforcement that runs first.
        """
        return dataclasses.replace(
            program,
            is_active=False,
            updated_at=datetime.now(tz=UTC),
        )

    # ── Weeks ─────────────────────────────────────────────────────────────────

    def create_week(
        self,
        program_id: UUID,
        week_number: int,
        label: str = "Week",
        notes: str | None = None,
    ) -> ProgramWeek:
        """
        Create a ProgramWeek entity.

        Validates:
        - week_number must be >= 1. Week 0 is not a real training week.

        Label defaults to "Week" if blank — still human-readable and safe
        to display. Coaches almost always provide a meaningful label
        ("Deload Week", "Peak Week") but the default prevents an empty
        label reaching the frontend.
        """
        if week_number < 1:
            raise ValidationError(
                f"week_number must be a positive integer, got {week_number}"
            )
        stripped = label.strip()
        return ProgramWeek(
            id=uuid4(),
            program_id=program_id,
            week_number=week_number,
            label=stripped or "Week",
            notes=notes,
            created_at=datetime.now(tz=UTC),
        )

    # ── Days ──────────────────────────────────────────────────────────────────

    def create_day(
        self,
        week_id: UUID,
        day_number: int,
        label: str = "Day",
        notes: str | None = None,
    ) -> ProgramDay:
        """
        Create a ProgramDay entity.

        Validates:
        - day_number must be >= 1. Day 0 is not a real training day.

        Label defaults to "Day" if blank.
        """
        if day_number < 1:
            raise ValidationError(
                f"day_number must be a positive integer, got {day_number}"
            )
        stripped = label.strip()
        return ProgramDay(
            id=uuid4(),
            week_id=week_id,
            day_number=day_number,
            label=stripped or "Day",
            notes=notes,
            created_at=datetime.now(tz=UTC),
        )

    # ── Prescriptions ─────────────────────────────────────────────────────────

    def create_prescription(  # noqa: PLR0913
        self,
        day_id: UUID,
        order_index: int,
        exercise_name: str,
        warmup_sets: int | None = None,
        working_sets: int | None = None,
        reps_min: int | None = None,
        reps_max: int | None = None,
        reps_note: str | None = None,
        prescribed_load_kg: Decimal | None = None,
        prescribed_load_text: str | None = None,
        prescribed_rpe: Decimal | None = None,
        prescribed_rir: int | None = None,
        rest_seconds: int | None = None,
        instructions: str | None = None,
    ) -> WorkoutPrescription:
        """
        Create a WorkoutPrescription entity (BLUE side of the spreadsheet).

        Validates (mirrors DB CHECK constraints so failures are domain errors,
        not raw DB constraint violations bubbling to the presentation layer):
        - order_index >= 1 (maps to exercise label A, B, C... via chr(64 + idx))
        - exercise_name is not blank
        - at least reps_min or reps_note is provided
          (mirrors: CHECK (reps_min IS NOT NULL OR reps_note IS NOT NULL))
        - reps_max >= reps_min when both provided
        - prescribed_rpe in [1.0, 10.0] when provided
        - warmup_sets >= 0 when provided
        - working_sets >= 1 when provided
        - rest_seconds >= 0 when provided

        These validations run before the WorkoutPrescription constructor.
        The entity's __post_init__ checks the reps constraint again as a
        second line of defence; the factory catches it first with a clean
        ValidationError message.
        """
        if order_index < 1:
            raise ValidationError(
                f"order_index must be a positive integer, got {order_index}"
            )
        stripped_name = exercise_name.strip()
        if not stripped_name:
            raise ValidationError("Exercise name cannot be empty")
        if reps_min is None and reps_note is None:
            raise ValidationError(
                "Either reps_min or reps_note must be provided. "
                "Use reps_min for numeric prescriptions (e.g. 6–8 reps) or "
                "reps_note for open-ended prescriptions (e.g. 'max reps')."
            )
        if reps_max is not None and reps_min is not None and reps_max < reps_min:
            raise ValidationError(
                f"reps_max ({reps_max}) cannot be less than reps_min ({reps_min})"
            )
        if prescribed_rpe is not None and not (
            Decimal("1.0") <= prescribed_rpe <= Decimal("10.0")
        ):
            raise ValidationError(
                f"prescribed_rpe must be between 1.0 and 10.0, got {prescribed_rpe}"
            )
        if warmup_sets is not None and warmup_sets < 0:
            raise ValidationError("warmup_sets cannot be negative")
        if working_sets is not None and working_sets < 1:
            raise ValidationError("working_sets must be at least 1 when provided")
        if rest_seconds is not None and rest_seconds < 0:
            raise ValidationError("rest_seconds cannot be negative")

        now = datetime.now(tz=UTC)
        return WorkoutPrescription(
            id=uuid4(),
            day_id=day_id,
            order_index=order_index,
            exercise_name=stripped_name,
            warmup_sets=warmup_sets,
            working_sets=working_sets,
            reps_min=reps_min,
            reps_max=reps_max,
            reps_note=reps_note,
            prescribed_load_kg=prescribed_load_kg,
            prescribed_load_text=prescribed_load_text,
            prescribed_rpe=prescribed_rpe,
            prescribed_rir=prescribed_rir,
            rest_seconds=rest_seconds,
            instructions=instructions,
            created_at=now,
            updated_at=now,
        )
