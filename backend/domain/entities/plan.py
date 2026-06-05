"""
Cross-plan domain entities: PlanVersion, PlanComment, PlanActivityLog.

These three entities use a polymorphic (plan_type, plan_id) reference rather
than separate FK columns for workout and diet plans.

Design choice — polymorphic reference over two nullable FKs:
    Two nullable FKs (workout_program_id, diet_plan_id) would mean one
    is always NULL and queries always filter on the non-null one. The
    discriminator pair (plan_type, plan_id) is cleaner and extensible:
    adding a new plan type (e.g., supplement_plan) requires no schema
    change to these three tables.

Design choice — plan_id is NOT a FK constraint:
    In the database, plan_id is a UUID column with no foreign key constraint.
    This is intentional: version history, comments, and activity logs must
    survive even if a plan is hard-deleted by a DBA. Soft referential integrity
    is enforced at the application layer (services always check the plan exists
    before writing to these tables).
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.entities.enums import ActivityAction, PlanType


@dataclass(frozen=True)
class PlanVersion:
    """
    An immutable JSONB snapshot of a plan at a point in time.
    Maps to `plan_versions`. Append-only — never updated or deleted.

    Design choice — JSONB snapshot over row-level change tracking:
        Row-level tracking records each field change individually.
        Reconstructing a plan at a past point requires joining many
        change rows. A JSONB snapshot is self-contained: restoring a
        version is one read + one write, no join.

    Design choice — snapshot as dict, not a typed object:
        The snapshot captures the plan at write time. Its schema may
        evolve between sprints. Using dict keeps the entity decoupled
        from the current plan schema — old snapshots remain valid even
        after the live plan structure changes.
    """
    id:            UUID
    plan_type:     PlanType
    plan_id:       UUID
    snapshot:      dict[str, object]      # full plan state as JSONB blob
    modified_by:   UUID
    modified_at:   datetime
    change_reason: str | None         # mandatory for super_admin, optional for coaches


@dataclass(frozen=True)
class PlanComment:
    """
    A comment left by a staff member on a plan.
    Maps to `plan_comments`. Soft-deleted, never hard-deleted.

    Design choice — is_deleted not a physical delete:
        A coach's comment is part of the coaching record. A client may have
        acted on it ("coach said to drop the weight — this is why my load
        changed"). Permanent deletion would destroy that context. is_deleted
        replaces the body with "[comment removed]" in API responses while
        preserving the row and author_id for audit.
    """
    id:         UUID
    plan_type:  PlanType
    plan_id:    UUID
    author_id:  UUID
    body:       str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    @property
    def display_body(self) -> str:
        """Body to show in the UI — tombstone text if soft-deleted."""
        return "[comment removed]" if self.is_deleted else self.body


@dataclass(frozen=True)
class PlanActivityLog:
    """
    An immutable event record in the plan's activity feed.
    Maps to `plan_activity_log`. Append-only — never updated or deleted.

    Powers the cross-domain visibility feed: when a nutritionist updates
    a diet plan, the fitness trainer assigned to the same client sees
    the event in their dashboard.

    Design choice — occurred_at not created_at:
        occurred_at names the semantic reality: the event occurred at
        this time. created_at would name the row insertion time (same
        in practice, but semantically wrong for an event log).

    Design choice — metadata as dict | None:
        Each action type carries different context. A dict allows
        action-specific payloads without nullable columns per action.
        entry_added: {"exercise_name": "Deadlift", "sets": 3}
        override_applied: {"reason": "correcting data entry error"}
        commented: {"comment_id": "uuid", "preview": "Drop the weight..."}
    """
    id:          UUID
    plan_type:   PlanType
    plan_id:     UUID
    actor_id:    UUID
    action:      ActivityAction
    metadata:    dict[str, object] | None
    occurred_at: datetime
