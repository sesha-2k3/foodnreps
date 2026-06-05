"""
IntakeProfile and BodyMetric domain entities.

These two entities capture the client's physical context — who they are
before a plan is written, and how they change over time.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from domain.entities.enums import ExperienceLevel, FitnessGoal


@dataclass(frozen=True)
class IntakeProfile:
    """
    A client's coaching intake form.
    One per client, updated in place (not versioned).
    Maps to the `intake_profiles` table.

    Design choice — injuries and equipment as tuple[str, ...]:
        The schema stores these as PostgreSQL TEXT[] arrays. In the domain
        entity, we use tuple (not list) because the dataclass is frozen=True.
        A frozen dataclass prevents attribute reassignment but does NOT prevent
        mutating a mutable list object. Using tuple enforces true immutability.

        The repository translates between tuple and list at the storage boundary.
        Pydantic schemas in Sprint 4 translate tuple back to list for JSON
        responses (JSON arrays).

    Design choice — target/current weight are intake-time snapshots only:
        Ongoing weight tracking is in BodyMetric. These two fields are what
        the client reported at intake — not live values.
    """

    id: UUID
    client_id: UUID
    fitness_goal: FitnessGoal
    experience_level: ExperienceLevel
    injuries: tuple[str, ...]  # e.g. ("lower_back", "left_knee")
    equipment: tuple[str, ...]  # e.g. ("barbell", "pull_up_bar")
    dietary_notes: str | None
    target_weight_kg: Decimal | None
    current_weight_kg: Decimal | None
    completed_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class BodyMetric:
    """
    A single body measurement event for any user.
    Append-only time series — rows are never updated.
    Maps to the `body_metrics` table.

    Design choice — recorded_by separate from user_id:
        user_id answers "whose body?", recorded_by answers "who logged this?"
        When recorded_by == user_id, the client self-logged (home scale).
        When recorded_by != user_id, a coach logged it (gym assessment, DEXA).
        This distinction matters for data quality assessment.

    Design choice — __post_init__ enforces the at-least-one constraint:
        The database enforces this via a CHECK constraint. The domain entity
        enforces it here so the violation is caught before any DB call is
        made, with a clear domain error rather than a DB constraint violation.
    """

    id: UUID
    user_id: UUID
    recorded_by: UUID
    recorded_at: datetime
    weight_kg: Decimal | None
    body_fat_pct: Decimal | None
    muscle_mass_kg: Decimal | None
    notes: str | None
    created_at: datetime

    def __post_init__(self) -> None:
        """
        At least one measurement must be present.
        Mirrors: CHECK (weight_kg IS NOT NULL OR body_fat_pct IS NOT NULL
                        OR muscle_mass_kg IS NOT NULL)
        """
        if all(
            v is None for v in (self.weight_kg, self.body_fat_pct, self.muscle_mass_kg)
        ):
            raise ValueError(
                "BodyMetric requires at least one measurement: "
                "weight_kg, body_fat_pct, or muscle_mass_kg."
            )
