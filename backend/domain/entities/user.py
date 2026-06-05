"""
User and RefreshToken domain entities.

Design choice — frozen=True on all entities:
    Domain entities are facts about the world. Once a User is loaded from
    the database, its fields should not be mutated in place — that would
    create a divergence between the in-memory state and the persisted state
    with no clear point of reconciliation.

    When a service needs to "update" a user (e.g., deactivate them), it creates
    a new User instance via dataclasses.replace():

        deactivated = dataclasses.replace(user, is_active=False, updated_at=now())

    The repository then persists this new instance. The original object remains
    unchanged, which makes the operation easy to reason about and test.

Design choice — password_hash stored on User entity:
    The domain entity carries the hashed password. It never carries the raw
    password — that is never stored anywhere. AuthService receives the raw
    password, hashes it with bcrypt, and constructs the User entity with
    the hash. No other service ever touches the password fields.

Design choice — RefreshToken is a domain entity:
    Refresh tokens have a lifecycle (issued, used, revoked, expired) that
    is a business concern — not just a technical one. The revocation rules
    (rotate on use, revoke all on password change) are business rules enforced
    in AuthService. The entity models this lifecycle cleanly.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from domain.entities.enums import UserRole


@dataclass(frozen=True)
class User:
    """
    Every person in the system: clients, all coaching staff, super admins.
    Maps to the `users` table.
    """

    id: UUID
    email: str
    password_hash: str
    full_name: str
    role: UserRole
    is_active: bool
    is_deleted: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @property
    def is_staff(self) -> bool:
        """True for any coaching role — not client, not super admin."""
        return self.role in (
            UserRole.FITNESS_TRAINER,
            UserRole.NUTRITIONIST,
            UserRole.MASTER_COACH,
        )

    @property
    def is_coach(self) -> bool:
        """True for master coach only — the role that owns both domains."""
        return self.role == UserRole.MASTER_COACH

    @property
    def can_write_workout_plans(self) -> bool:
        """Fitness trainers and master coaches can write workout plans."""
        return self.role in (UserRole.FITNESS_TRAINER, UserRole.MASTER_COACH)

    @property
    def can_write_diet_plans(self) -> bool:
        """Nutritionists and master coaches can write diet plans."""
        return self.role in (UserRole.NUTRITIONIST, UserRole.MASTER_COACH)


@dataclass(frozen=True)
class RefreshToken:
    """
    A persisted refresh token for JWT rotation.
    Maps to the `refresh_tokens` table.

    Design: token_id is the `jti` claim stored in the JWT payload.
    On every refresh request, the server looks up by token_id, checks
    is_revoked, and if valid, issues a new token + revokes this one.
    The full JWT string is never stored — only its identifier.
    """

    id: UUID
    user_id: UUID
    token_id: UUID  # jti claim — what the JWT carries
    is_revoked: bool
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime

    @property
    def is_valid(self) -> bool:
        """A token is valid when it is not revoked and has not expired."""

        return not self.is_revoked and self.expires_at > datetime.now(tz=UTC)
