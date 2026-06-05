"""
AssignmentService — the single point of enforcement for coaching assignment rules.

This is the most architecturally significant service in Sprint 3.
The coaching conflict matrix lives here and nowhere else:

    master_coach + fitness_trainer  → CONFLICT ✗
    master_coach + nutritionist     → CONFLICT ✗
    fitness_trainer + nutritionist  → ALLOWED  ✓

Design choice — standalone service, not embedded in SuperAdminService:
    The conflict rule "a client cannot have both a master coach and a fitness
    trainer" is a cross-row, cross-table business rule. It belongs to no single
    coaching role's service. If this logic lived in MasterCoachService, it would
    need to know about fitness_trainer assignments. If it lived in both, it would
    be duplicated and could diverge. AssignmentService owns it exclusively.
    When the conflict rules change, there is one file to change.

Design choice — assignment history, never hard delete:
    Ending an assignment calls the repository's end_assignment() method, which
    sets ended_at and ended_reason on the row. No row is ever deleted.
    Every coaching relationship the client has ever had is permanently preserved.
    The partial unique indexes in the schema enforce one-active-per-role:

        UNIQUE (client_id) WHERE ended_at IS NULL AND staff_role = 'fitness_trainer'
        UNIQUE (client_id) WHERE ended_at IS NULL AND staff_role = 'nutritionist'
        UNIQUE (client_id) WHERE ended_at IS NULL AND staff_role = 'master_coach'

    The service does the cross-role check. The indexes are the DB-level safety net.

Design choice — replacing a same-role assignment does not raise:
    If a client already has trainer A and a super admin assigns trainer B,
    AssignmentService closes trainer A's assignment and opens trainer B's.
    This is the expected "switch coaches" workflow. Only cross-role violations
    (master coach conflicting with trainer/nutritionist) are errors.

Design choice — SelfAssignmentError:
    A staff member assigning themselves to a client (as a client) is always
    rejected. This is a structural impossibility in real coaching contexts and
    its presence as an explicit error prevents subtle data integrity issues
    where a staff member's own plans might be confused with client assignments.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from core.exceptions import (
    AssignmentConflictError,
    ForbiddenError,
    NotFoundError,
    SelfAssignmentError,
    ValidationError,
)
from domain.entities.assignment import ClientStaffAssignment
from domain.entities.enums import StaffRole, UserRole
from domain.interfaces.repositories import (
    IClientStaffAssignmentRepository,
    IUserRepository,
)
from domain.interfaces.services import IAssignmentService


class AssignmentService(IAssignmentService):
    def __init__(
        self,
        assignment_repo: IClientStaffAssignmentRepository,
        user_repo: IUserRepository,
    ) -> None:
        self._assignment_repo = assignment_repo
        self._user_repo = user_repo

    async def assign_staff(
        self,
        client_id: UUID,
        staff_id: UUID,
        staff_role: StaffRole,
        assigned_by: UUID,
    ) -> ClientStaffAssignment:
        """
        Create a new coaching assignment after validating all business rules.

        Validation order:
        1. Self-assignment guard.
        2. Client user exists and has role=client.
        3. Staff user exists and their role matches the claimed staff_role.
        4. Cross-role conflict check against currently active assignments.
        5. Close any existing same-role assignment for this client.
        6. Persist and return the new assignment.
        """
        # ── 1. Self-assignment guard ──────────────────────────────────────────
        if client_id == staff_id:
            raise SelfAssignmentError(
                "A user cannot be assigned to themselves as a coaching client"
            )

        # ── 2. Validate client ────────────────────────────────────────────────
        client = await self._user_repo.get_by_id(client_id)
        if client is None:
            raise NotFoundError(f"Client {client_id} not found")
        if client.role != UserRole.CLIENT:
            raise ValidationError(
                f"User {client_id} has role '{client.role}' — only users with "
                "role 'client' can be assigned coaching staff"
            )

        # ── 3. Validate staff ─────────────────────────────────────────────────
        staff = await self._user_repo.get_by_id(staff_id)
        if staff is None:
            raise NotFoundError(f"Staff member {staff_id} not found")
        # Both str,Enum subclasses — string equality works because values match
        if staff.role.value != staff_role.value:
            raise ForbiddenError(
                f"User {staff_id} has role '{staff.role}' but was claimed as "
                f"'{staff_role}' — the claimed role does not match the user's role"
            )

        # ── 4. Cross-role conflict check ──────────────────────────────────────
        active = await self._assignment_repo.get_active_for_client(client_id)
        active_roles = {a.staff_role for a in active}

        if staff_role == StaffRole.MASTER_COACH:
            conflicting = active_roles & {
                StaffRole.FITNESS_TRAINER,
                StaffRole.NUTRITIONIST,
            }
            if conflicting:
                role_names = ", ".join(r.value for r in conflicting)
                raise AssignmentConflictError(
                    f"Cannot assign a master coach: client {client_id} already has "
                    f"active individual coaching staff ({role_names}). "
                    "Remove existing staff assignments before assigning a master coach."
                )

        if (
            staff_role in {StaffRole.FITNESS_TRAINER, StaffRole.NUTRITIONIST}
            and StaffRole.MASTER_COACH in active_roles
        ):
            raise AssignmentConflictError(
                f"Cannot assign a {staff_role.value}: client {client_id} already "
                "has an active master coach. Remove the master coach first, or "
                "assign a master coach instead of individual coaching staff."
            )

        # ── 5. Close existing same-role assignment if present ─────────────────
        existing_same_role = next(
            (a for a in active if a.staff_role == staff_role), None
        )
        if existing_same_role is not None:
            await self._assignment_repo.end_assignment(
                assignment_id=existing_same_role.id,
                ended_at=datetime.now(tz=UTC),
                ended_reason="replaced",
            )

        # ── 6. Persist new assignment ─────────────────────────────────────────
        new_assignment = ClientStaffAssignment(
            id=uuid4(),
            client_id=client_id,
            staff_id=staff_id,
            staff_role=staff_role,
            assigned_at=datetime.now(tz=UTC),
            ended_at=None,
            ended_reason=None,
            assigned_by=assigned_by,
        )
        return await self._assignment_repo.save(new_assignment)

    async def end_assignment(
        self,
        assignment_id: UUID,
        ended_reason: str,
    ) -> None:
        """
        Close an active assignment by assignment_id.
        The repository records ended_at and ended_reason on the row.
        The row is never deleted — the coaching history is permanent.
        """
        await self._assignment_repo.end_assignment(
            assignment_id=assignment_id,
            ended_at=datetime.now(tz=UTC),
            ended_reason=ended_reason,
        )

    # ── Read helpers (not on IAssignmentService — called by SuperAdminService) ─

    async def get_active_for_client(
        self, client_id: UUID
    ) -> list[ClientStaffAssignment]:
        """Return all currently active assignments for a client."""
        return await self._assignment_repo.get_active_for_client(client_id)
