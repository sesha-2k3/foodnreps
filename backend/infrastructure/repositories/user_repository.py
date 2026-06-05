"""
User and RefreshToken repository implementations.

Design choice — _to_entity and _to_model as the only translation boundary:
    Every read goes through _to_entity. Every write goes through _to_model.
    No other code in this file should map field by field. This ensures there
    is exactly one place to update when a field is added or renamed.

Design choice — session.flush() not session.commit():
    Repositories flush to make changes visible within the current transaction
    and to get server-generated values (id, created_at, updated_at) back from
    the DB via refresh(). Committing is the session dependency's responsibility
    (infrastructure/db/session.py::get_session). Repositories never commit.

Design choice — update by mutating the existing model, not delete+insert:
    When save() finds an existing row, it updates fields on the loaded model
    object. SQLAlchemy's unit-of-work tracks the mutation and issues an UPDATE
    on flush. Delete+insert would change the row's created_at and could violate
    FK constraints on child rows.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import RefreshToken, User
from domain.interfaces.repositories import IRefreshTokenRepository, IUserRepository
from infrastructure.db.models import RefreshTokenModel, UserModel


class UserRepository(IUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Mapping ───────────────────────────────────────────────────────────────

    def _to_entity(self, m: UserModel) -> User:
        return User(
            id=m.id,
            email=m.email,
            password_hash=m.password_hash,
            full_name=m.full_name,
            role=m.role,
            is_active=m.is_active,
            is_deleted=m.is_deleted,
            deleted_at=m.deleted_at,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )

    def _to_model(self, e: User) -> UserModel:
        return UserModel(
            id=e.id,
            email=e.email,
            password_hash=e.password_hash,
            full_name=e.full_name,
            role=e.role,
            is_active=e.is_active,
            is_deleted=e.is_deleted,
            deleted_at=e.deleted_at,
            created_at=e.created_at,
            updated_at=e.updated_at,
        )

    # ── Interface implementation ───────────────────────────────────────────────

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(UserModel).where(
                UserModel.email == email, UserModel.is_deleted == False
            )  # noqa: E712
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, user: User) -> User:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            model = self._to_model(user)
            self._session.add(model)
        else:
            model.email = user.email
            model.password_hash = user.password_hash
            model.full_name = user.full_name
            model.role = user.role
            model.is_active = user.is_active
            model.is_deleted = user.is_deleted
            model.deleted_at = user.deleted_at
            model.updated_at = user.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def list_clients(self) -> list[User]:
        from domain.entities.enums import UserRole

        stmt = select(UserModel).where(
            UserModel.role == UserRole.CLIENT,
            UserModel.is_deleted == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def list_staff(self) -> list[User]:
        from domain.entities.enums import UserRole

        stmt = select(UserModel).where(
            UserModel.role.in_(
                [
                    UserRole.FITNESS_TRAINER,
                    UserRole.NUTRITIONIST,
                    UserRole.MASTER_COACH,
                ]
            ),
            UserModel.is_deleted == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]


class RefreshTokenRepository(IRefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=m.id,
            user_id=m.user_id,
            token_id=m.token_id,
            is_revoked=m.is_revoked,
            expires_at=m.expires_at,
            revoked_at=m.revoked_at,
            created_at=m.created_at,
        )

    async def get_by_token_id(self, token_id: UUID) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_id == token_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_id=token.token_id,
            is_revoked=token.is_revoked,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            created_at=token.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def revoke(self, token_id: UUID, revoked_at: datetime) -> None:
        stmt = (
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_id == token_id)
            .values(is_revoked=True, revoked_at=revoked_at)
        )
        await self._session.execute(stmt)

    async def revoke_all_for_user(self, user_id: UUID, revoked_at: datetime) -> None:
        stmt = (
            update(RefreshTokenModel)
            .where(
                RefreshTokenModel.user_id == user_id,
                RefreshTokenModel.is_revoked == False,  # noqa: E712
            )
            .values(is_revoked=True, revoked_at=revoked_at)
        )
        await self._session.execute(stmt)
