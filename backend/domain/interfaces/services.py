"""
Service interfaces — abstract contracts for the application layer.

Design choice — why service interfaces in the domain layer:
    Service interfaces here enable the Strategy pattern for role-based
    access and make services independently mockable in tests. A route
    handler that depends on IWorkoutService can be tested with a mock
    without building the full concrete service.

    These interfaces define the WHAT (method signatures, input types,
    return types). The application layer defines the HOW (business logic).

Design choice — minimal surface area:
    Only methods that a caller outside the service actually needs are
    declared here. Internal helper methods stay private to the
    implementation. This keeps the interface stable even as the
    implementation evolves.

Sprint 3 correction — IAuthService.refresh return type:
    The original interface declared refresh() -> str (access token only).
    Sprint 3 implementation revealed that the route handler in Sprint 4
    also needs to set a new httpOnly refresh token cookie on every refresh
    call. Both tokens must come from the service. The correct return type
    is tuple[str, str] = (new_access_token_jwt, new_refresh_token_jwt),
    matching the login() signature. Updated here before Sprint 4 is built.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID

from domain.entities.assignment import ClientStaffAssignment
from domain.entities.diet import DietEntry, DietPlan
from domain.entities.enums import StaffRole
from domain.entities.plan import PlanComment, PlanVersion
from domain.entities.profile import BodyMetric, IntakeProfile
from domain.entities.user import User
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutLog,
    WorkoutPrescription,
    WorkoutProgram,
)


# ── Auth ──────────────────────────────────────────────────────────────────────

class IAuthService(ABC):

    @abstractmethod
    async def login(
        self, email: str, password: str
    ) -> tuple[str, str]:
        """
        Verify credentials and return (access_token_jwt, refresh_token_jwt).
        Raises UnauthorizedError on invalid credentials.
        Raises InactiveUserError if the account is deactivated.
        """
        ...

    @abstractmethod
    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """
        Validate the refresh token, rotate it, and return
        (new_access_token_jwt, new_refresh_token_jwt).

        Sprint 3 correction: original interface declared -> str (access token
        only). The Sprint 4 route handler also needs the new refresh token to
        set as an httpOnly cookie. Both tokens are returned.

        Raises UnauthorizedError if the token is invalid or revoked.
        """
        ...

    @abstractmethod
    async def logout(self, refresh_token: str) -> None:
        """Revoke the refresh token immediately. Idempotent."""
        ...


# ── Assignment ────────────────────────────────────────────────────────────────

class IAssignmentService(ABC):

    @abstractmethod
    async def assign_staff(
        self,
        client_id: UUID,
        staff_id: UUID,
        staff_role: StaffRole,
        assigned_by: UUID,
    ) -> ClientStaffAssignment:
        """
        Assign a staff member to a client.
        Enforces the conflict matrix:
        - master_coach conflicts with any existing fitness_trainer or nutritionist
        - fitness_trainer conflicts with any existing master_coach
        - nutritionist conflicts with any existing master_coach
        Raises AssignmentConflictError on violations.
        Raises SelfAssignmentError if client_id == staff_id.
        """
        ...

    @abstractmethod
    async def end_assignment(
        self,
        assignment_id: UUID,
        ended_reason: str,
    ) -> None:
        """
        Close an active assignment. Called only by SuperAdminService.
        Raises NotFoundError if assignment_id does not exist.
        """
        ...


# ── Personal plans (all roles) ────────────────────────────────────────────────

class IPersonalPlanService(ABC):
    """
    Manages personal workout and diet plans for any authenticated user.
    Shared by all roles — every user can have their own plans.
    """

    @abstractmethod
    async def get_personal_workout(
        self, owner_id: UUID
    ) -> WorkoutProgram | None: ...

    @abstractmethod
    async def get_personal_diet(
        self, owner_id: UUID
    ) -> DietPlan | None: ...

    @abstractmethod
    async def create_personal_workout(
        self, owner_id: UUID, name: str
    ) -> WorkoutProgram: ...

    @abstractmethod
    async def create_personal_diet(
        self, owner_id: UUID, name: str
    ) -> DietPlan: ...


# ── Client ────────────────────────────────────────────────────────────────────

class IClientService(ABC):
    """Read-only service for clients viewing their assigned plans."""

    @abstractmethod
    async def get_assigned_workout(
        self, client_id: UUID
    ) -> WorkoutProgram | None: ...

    @abstractmethod
    async def get_assigned_diet(
        self, client_id: UUID
    ) -> DietPlan | None: ...

    @abstractmethod
    async def log_workout(
        self,
        client_id: UUID,
        prescription_id: UUID | None,
        exercise_name: str | None,
        actual_sets: int,
        actual_reps: int,
        actual_load_kg: Decimal | None,
        actual_rpe: Decimal | None,
        readiness: int | None,
        time_taken_seconds: int | None,
        client_notes: str | None,
    ) -> WorkoutLog: ...


# ── Workout (coach-facing) ────────────────────────────────────────────────────

class IWorkoutService(ABC):
    """
    Manages workout programmes on behalf of coaching staff.
    Implemented by FitnessTrainerService and MasterCoachService.
    """

    @abstractmethod
    async def create_programme(
        self,
        owner_id: UUID,
        created_by_id: UUID,
        name: str,
        is_personal: bool = False,
    ) -> WorkoutProgram: ...

    @abstractmethod
    async def add_week(
        self,
        program_id: UUID,
        week_number: int,
        label: str,
    ) -> ProgramWeek: ...

    @abstractmethod
    async def add_day(
        self,
        week_id: UUID,
        day_number: int,
        label: str,
    ) -> ProgramDay: ...

    @abstractmethod
    async def add_prescription(
        self,
        day_id: UUID,
        order_index: int,
        exercise_name: str,
        **kwargs: object,
    ) -> WorkoutPrescription: ...

    @abstractmethod
    async def get_full_programme(
        self, program_id: UUID
    ) -> WorkoutProgram | None: ...


# ── Diet (coach-facing) ───────────────────────────────────────────────────────

class IDietService(ABC):
    """
    Manages diet plans on behalf of coaching staff.
    Implemented by NutritionistService and MasterCoachService.
    """

    @abstractmethod
    async def create_plan(
        self,
        owner_id: UUID,
        created_by_id: UUID,
        name: str,
        is_personal: bool = False,
    ) -> DietPlan: ...

    @abstractmethod
    async def add_entry(
        self,
        plan_id: UUID,
        food_name: str,
        calories: Decimal,
        protein_g: Decimal,
        fat_g: Decimal,
        carbs_g: Decimal,
        order_index: int,
    ) -> DietEntry: ...


# ── Super admin ───────────────────────────────────────────────────────────────

class ISuperAdminService(ABC):

    @abstractmethod
    async def create_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: str,
    ) -> User: ...

    @abstractmethod
    async def deactivate_user(self, user_id: UUID) -> None: ...

    @abstractmethod
    async def override_workout_programme(
        self,
        program_id: UUID,
        override_reason: str,
        admin_id: UUID,
    ) -> WorkoutProgram: ...
