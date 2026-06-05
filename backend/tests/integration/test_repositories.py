"""
Repository integration tests.

These tests verify that:
1. ORM models map correctly to the database schema (columns, types, constraints).
2. Repository methods return correct domain entities.
3. Business rule constraints are enforced at the DB level (partial unique indexes).
4. The entity ↔ model translation is lossless (fields round-trip correctly).

Design choice — test against a real database, not mocks:
    Repository implementations contain SQL queries and ORM mappings.
    The only thing worth verifying is whether they correctly read and write
    to a real PostgreSQL instance. Mocking the DB would test SQLAlchemy's
    API, not our code. Every test here requires a running PostgreSQL.

Design choice — one assertion per concept, not one test per method:
    Tests are organised around business concepts ("a client can be saved and
    retrieved") not method signatures ("get_by_id returns User or None").
    This makes failures self-documenting.

Run with:
    make test-integration
    # or specifically:
    uv run pytest tests/integration/ -v
"""

import dataclasses
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from core.exceptions import PlanVersionConflictError
from tests.conftest import db_session
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.assignment import ClientStaffAssignment
from domain.entities.diet import DietEntry, DietPlan
from domain.entities.enums import (
    ExperienceLevel,
    FitnessGoal,
    PlanType,
    ActivityAction,
    StaffRole,
    UserRole,
)
from domain.entities.plan import PlanActivityLog, PlanVersion
from domain.entities.profile import BodyMetric, IntakeProfile
from domain.entities.user import User
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutLog,
    WorkoutPrescription,
    WorkoutProgram,
)
from infrastructure.repositories.assignment_repository import (
    ClientStaffAssignmentRepository,
)
from infrastructure.repositories.diet_repository import (
    DietEntryRepository,
    DietPlanRepository,
)
from infrastructure.repositories.plan_repository import (
    PlanActivityLogRepository,
    PlanVersionRepository,
)
from infrastructure.repositories.profile_repository import (
    BodyMetricRepository,
    IntakeProfileRepository,
)
from infrastructure.repositories.user_repository import UserRepository
from infrastructure.repositories.workout_repository import (
    ProgramDayRepository,
    ProgramWeekRepository,
    WorkoutLogRepository,
    WorkoutPrescriptionRepository,
    WorkoutProgramRepository,
)

NOW = datetime(2025, 4, 8, 12, 0, 0, tzinfo=timezone.utc)


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_user(role: UserRole = UserRole.CLIENT, email: str | None = None) -> User:
    return User(
        id=uuid4(),
        email=email or f"{uuid4()}@test.com",
        password_hash="$2b$12$hashed",
        full_name="Test User",
        role=role,
        is_active=True,
        is_deleted=False,
        deleted_at=None,
        created_at=NOW,
        updated_at=NOW,
    )


def make_workout_program(owner: User, created_by: User | None = None) -> WorkoutProgram:
    return WorkoutProgram(
        id=uuid4(),
        owner_id=owner.id,
        created_by_id=(created_by or owner).id,
        name="Test Programme",
        is_active=True,
        is_personal=(created_by is None),
        is_template=False,
        coach_notes=None,
        version=1,
        last_modified_by=None,
        last_modified_at=None,
        override_reason=None,
        created_at=NOW,
        updated_at=NOW,
    )


# ── UserRepository ────────────────────────────────────────────────────────────


