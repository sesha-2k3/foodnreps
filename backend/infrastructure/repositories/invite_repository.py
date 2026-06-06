"""
Concrete implementation of ICoachingInviteRepository.
Place at: infrastructure/repositories/invite_repository.py
"""

from datetime import datetime, timezone, UTC
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.invite import CoachingInvite
from domain.interfaces.repositories import ICoachingInviteRepository
from infrastructure.db.models import CoachingInviteModel


class CoachingInviteRepository(ICoachingInviteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: CoachingInviteModel) -> CoachingInvite:
        return CoachingInvite(
            id=m.id,
            staff_id=m.staff_id,
            staff_role=m.staff_role,
            code=m.code,
            expires_at=m.expires_at,
            used_at=m.used_at,
            used_by=m.used_by,
            created_at=m.created_at,
        )

    async def get_by_code(self, code: str) -> CoachingInvite | None:
        # Always query uppercase — code is stored uppercase
        stmt = select(CoachingInviteModel).where(
            CoachingInviteModel.code == code.upper().strip()
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_id(self, invite_id: UUID) -> CoachingInvite | None:
        model = await self._session.get(CoachingInviteModel, invite_id)
        return self._to_entity(model) if model else None

    async def list_active_by_staff(self, staff_id: UUID) -> list[CoachingInvite]:
        from datetime import timezone

        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(CoachingInviteModel)
            .where(
                CoachingInviteModel.staff_id == staff_id,
                CoachingInviteModel.used_at.is_(None),
                CoachingInviteModel.expires_at > now,
            )
            .order_by(CoachingInviteModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, invite: CoachingInvite) -> CoachingInvite:
        model = CoachingInviteModel(
            id=invite.id,
            staff_id=invite.staff_id,
            staff_role=invite.staff_role,
            code=invite.code.upper(),
            expires_at=invite.expires_at.replace(tzinfo=None),  # strip tz
            used_at=invite.used_at.replace(tzinfo=None) if invite.used_at else None,
            used_by=invite.used_by,
            created_at=invite.created_at.replace(tzinfo=None),  # strip tz
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def mark_used(
        self,
        invite_id: UUID,
        used_by: UUID,
        used_at: datetime,
    ) -> None:
        # Strip timezone before writing — column is TIMESTAMP WITHOUT TIME ZONE
        used_at_naive = used_at.replace(tzinfo=None)
        stmt = (
            update(CoachingInviteModel)
            .where(CoachingInviteModel.id == invite_id)
            .values(used_at=used_at_naive, used_by=used_by)
        )
        await self._session.execute(stmt)

    async def delete(self, invite_id: UUID) -> None:
        stmt = delete(CoachingInviteModel).where(CoachingInviteModel.id == invite_id)
        await self._session.execute(stmt)
