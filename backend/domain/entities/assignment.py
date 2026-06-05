"""
ClientStaffAssignment domain entity.

This entity models the coaching relationship between a client and a staff member.
It is the most business-critical entity in the system — the conflict rules
(one active master coach, no master coach + trainer simultaneously) all derive
from querying the active rows in this entity's collection.

Design choice — assignment history, never hard delete:
    When a coaching relationship ends, ended_at is set. The row is never
    deleted. This means the full history of who coached whom is always
    queryable. AssignmentService enforces this: it never deletes rows,
    only closes them by setting ended_at.

Design choice — is_active as a @property, not a column:
    is_active is a derived fact: ended_at IS NULL. Storing it as a
    separate boolean would require keeping it in sync with ended_at
    (an update anomaly waiting to happen). The @property computes it
    from the authoritative source — ended_at.

    In the database, the partial unique indexes use IS NULL directly:
        WHERE ended_at IS NULL AND staff_role = 'fitness_trainer'
    This is consistent with the property logic.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from domain.entities.enums import StaffRole


@dataclass(frozen=True)
class ClientStaffAssignment:
    """
    A coaching relationship between one client and one staff member.
    Maps to the `client_staff_assignments` table.
    """

    id: UUID
    client_id: UUID
    staff_id: UUID
    staff_role: StaffRole
    assigned_at: datetime
    ended_at: datetime | None
    ended_reason: str | None
    assigned_by: UUID  # always a super_admin user_id

    @property
    def is_active(self) -> bool:
        """
        True when the assignment is currently active.
        An assignment is active when ended_at has not been set.
        This mirrors the partial unique index condition: WHERE ended_at IS NULL.
        """
        return self.ended_at is None