class TestUserRepository:
    async def test_save_and_retrieve_by_id(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        user = make_user()

        saved = await repo.save(user)
        fetched = await repo.get_by_id(saved.id)

        assert fetched is not None
        assert fetched.id == user.id
        assert fetched.email == user.email
        assert fetched.role == UserRole.CLIENT

    async def test_get_by_email(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        user = make_user(email="coach@foodandreps.com")
        await repo.save(user)

        fetched = await repo.get_by_email("coach@foodandreps.com")
        assert fetched is not None
        assert fetched.id == user.id

    async def test_get_by_email_returns_none_for_unknown(
        self, db_session: AsyncSession
    ) -> None:
        repo = UserRepository(db_session)
        result = await repo.get_by_email("nobody@nowhere.com")
        assert result is None

    async def test_list_clients_excludes_staff(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        client = make_user(role=UserRole.CLIENT)
        trainer = make_user(role=UserRole.FITNESS_TRAINER)
        await repo.save(client)
        await repo.save(trainer)

        clients = await repo.list_clients()
        ids = [u.id for u in clients]
        assert client.id in ids
        assert trainer.id not in ids

    async def test_update_existing_user(self, db_session: AsyncSession) -> None:
        repo = UserRepository(db_session)
        user = make_user()
        await repo.save(user)

        import dataclasses

        updated = dataclasses.replace(user, full_name="Updated Name", updated_at=NOW)
        saved = await repo.save(updated)

        assert saved.full_name == "Updated Name"


# ── WorkoutProgramRepository ──────────────────────────────────────────────────


class TestWorkoutProgramRepository:
    async def test_save_and_retrieve(self, db_session: AsyncSession) -> None:
        user_repo = UserRepository(db_session)
        program_repo = WorkoutProgramRepository(db_session)

        owner = make_user()
        await user_repo.save(owner)

        program = make_workout_program(owner)
        saved = await program_repo.save(program)

        assert saved.id == program.id
        assert saved.name == "Test Programme"
        assert saved.version == 1

    async def test_get_active_by_owner(self, db_session: AsyncSession) -> None:
        user_repo = UserRepository(db_session)
        program_repo = WorkoutProgramRepository(db_session)

        owner = make_user()
        await user_repo.save(owner)
        program = make_workout_program(owner)
        await program_repo.save(program)

        active = await program_repo.get_active_by_owner(owner.id)
        assert active is not None
        assert active.id == program.id

    async def test_optimistic_lock_raises_on_version_mismatch(
        self,
        db_session: AsyncSession,  # noqa: F811
    ) -> None:
        from core.exceptions import PlanVersionConflictError  # noqa: F811

        user_repo = UserRepository(db_session)
        program_repo = WorkoutProgramRepository(db_session)

        owner = make_user()
        await user_repo.save(owner)
        program = make_workout_program(owner)

        # Save 1 — insert, DB has version=1
        await program_repo.save(program)

        # Save 2 — first update succeeds, DB becomes version=2
        first_update = dataclasses.replace(program, name="First Update", version=1)
        await program_repo.save(first_update)

        # Save 3 — stale update: version=1 but DB is at version=2 → must fail
        stale = dataclasses.replace(program, name="Stale Update", version=1)
        with pytest.raises(PlanVersionConflictError):
            await program_repo.save(stale)


# ── AssignmentRepository ──────────────────────────────────────────────────────


class TestAssignmentRepository:
    async def test_save_and_list_active(self, db_session: AsyncSession) -> None:
        user_repo = UserRepository(db_session)
        repo = ClientStaffAssignmentRepository(db_session)

        client = make_user(role=UserRole.CLIENT)
        trainer = make_user(role=UserRole.FITNESS_TRAINER)
        admin = make_user(role=UserRole.SUPER_ADMIN)
        await user_repo.save(client)
        await user_repo.save(trainer)
        await user_repo.save(admin)

        assignment = ClientStaffAssignment(
            id=uuid4(),
            client_id=client.id,
            staff_id=trainer.id,
            staff_role=StaffRole.FITNESS_TRAINER,
            assigned_at=NOW,
            ended_at=None,
            ended_reason=None,
            assigned_by=admin.id,
        )
        await repo.save(assignment)

        active = await repo.get_active_for_client(client.id)
        assert len(active) == 1
        assert active[0].is_active is True
        assert active[0].staff_role == StaffRole.FITNESS_TRAINER

    async def test_end_assignment(self, db_session: AsyncSession) -> None:
        user_repo = UserRepository(db_session)
        repo = ClientStaffAssignmentRepository(db_session)

        client = make_user(role=UserRole.CLIENT)
        trainer = make_user(role=UserRole.FITNESS_TRAINER)
        admin = make_user(role=UserRole.SUPER_ADMIN)
        await user_repo.save(client)
        await user_repo.save(trainer)
        await user_repo.save(admin)

        assignment = ClientStaffAssignment(
            id=uuid4(),
            client_id=client.id,
            staff_id=trainer.id,
            staff_role=StaffRole.FITNESS_TRAINER,
            assigned_at=NOW,
            ended_at=None,
            ended_reason=None,
            assigned_by=admin.id,
        )
        await repo.save(assignment)
        await repo.end_assignment(assignment.id, NOW, "client_request")

        active = await repo.get_active_for_client(client.id)
        assert len(active) == 0


# ── WorkoutLog — tonnage GENERATED column ─────────────────────────────────────


class TestWorkoutLogRepository:
    async def test_tonnage_generated_correctly(self, db_session: AsyncSession) -> None:
        """
        Verifies the GENERATED ALWAYS AS column computes correctly in PostgreSQL.
        4 sets × 6 reps × 70 kg = 1680 kg (matches spreadsheet sample data).
        """
        from datetime import date

        user_repo = UserRepository(db_session)
        prog_repo = WorkoutProgramRepository(db_session)
        week_repo = ProgramWeekRepository(db_session)
        day_repo = ProgramDayRepository(db_session)
        pres_repo = WorkoutPrescriptionRepository(db_session)
        log_repo = WorkoutLogRepository(db_session)

        client = make_user()
        await user_repo.save(client)

        program = make_workout_program(client)
        await prog_repo.save(program)

        week = ProgramWeek(
            id=uuid4(),
            program_id=program.id,
            week_number=1,
            label="Week 1",
            notes=None,
            created_at=NOW,
        )
        await week_repo.save(week)

        day = ProgramDay(
            id=uuid4(),
            week_id=week.id,
            day_number=1,
            label="Day 1",
            notes=None,
            created_at=NOW,
        )
        await day_repo.save(day)

        prescription = WorkoutPrescription(
            id=uuid4(),
            day_id=day.id,
            order_index=1,
            exercise_name="Bench Press",
            warmup_sets=2,
            working_sets=4,
            reps_min=6,
            reps_max=8,
            reps_note=None,
            prescribed_load_kg=Decimal("70"),
            prescribed_load_text=None,
            prescribed_rpe=None,
            prescribed_rir=None,
            rest_seconds=180,
            instructions=None,
            created_at=NOW,
            updated_at=NOW,
        )
        await pres_repo.save(prescription)

        log = WorkoutLog(
            id=uuid4(),
            prescription_id=prescription.id,
            client_id=client.id,
            exercise_name=None,
            logged_at=date(2025, 4, 8),
            actual_sets=4,
            actual_reps=6,
            actual_load_kg=Decimal("70"),
            actual_rpe=Decimal("8.0"),
            readiness=8,
            time_taken_seconds=2580,
            client_notes=None,
            video_url=None,
            video_source=None,
            created_at=NOW,
        )
        saved_log = await log_repo.save(log)

        # Verify domain entity @property
        assert saved_log.tonnage_kg == Decimal("1680")

    async def test_bodyweight_log_has_none_tonnage(
        self, db_session: AsyncSession
    ) -> None:
        from datetime import date

        user_repo = UserRepository(db_session)
        log_repo = WorkoutLogRepository(db_session)

        client = make_user()
        await user_repo.save(client)

        log = WorkoutLog(
            id=uuid4(),
            prescription_id=None,
            client_id=client.id,
            exercise_name="Pull-ups",
            logged_at=date(2025, 4, 8),
            actual_sets=3,
            actual_reps=10,
            actual_load_kg=None,
            actual_rpe=Decimal("7.5"),
            readiness=9,
            time_taken_seconds=600,
            client_notes=None,
            video_url=None,
            video_source=None,
            created_at=NOW,
        )
        saved = await log_repo.save(log)
        assert saved.tonnage_kg is None
        assert saved.is_self_logged is True


# ── PlanVersion — append-only ─────────────────────────────────────────────────


class TestPlanVersionRepository:
    async def test_versions_are_append_only(self, db_session: AsyncSession) -> None:
        user_repo = UserRepository(db_session)
        program_repo = WorkoutProgramRepository(db_session)
        version_repo = PlanVersionRepository(db_session)

        owner = make_user()
        await user_repo.save(owner)
        program = make_workout_program(owner)
        await program_repo.save(program)

        v1 = PlanVersion(
            id=uuid4(),
            plan_type=PlanType.WORKOUT,
            plan_id=program.id,
            snapshot={"version": 1, "name": "Test Programme"},
            modified_by=owner.id,
            modified_at=NOW,
            change_reason=None,
        )
        v2 = PlanVersion(
            id=uuid4(),
            plan_type=PlanType.WORKOUT,
            plan_id=program.id,
            snapshot={"version": 2, "name": "Test Programme — updated"},
            modified_by=owner.id,
            modified_at=NOW,
            change_reason="Added week 2",
        )
        await version_repo.save(v1)
        await version_repo.save(v2)

        versions = await version_repo.list_by_plan(PlanType.WORKOUT, program.id)
        assert len(versions) == 2
        # Most recent first
        assert versions[0].snapshot["version"] == 2


# ── BodyMetric — at-least-one constraint ──────────────────────────────────────


class TestBodyMetricRepository:
    async def test_save_weight_only_metric(self, db_session: AsyncSession) -> None:
        user_repo = UserRepository(db_session)
        metric_repo = BodyMetricRepository(db_session)

        user = make_user()
        await user_repo.save(user)

        metric = BodyMetric(
            id=uuid4(),
            user_id=user.id,
            recorded_by=user.id,
            recorded_at=NOW,
            weight_kg=Decimal("73.5"),
            body_fat_pct=None,
            muscle_mass_kg=None,
            notes=None,
            created_at=NOW,
        )
        saved = await metric_repo.save(metric)
        assert saved.weight_kg == Decimal("73.5")

    async def test_list_returns_most_recent_first(
        self, db_session: AsyncSession
    ) -> None:
        from datetime import timezone
        import datetime as dt

        user_repo = UserRepository(db_session)
        metric_repo = BodyMetricRepository(db_session)

        user = make_user()
        await user_repo.save(user)

        older = BodyMetric(
            id=uuid4(),
            user_id=user.id,
            recorded_by=user.id,
            recorded_at=datetime(2025, 3, 1, tzinfo=timezone.utc),
            weight_kg=Decimal("74.0"),
            body_fat_pct=None,
            muscle_mass_kg=None,
            notes=None,
            created_at=NOW,
        )
        newer = BodyMetric(
            id=uuid4(),
            user_id=user.id,
            recorded_by=user.id,
            recorded_at=datetime(2025, 4, 8, tzinfo=timezone.utc),
            weight_kg=Decimal("72.5"),
            body_fat_pct=None,
            muscle_mass_kg=None,
            notes=None,
            created_at=NOW,
        )
        await metric_repo.save(older)
        await metric_repo.save(newer)

        metrics = await metric_repo.list_for_user(user.id)
        assert metrics[0].weight_kg == Decimal("72.5")  # newer first
        assert metrics[1].weight_kg == Decimal("74.0")
