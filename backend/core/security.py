"""
JWT encoding/decoding and password hashing utilities.

Design choice — lives in core/, not application/:
    Two layers consume this module: AuthService (application layer) and JWT
    middleware (presentation layer, Sprint 4). Placing it in application/
    would force the presentation layer to import downward through application/,
    creating a cross-layer dependency. core/ has no layer affiliation and is
    safe to import from any layer — it is the correct home for shared
    infrastructure primitives that are not themselves business logic.

Design choice — pure functions, not a class:
    These are stateless transformations. A class with no mutable state is just
    a namespace with extra syntax. Module-level functions are simpler, faster
    to call, and trivially patchable in unit tests via unittest.mock.patch.

Design choice — two decode functions (verify_exp vs ignore_exp):
    decode_token enforces expiry — the normal path for protected routes.
    decode_token_ignore_expiry is used only by AuthService.logout() so that
    a client can revoke an already-expired refresh token without receiving
    an Unauthorized error. Logout intent is valid regardless of expiry.

Design choice — token type claim ("type":  "access" | "refresh"):
    This prevents a refresh token from being used as an access token and
    vice versa. Without it, a long-lived refresh token that leaks could be
    presented to a protected route and succeed the signature check.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from core.config import settings
from core.exceptions import UnauthorizedError

# ── Password hashing ──────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    """
    Hash a plaintext password with bcrypt and return a UTF-8 string.

    bcrypt is intentionally slow (~100 ms at the default work factor of 12).
    This cost makes offline brute-force attacks against the stored hash
    computationally impractical. Never reduce the work factor below 12
    in production.
    """
    hashed: bytes = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Return True if plain matches the stored bcrypt hash.

    bcrypt.checkpw uses a constant-time comparison — the result takes the
    same amount of time regardless of how close the guess was. This prevents
    timing attacks that could reveal partial information about the hash.
    """
    return bool(bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8")))


# ── Token creation ────────────────────────────────────────────────────────────


def create_access_token(user_id: UUID, role: str) -> str:
    """
    Encode a short-lived access token (default: 15 minutes).

    Payload claims:
        sub   — user_id as string (standard JWT subject claim)
        role  — UserRole string value for route-level authorisation
        exp   — expiry timestamp (validated automatically by python-jose)
        type  — "access" (distinguishes from refresh tokens)
    """
    expires = datetime.now(tz=UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expires,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token_jwt(user_id: UUID, token_id: UUID) -> str:
    """
    Encode a long-lived refresh token (default: 7 days).

    Payload claims:
        sub   — user_id as string
        jti   — token_id UUID as string (stored in refresh_tokens.token_id)
        exp   — expiry timestamp
        type  — "refresh" (prevents use as an access token)

    The full JWT string is never stored in the database — only token_id (jti).
    A database breach therefore never exposes a valid, usable token — only
    an identifier that is useless without the signing secret.
    """
    expires = datetime.now(tz=UTC) + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "jti": str(token_id),
        "exp": expires,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ── Token decoding ────────────────────────────────────────────────────────────


def decode_token(token: str) -> dict[str, object]:
    """
    Decode and fully verify a JWT — signature, expiry, and algorithm.

    Returns the raw payload dict on success.
    Raises UnauthorizedError if the token is expired, tampered, or malformed.

    Called by: AuthService.refresh(), Sprint 4 JWT middleware.
    """
    try:
        payload: dict[str, object] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as exc:
        raise UnauthorizedError(f"Invalid or expired token: {exc}") from exc


def decode_token_ignore_expiry(token: str) -> dict[str, object]:
    """
    Decode a JWT verifying signature and algorithm but NOT expiry.

    Used exclusively by AuthService.logout() so that a client presenting
    an already-expired refresh token can still revoke it. The intent
    (end this session) is valid regardless of whether the token has expired.
    Expiry-checking is bypassed only here — all other callers use decode_token.
    """
    try:
        payload: dict[str, object] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        return payload
    except JWTError as exc:
        raise UnauthorizedError(f"Malformed token: {exc}") from exc
