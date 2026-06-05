"""
ClientStaffAssignment repository.

Design choice — end_assignment updates in place, never deletes:
    Ending an assignment sets ended_at and ended_reason on the existing row.
    The row is never deleted. History is the product — every coaching
    relationship the client has ever had is preserved and queryable.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.assignment import ClientStaffAssignment
from domain.entities.enums import StaffRole
from domain.interfaces.repositories import IClientStaffAssignmentRepository
from infrastructure.db.models import ClientStaffAssignmentModel


class ClientStaffAssignmentRepository(IClientStaffAssignmentRepository):

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: ClientStaffAssignmentModel) -> ClientStaffAssignment:
        return ClientStaffAssignment(
            id=m.id, client_id=m.client_id, staff_id=m.staff_id,
            staff_role=m.staff_role,
            assigned_at=m.assigned_at, ended_at=m.ended_at,
            ended_reason=m.ended_reason, assigned_by=m.assigned_by,
        )

    async def get_active_for_client(
        self, client_id: UUID
    ) -> list[ClientStaffAssignment]:
        stmt = select(ClientStaffAssignmentModel).where(
            ClientStaffAssignmentModel.client_id == client_id,
            ClientStaffAssignmentModel.ended_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def get_active_by_role_for_client(
        self, client_id: UUID, staff_role: StaffRole
    ) -> ClientStaffAssignment | None:
        stmt = select(ClientStaffAssignmentModel).where(
            ClientStaffAssignmentModel.client_id == client_id,
            ClientStaffAssignmentModel.staff_role == staff_role,
            ClientStaffAssignmentModel.ended_at.is_(None),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_active_for_staff(
        self, staff_id: UUID
    ) -> list[ClientStaffAssignment]:
        stmt = select(ClientStaffAssignmentModel).where(
            ClientStaffAssignmentModel.staff_id == staff_id,
            ClientStaffAssignmentModel.ended_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def get_history_for_client(
        self, client_id: UUID
    ) -> list[ClientStaffAssignment]:
        stmt = (
            select(ClientStaffAssignmentModel)
            .where(ClientStaffAssignmentModel.client_id == client_id)
            .order_by(ClientStaffAssignmentModel.assigned_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(
        self, assignment: ClientStaffAssignment
    ) -> ClientStaffAssignment:
        model = ClientStaffAssignmentModel(
            id=assignment.id, client_id=assignment.client_id,
            staff_id=assignment.staff_id, staff_role=assignment.staff_role,
            assigned_at=assignment.assigned_at,
            ended_at=assignment.ended_at, ended_reason=assignment.ended_reason,
            assigned_by=assignment.assigned_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def end_assignment(
        self, assignment_id: UUID, ended_at: datetime, ended_reason: str
    ) -> None:
        stmt = (
            update(ClientStaffAssignmentModel)
            .where(ClientStaffAssignmentModel.id == assignment_id)
            .values(ended_at=ended_at, ended_reason=ended_reason)
        )
        await self._session.execute(stmt)
