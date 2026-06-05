"""
Repository interfaces — abstract contracts that infrastructure must implement.

Design choice — interfaces in the domain layer, not the infrastructure layer:
    The domain layer defines WHAT it needs. Infrastructure defines HOW to
    provide it. If IWorkoutProgramRepository lived in infrastructure, the
    domain would need to import from infrastructure to reference its own
    contract — reversing the dependency direction and breaking Clean Architecture.

    By placing interfaces here, the dependency arrow points correctly:
    Infrastructure → Domain (implements the contract).
    Application  → Domain (uses the contract).
    Neither ever imports from each other.

Design choice — async abstract methods:
    All repository methods are async because the infrastructure layer uses
    async SQLAlchemy. Defining them as async here enforces that all
    implementations are also async — a sync implementation would not satisfy
    the interface, and mypy would catch it.

Design choice — save() handles both create and update:
    A single save() method accepts an entity and either inserts or updates
    it based on whether the id exists. This keeps service code simple:
    services always call save() without knowing whether it's a new or
    existing entity. The repository implementation handles the distinction.
    For update operations, save() checks the version field for optimistic locking.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from domain.entities.assignment import ClientStaffAssignment
from domain.entities.diet import DietEntry, DietPlan
from domain.entities.enums import PlanType, StaffRole
from domain.entities.plan import PlanActivityLog, PlanComment, PlanVersion
from domain.entities.profile import BodyMetric, IntakeProfile
from domain.entities.user import RefreshToken, User
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutLog,
    WorkoutPrescription,
    WorkoutProgram,
)

# ── User ──────────────────────────────────────────────────────────────────────


class IUserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> User:
        """Create or update. Raises ConflictError on email duplicate."""
        ...

    @abstractmethod
    async def list_clients(self) -> list[User]:
        """All non-deleted users with role=client."""
        ...

    @abstractmethod
    async def list_staff(self) -> list[User]:
        """All non-deleted users with coaching roles."""
        ...


# ── Auth ──────────────────────────────────────────────────────────────────────


class IRefreshTokenRepository(ABC):
    @abstractmethod
    async def get_by_token_id(self, token_id: UUID) -> RefreshToken | None: ...

    @abstractmethod
    async def save(self, token: RefreshToken) -> RefreshToken: ...

    @abstractmethod
    async def revoke(self, token_id: UUID, revoked_at: datetime) -> None:
        """Mark one token as revoked."""
        ...

    @abstractmethod
    async def revoke_all_for_user(self, user_id: UUID, revoked_at: datetime) -> None:
        """
        Revoke every active token for a user.
        Called on password change and account deactivation.
        """
        ...


# ── Assignment ────────────────────────────────────────────────────────────────


class IClientStaffAssignmentRepository(ABC):
    @abstractmethod
    async def get_active_for_client(
        self, client_id: UUID
    ) -> list[ClientStaffAssignment]:
        """All currently active (ended_at IS NULL) assignments for a client."""
        ...

    @abstractmethod
    async def get_active_by_role_for_client(
        self, client_id: UUID, staff_role: StaffRole
    ) -> ClientStaffAssignment | None:
        """The single active assignment of a specific role for a client."""
        ...

    @abstractmethod
    async def get_active_for_staff(self, staff_id: UUID) -> list[ClientStaffAssignment]:
        """All clients currently assigned to a staff member."""
        ...

    @abstractmethod
    async def get_history_for_client(
        self, client_id: UUID
    ) -> list[ClientStaffAssignment]:
        """Full assignment history including ended assignments."""
        ...

    @abstractmethod
    async def save(self, assignment: ClientStaffAssignment) -> ClientStaffAssignment:
        """Insert a new assignment. Assignments are never updated."""
        ...

    @abstractmethod
    async def end_assignment(
        self,
        assignment_id: UUID,
        ended_at: datetime,
        ended_reason: str,
    ) -> None:
        """Close an active assignment by setting ended_at and ended_reason."""
        ...


# ── Profile ───────────────────────────────────────────────────────────────────


class IIntakeProfileRepository(ABC):
    @abstractmethod
    async def get_by_client_id(self, client_id: UUID) -> IntakeProfile | None: ...

    @abstractmethod
    async def save(self, profile: IntakeProfile) -> IntakeProfile:
        """Create or update (upsert on client_id)."""
        ...


class IBodyMetricRepository(ABC):
    @abstractmethod
    async def list_for_user(self, user_id: UUID, limit: int = 50) -> list[BodyMetric]:
        """Most recent measurements first."""
        ...

    @abstractmethod
    async def save(self, metric: BodyMetric) -> BodyMetric:
        """Always inserts — body metrics are append-only."""
        ...


# ── Workout programme ─────────────────────────────────────────────────────────


class IWorkoutProgramRepository(ABC):
    @abstractmethod
    async def get_by_id(self, program_id: UUID) -> WorkoutProgram | None: ...

    @abstractmethod
    async def get_active_by_owner(self, owner_id: UUID) -> WorkoutProgram | None:
        """The single active non-template programme for an owner."""
        ...

    @abstractmethod
    async def list_by_owner(self, owner_id: UUID) -> list[WorkoutProgram]:
        """All programmes (active, inactive, templates) for an owner."""
        ...

    @abstractmethod
    async def save(self, program: WorkoutProgram) -> WorkoutProgram:
        """
        Create or update. On update, checks program.version matches DB.
        Raises PlanVersionConflictError if version has changed (optimistic lock).
        """
        ...


class IProgramWeekRepository(ABC):
    @abstractmethod
    async def list_by_program(self, program_id: UUID) -> list[ProgramWeek]:
        """All weeks for a programme, ordered by week_number."""
        ...

    @abstractmethod
    async def save(self, week: ProgramWeek) -> ProgramWeek: ...

    @abstractmethod
    async def delete(self, week_id: UUID) -> None: ...


class IProgramDayRepository(ABC):
    @abstractmethod
    async def list_by_week(self, week_id: UUID) -> list[ProgramDay]:
        """All days for a week, ordered by day_number."""
        ...

    @abstractmethod
    async def save(self, day: ProgramDay) -> ProgramDay: ...

    @abstractmethod
    async def delete(self, day_id: UUID) -> None: ...


class IWorkoutPrescriptionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, prescription_id: UUID) -> WorkoutPrescription | None: ...

    @abstractmethod
    async def list_by_day(self, day_id: UUID) -> list[WorkoutPrescription]:
        """All prescriptions for a day, ordered by order_index."""
        ...

    @abstractmethod
    async def save(self, prescription: WorkoutPrescription) -> WorkoutPrescription: ...

    @abstractmethod
    async def delete(self, prescription_id: UUID) -> None: ...


class IWorkoutLogRepository(ABC):
    @abstractmethod
    async def list_by_client(
        self, client_id: UUID, limit: int = 50
    ) -> list[WorkoutLog]:
        """Most recent logs first."""
        ...

    @abstractmethod
    async def list_by_prescription(self, prescription_id: UUID) -> list[WorkoutLog]:
        """All logs for a specific prescription (coach review view)."""
        ...

    @abstractmethod
    async def save(self, log: WorkoutLog) -> WorkoutLog:
        """Always inserts — workout logs are append-only."""
        ...


# ── Diet plan ─────────────────────────────────────────────────────────────────


class IDietPlanRepository(ABC):
    @abstractmethod
    async def get_by_id(self, plan_id: UUID) -> DietPlan | None: ...

    @abstractmethod
    async def get_active_by_owner(self, owner_id: UUID) -> DietPlan | None: ...

    @abstractmethod
    async def list_by_owner(self, owner_id: UUID) -> list[DietPlan]: ...

    @abstractmethod
    async def save(self, plan: DietPlan) -> DietPlan:
        """
        Create or update. Raises PlanVersionConflictError on version mismatch.
        """
        ...


class IDietEntryRepository(ABC):
    @abstractmethod
    async def get_by_id(self, entry_id: UUID) -> DietEntry | None: ...

    @abstractmethod
    async def list_by_plan(self, plan_id: UUID) -> list[DietEntry]:
        """All entries for a plan, ordered by order_index."""
        ...

    @abstractmethod
    async def save(self, entry: DietEntry) -> DietEntry: ...

    @abstractmethod
    async def delete(self, entry_id: UUID) -> None: ...


# ── Plan cross-cutting ────────────────────────────────────────────────────────


class IPlanVersionRepository(ABC):
    @abstractmethod
    async def list_by_plan(
        self, plan_type: PlanType, plan_id: UUID
    ) -> list[PlanVersion]:
        """All versions for a plan, most recent first."""
        ...

    @abstractmethod
    async def save(self, version: PlanVersion) -> PlanVersion:
        """Always inserts — plan versions are append-only."""
        ...


class IPlanCommentRepository(ABC):
    @abstractmethod
    async def list_by_plan(
        self, plan_type: PlanType, plan_id: UUID
    ) -> list[PlanComment]:
        """Non-deleted comments, most recent first."""
        ...

    @abstractmethod
    async def save(self, comment: PlanComment) -> PlanComment: ...

    @abstractmethod
    async def soft_delete(self, comment_id: UUID) -> None:
        """Set is_deleted=True. Physical rows are never deleted."""
        ...


class IPlanActivityLogRepository(ABC):
    @abstractmethod
    async def list_by_plan(
        self,
        plan_type: PlanType,
        plan_id: UUID,
        limit: int = 50,
    ) -> list[PlanActivityLog]:
        """Most recent events first."""
        ...

    @abstractmethod
    async def save(self, log: PlanActivityLog) -> PlanActivityLog:
        """Always inserts — activity log is append-only."""
        ...
