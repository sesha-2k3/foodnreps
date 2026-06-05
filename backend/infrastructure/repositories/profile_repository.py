"""
IntakeProfile and BodyMetric repository implementations.

Design choice — tuple ↔ list conversion at the storage boundary:
    Domain entities store injuries and equipment as tuple[str, ...] for
    immutability (frozen dataclasses with mutable lists can be mutated
    in place, breaking the immutability guarantee).
    PostgreSQL ARRAY maps to Python list[str] in SQLAlchemy.
    This repository is the translation point — the only place in the
    codebase where this conversion exists.

Design choice — BodyMetric.save() always inserts, never updates:
    Body metrics are an append-only time series. Providing an update
    path would make it possible to silently rewrite historical measurement
    data. The interface defines save() as insert-only; the implementation
    enforces this by never calling session.get() first.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.profile import BodyMetric, IntakeProfile
from domain.interfaces.repositories import (
    IBodyMetricRepository,
    IIntakeProfileRepository,
)
from infrastructure.db.models import BodyMetricModel, IntakeProfileModel


class IntakeProfileRepository(IIntakeProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: IntakeProfileModel) -> IntakeProfile:
        return IntakeProfile(
            id=m.id,
            client_id=m.client_id,
            fitness_goal=m.fitness_goal,
            experience_level=m.experience_level,
            # list[str] from ARRAY → tuple[str, ...] for frozen entity
            injuries=tuple(m.injuries),
            equipment=tuple(m.equipment),
            dietary_notes=m.dietary_notes,
            target_weight_kg=m.target_weight_kg,
            current_weight_kg=m.current_weight_kg,
            completed_at=m.completed_at,
            updated_at=m.updated_at,
        )

    async def get_by_client_id(self, client_id: UUID) -> IntakeProfile | None:
        stmt = select(IntakeProfileModel).where(
            IntakeProfileModel.client_id == client_id
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, profile: IntakeProfile) -> IntakeProfile:
        model = await self._session.get(IntakeProfileModel, profile.id)
        if model is None:
            model = IntakeProfileModel(
                id=profile.id,
                client_id=profile.client_id,
                fitness_goal=profile.fitness_goal,
                experience_level=profile.experience_level,
                # tuple[str, ...] → list[str] for ARRAY column
                injuries=list(profile.injuries),
                equipment=list(profile.equipment),
                dietary_notes=profile.dietary_notes,
                target_weight_kg=profile.target_weight_kg,
                current_weight_kg=profile.current_weight_kg,
                completed_at=profile.completed_at,
                updated_at=profile.updated_at,
            )
            self._session.add(model)
        else:
            model.fitness_goal = profile.fitness_goal
            model.experience_level = profile.experience_level
            model.injuries = list(profile.injuries)
            model.equipment = list(profile.equipment)
            model.dietary_notes = profile.dietary_notes
            model.target_weight_kg = profile.target_weight_kg
            model.current_weight_kg = profile.current_weight_kg
            model.updated_at = profile.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)


class BodyMetricRepository(IBodyMetricRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: BodyMetricModel) -> BodyMetric:
        return BodyMetric(
            id=m.id,
            user_id=m.user_id,
            recorded_by=m.recorded_by,
            recorded_at=m.recorded_at,
            weight_kg=m.weight_kg,
            body_fat_pct=m.body_fat_pct,
            muscle_mass_kg=m.muscle_mass_kg,
            notes=m.notes,
            created_at=m.created_at,
        )

    async def list_for_user(self, user_id: UUID, limit: int = 50) -> list[BodyMetric]:
        stmt = (
            select(BodyMetricModel)
            .where(BodyMetricModel.user_id == user_id)
            .order_by(BodyMetricModel.recorded_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, metric: BodyMetric) -> BodyMetric:
        """Always inserts — body metrics are append-only."""
        model = BodyMetricModel(
            id=metric.id,
            user_id=metric.user_id,
            recorded_by=metric.recorded_by,
            recorded_at=metric.recorded_at,
            weight_kg=metric.weight_kg,
            body_fat_pct=metric.body_fat_pct,
            muscle_mass_kg=metric.muscle_mass_kg,
            notes=metric.notes,
            created_at=metric.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
