"""
Workout repository implementations:
    WorkoutProgramRepository, ProgramWeekRepository, ProgramDayRepository,
    WorkoutPrescriptionRepository, WorkoutLogRepository

Design choice — optimistic locking in WorkoutProgramRepository.save():
    Before updating a programme, the repository checks that program.version
    matches the current version in the database. If another save has happened
    between the load and this save, the versions will differ and
    PlanVersionConflictError is raised. The service layer presents this as a
    "please reload" error to the user.

    The version is incremented on every successful update by the repository —
    not by the service. This keeps the version management in one place.

Design choice — WorkoutLogRepository.save() always inserts:
    Training logs are append-only. Updating a log would rewrite history.
    No update path is provided.

Design choice — tonnage_kg is not mapped in _to_entity for WorkoutLog:
    The domain entity computes tonnage_kg as a @property from actual_sets,
    actual_reps, and actual_load_kg. The GENERATED column in the DB stores
    the same value for query/sort purposes. The repository does not need to
    map the GENERATED column — the entity property handles it automatically.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import PlanVersionConflictError
from domain.entities.workout import (
    ProgramDay,
    ProgramWeek,
    WorkoutLog,
    WorkoutPrescription,
    WorkoutProgram,
)
from domain.interfaces.repositories import (
    IProgramDayRepository,
    IProgramWeekRepository,
    IWorkoutLogRepository,
    IWorkoutPrescriptionRepository,
    IWorkoutProgramRepository,
)
from infrastructure.db.models import (
    ProgramDayModel,
    ProgramWeekModel,
    WorkoutLogModel,
    WorkoutPrescriptionModel,
    WorkoutProgramModel,
)


class WorkoutProgramRepository(IWorkoutProgramRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: WorkoutProgramModel) -> WorkoutProgram:
        return WorkoutProgram(
            id=m.id,
            owner_id=m.owner_id,
            created_by_id=m.created_by_id,
            name=m.name,
            is_active=m.is_active,
            is_personal=m.is_personal,
            is_template=m.is_template,
            coach_notes=m.coach_notes,
            version=m.version,
            last_modified_by=m.last_modified_by,
            last_modified_at=m.last_modified_at,
            override_reason=m.override_reason,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def get_by_id(self, program_id: UUID) -> WorkoutProgram | None:
        model = await self._session.get(WorkoutProgramModel, program_id)
        return self._to_entity(model) if model else None

    async def get_active_by_owner(self, owner_id: UUID) -> WorkoutProgram | None:
        stmt = select(WorkoutProgramModel).where(
            WorkoutProgramModel.owner_id == owner_id,
            WorkoutProgramModel.is_active == True,  # noqa: E712
            WorkoutProgramModel.is_template == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_owner(self, owner_id: UUID) -> list[WorkoutProgram]:
        stmt = (
            select(WorkoutProgramModel)
            .where(WorkoutProgramModel.owner_id == owner_id)
            .order_by(WorkoutProgramModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, program: WorkoutProgram) -> WorkoutProgram:
        model = await self._session.get(WorkoutProgramModel, program.id)
        if model is None:
            model = WorkoutProgramModel(
                id=program.id,
                owner_id=program.owner_id,
                created_by_id=program.created_by_id,
                name=program.name,
                is_active=program.is_active,
                is_personal=program.is_personal,
                is_template=program.is_template,
                coach_notes=program.coach_notes,
                version=program.version,
                last_modified_by=program.last_modified_by,
                last_modified_at=program.last_modified_at,
                override_reason=program.override_reason,
                created_at=program.created_at,
                updated_at=program.updated_at,
            )
            self._session.add(model)
        else:
            # Optimistic lock — version must match what the caller loaded
            if model.version != program.version:
                raise PlanVersionConflictError(
                    f"Programme '{program.name}' was modified by someone else "
                    f"(expected version {program.version}, found {model.version}). "
                    "Please reload and try again."
                )
            model.name = program.name
            model.is_active = program.is_active
            model.is_personal = program.is_personal
            model.is_template = program.is_template
            model.coach_notes = program.coach_notes
            model.version = program.version + 1  # increment on every update
            model.last_modified_by = program.last_modified_by
            model.last_modified_at = program.last_modified_at
            model.override_reason = program.override_reason
            model.updated_at = program.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def get_active_assigned_by_owner(
        self, owner_id: UUID
    ) -> WorkoutProgram | None:
        """Returns the trainer/coach-assigned programme (is_personal=False)."""
        stmt = select(WorkoutProgramModel).where(
            WorkoutProgramModel.owner_id == owner_id,
            WorkoutProgramModel.is_active == True,  # noqa: E712
            WorkoutProgramModel.is_template == False,  # noqa: E712
            WorkoutProgramModel.is_personal == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_active_personal_by_owner(
        self, owner_id: UUID
    ) -> WorkoutProgram | None:
        """Returns the self-managed personal programme (is_personal=True)."""
        stmt = select(WorkoutProgramModel).where(
            WorkoutProgramModel.owner_id == owner_id,
            WorkoutProgramModel.is_active == True,  # noqa: E712
            WorkoutProgramModel.is_template == False,  # noqa: E712
            WorkoutProgramModel.is_personal == True,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None


class ProgramWeekRepository(IProgramWeekRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: ProgramWeekModel) -> ProgramWeek:
        return ProgramWeek(
            id=m.id,
            program_id=m.program_id,
            week_number=m.week_number,
            label=m.label,
            notes=m.notes,
            created_at=m.created_at,
        )

    async def list_by_program(self, program_id: UUID) -> list[ProgramWeek]:
        stmt = (
            select(ProgramWeekModel)
            .where(ProgramWeekModel.program_id == program_id)
            .order_by(ProgramWeekModel.week_number)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, week: ProgramWeek) -> ProgramWeek:
        model = await self._session.get(ProgramWeekModel, week.id)
        if model is None:
            model = ProgramWeekModel(
                id=week.id,
                program_id=week.program_id,
                week_number=week.week_number,
                label=week.label,
                notes=week.notes,
                created_at=week.created_at,
            )
            self._session.add(model)
        else:
            model.label = week.label
            model.notes = week.notes
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, week_id: UUID) -> None:
        model = await self._session.get(ProgramWeekModel, week_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()


class ProgramDayRepository(IProgramDayRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: ProgramDayModel) -> ProgramDay:
        return ProgramDay(
            id=m.id,
            week_id=m.week_id,
            day_number=m.day_number,
            label=m.label,
            notes=m.notes,
            created_at=m.created_at,
        )

    async def list_by_week(self, week_id: UUID) -> list[ProgramDay]:
        stmt = (
            select(ProgramDayModel)
            .where(ProgramDayModel.week_id == week_id)
            .order_by(ProgramDayModel.day_number)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, day: ProgramDay) -> ProgramDay:
        model = await self._session.get(ProgramDayModel, day.id)
        if model is None:
            model = ProgramDayModel(
                id=day.id,
                week_id=day.week_id,
                day_number=day.day_number,
                label=day.label,
                notes=day.notes,
                created_at=day.created_at,
            )
            self._session.add(model)
        else:
            model.label = day.label
            model.notes = day.notes
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, day_id: UUID) -> None:
        model = await self._session.get(ProgramDayModel, day_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()


class WorkoutPrescriptionRepository(IWorkoutPrescriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: WorkoutPrescriptionModel) -> WorkoutPrescription:
        return WorkoutPrescription(
            id=m.id,
            day_id=m.day_id,
            order_index=m.order_index,
            exercise_name=m.exercise_name,
            warmup_sets=m.warmup_sets,
            working_sets=m.working_sets,
            reps_min=m.reps_min,
            reps_max=m.reps_max,
            reps_note=m.reps_note,
            prescribed_load_kg=m.prescribed_load_kg,
            prescribed_load_text=m.prescribed_load_text,
            prescribed_rpe=m.prescribed_rpe,
            prescribed_rir=m.prescribed_rir,
            rest_seconds=m.rest_seconds,
            instructions=m.instructions,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def get_by_id(self, prescription_id: UUID) -> WorkoutPrescription | None:
        model = await self._session.get(WorkoutPrescriptionModel, prescription_id)
        return self._to_entity(model) if model else None

    async def list_by_day(self, day_id: UUID) -> list[WorkoutPrescription]:
        stmt = (
            select(WorkoutPrescriptionModel)
            .where(WorkoutPrescriptionModel.day_id == day_id)
            .order_by(WorkoutPrescriptionModel.order_index)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, prescription: WorkoutPrescription) -> WorkoutPrescription:
        model = await self._session.get(WorkoutPrescriptionModel, prescription.id)
        if model is None:
            model = WorkoutPrescriptionModel(
                id=prescription.id,
                day_id=prescription.day_id,
                order_index=prescription.order_index,
                exercise_name=prescription.exercise_name,
                warmup_sets=prescription.warmup_sets,
                working_sets=prescription.working_sets,
                reps_min=prescription.reps_min,
                reps_max=prescription.reps_max,
                reps_note=prescription.reps_note,
                prescribed_load_kg=prescription.prescribed_load_kg,
                prescribed_load_text=prescription.prescribed_load_text,
                prescribed_rpe=prescription.prescribed_rpe,
                prescribed_rir=prescription.prescribed_rir,
                rest_seconds=prescription.rest_seconds,
                instructions=prescription.instructions,
                created_at=prescription.created_at,
                updated_at=prescription.updated_at,
            )
            self._session.add(model)
        else:
            model.order_index = prescription.order_index
            model.exercise_name = prescription.exercise_name
            model.warmup_sets = prescription.warmup_sets
            model.working_sets = prescription.working_sets
            model.reps_min = prescription.reps_min
            model.reps_max = prescription.reps_max
            model.reps_note = prescription.reps_note
            model.prescribed_load_kg = prescription.prescribed_load_kg
            model.prescribed_load_text = prescription.prescribed_load_text
            model.prescribed_rpe = prescription.prescribed_rpe
            model.prescribed_rir = prescription.prescribed_rir
            model.rest_seconds = prescription.rest_seconds
            model.instructions = prescription.instructions
            model.updated_at = prescription.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, prescription_id: UUID) -> None:
        model = await self._session.get(WorkoutPrescriptionModel, prescription_id)
        if model:
            await self._session.delete(model)
            await self._session.flush()


class WorkoutLogRepository(IWorkoutLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: WorkoutLogModel) -> WorkoutLog:
        return WorkoutLog(
            id=m.id,
            prescription_id=m.prescription_id,
            client_id=m.client_id,
            exercise_name=m.exercise_name,
            logged_at=m.logged_at,
            actual_sets=m.actual_sets,
            actual_reps=m.actual_reps,
            actual_load_kg=m.actual_load_kg,
            actual_rpe=m.actual_rpe,
            readiness=m.readiness,
            time_taken_seconds=m.time_taken_seconds,
            client_notes=m.client_notes,
            video_url=m.video_url,
            video_source=m.video_source,
            created_at=m.created_at,
            # tonnage_kg intentionally NOT mapped — the entity @property
            # computes it from actual_sets, actual_reps, actual_load_kg
        )

    async def list_by_client(
        self, client_id: UUID, limit: int = 50
    ) -> list[WorkoutLog]:
        stmt = (
            select(WorkoutLogModel)
            .where(WorkoutLogModel.client_id == client_id)
            .order_by(WorkoutLogModel.logged_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def list_by_prescription(self, prescription_id: UUID) -> list[WorkoutLog]:
        stmt = (
            select(WorkoutLogModel)
            .where(WorkoutLogModel.prescription_id == prescription_id)
            .order_by(WorkoutLogModel.logged_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, log: WorkoutLog) -> WorkoutLog:
        """Always inserts — workout logs are append-only."""
        model = WorkoutLogModel(
            id=log.id,
            prescription_id=log.prescription_id,
            client_id=log.client_id,
            exercise_name=log.exercise_name,
            logged_at=log.logged_at,
            actual_sets=log.actual_sets,
            actual_reps=log.actual_reps,
            actual_load_kg=log.actual_load_kg,
            actual_rpe=log.actual_rpe,
            readiness=log.readiness,
            time_taken_seconds=log.time_taken_seconds,
            client_notes=log.client_notes,
            video_url=log.video_url,
            video_source=log.video_source,
            created_at=log.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
