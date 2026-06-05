"""
Cross-plan repository implementations.

All three tables (plan_versions, plan_comments, plan_activity_log) use a
(plan_type, plan_id) discriminator. The queries always filter on both
columns together — never on plan_id alone — to avoid cross-plan contamination.

Design choice — soft_delete on PlanComment, no hard delete method:
    The interface exposes only soft_delete(). There is no delete() method.
    Providing a hard delete path would make it possible to accidentally
    destroy coaching records. The only way to permanently remove a comment
    is a direct DBA action with a documented reason.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.enums import PlanType
from domain.entities.plan import PlanActivityLog, PlanComment, PlanVersion
from domain.interfaces.repositories import (
    IPlanActivityLogRepository,
    IPlanCommentRepository,
    IPlanVersionRepository,
)
from infrastructure.db.models import (
    PlanActivityLogModel,
    PlanCommentModel,
    PlanVersionModel,
)


class PlanVersionRepository(IPlanVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: PlanVersionModel) -> PlanVersion:
        return PlanVersion(
            id=m.id,
            plan_type=m.plan_type,
            plan_id=m.plan_id,
            snapshot=dict(m.snapshot),
            modified_by=m.modified_by,
            modified_at=m.modified_at,
            change_reason=m.change_reason,
        )

    async def list_by_plan(
        self, plan_type: PlanType, plan_id: UUID
    ) -> list[PlanVersion]:
        stmt = (
            select(PlanVersionModel)
            .where(
                PlanVersionModel.plan_type == plan_type,
                PlanVersionModel.plan_id == plan_id,
            )
            .order_by(PlanVersionModel.modified_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, version: PlanVersion) -> PlanVersion:
        """Always inserts — plan versions are append-only."""
        model = PlanVersionModel(
            id=version.id,
            plan_type=version.plan_type,
            plan_id=version.plan_id,
            snapshot=version.snapshot,
            modified_by=version.modified_by,
            modified_at=version.modified_at,
            change_reason=version.change_reason,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)


class PlanCommentRepository(IPlanCommentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: PlanCommentModel) -> PlanComment:
        return PlanComment(
            id=m.id,
            plan_type=m.plan_type,
            plan_id=m.plan_id,
            author_id=m.author_id,
            body=m.body,
            is_deleted=m.is_deleted,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    async def list_by_plan(
        self, plan_type: PlanType, plan_id: UUID
    ) -> list[PlanComment]:
        stmt = (
            select(PlanCommentModel)
            .where(
                PlanCommentModel.plan_type == plan_type,
                PlanCommentModel.plan_id == plan_id,
                PlanCommentModel.is_deleted == False,  # noqa: E712
            )
            .order_by(PlanCommentModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, comment: PlanComment) -> PlanComment:
        model = await self._session.get(PlanCommentModel, comment.id)
        if model is None:
            model = PlanCommentModel(
                id=comment.id,
                plan_type=comment.plan_type,
                plan_id=comment.plan_id,
                author_id=comment.author_id,
                body=comment.body,
                is_deleted=comment.is_deleted,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
            )
            self._session.add(model)
        else:
            model.body = comment.body
            model.updated_at = comment.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def soft_delete(self, comment_id: UUID) -> None:
        stmt = (
            update(PlanCommentModel)
            .where(PlanCommentModel.id == comment_id)
            .values(is_deleted=True)
        )
        await self._session.execute(stmt)


class PlanActivityLogRepository(IPlanActivityLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: PlanActivityLogModel) -> PlanActivityLog:
        return PlanActivityLog(
            id=m.id,
            plan_type=m.plan_type,
            plan_id=m.plan_id,
            actor_id=m.actor_id,
            action=m.action,
            metadata=dict(m.log_metadata) if m.log_metadata else None,
            occurred_at=m.occurred_at,
        )

    async def list_by_plan(
        self, plan_type: PlanType, plan_id: UUID, limit: int = 50
    ) -> list[PlanActivityLog]:
        stmt = (
            select(PlanActivityLogModel)
            .where(
                PlanActivityLogModel.plan_type == plan_type,
                PlanActivityLogModel.plan_id == plan_id,
            )
            .order_by(PlanActivityLogModel.occurred_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def save(self, log: PlanActivityLog) -> PlanActivityLog:
        """Always inserts — the activity log is append-only."""
        model = PlanActivityLogModel(
            id=log.id,
            plan_type=log.plan_type,
            plan_id=log.plan_id,
            actor_id=log.actor_id,
            action=log.action,
            log_metadata=log.metadata,
            occurred_at=log.occurred_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
