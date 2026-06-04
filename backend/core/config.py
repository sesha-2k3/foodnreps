"""
Application configuration loaded from environment variables / .env file.

Design choice — pydantic-settings, not python-dotenv:
    pydantic-settings validates every field at import time with full type checking.
    A missing JWT_SECRET or a malformed DATABASE_URL causes an immediate, clear
    error at startup — not a confusing AttributeError three requests into production.
    This is the fail-fast principle applied to configuration.

Design choice — Settings as a module-level singleton:
    `settings = Settings()` runs once at import time. Every module that needs
    configuration does `from core.config import settings` and gets the same object.
    No dependency injection needed for configuration — it is immutable after startup.
"""

from pathlib import Path
from pydantic import PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────────────────
    # PostgresDsn validates the URL format (scheme, host, port, db name).
    # str(settings.database_url) is required when passing to SQLAlchemy —
    # pydantic v2 returns a PostgresDsn object, not a plain string.
    database_url: PostgresDsn

    # Test database — None in production, set in .env for local dev.
    # Sprint 2 integration test conftest will use this.
    test_database_url: PostgresDsn | None = None

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # Access token: short-lived, stored in JS memory only (never localStorage).
    access_token_expire_minutes: int = 15

    # Refresh token: long-lived, stored in httpOnly cookie.
    refresh_token_expire_days: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    # List of allowed origins for cross-origin requests.
    # Frontend dev server default: http://localhost:5173 (Vite)
    allowed_origins: list[str] = ["http://localhost:5173"]

    # ── Application ───────────────────────────────────────────────────────────
    debug: bool = False
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,       # DATABASE_URL and database_url both work
        extra="ignore",             # unknown env vars are silently ignored
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """
        Refuse to start in production with the placeholder JWT secret.

        Design choice: This validation runs after all fields are populated,
        so it can check the combination of `environment` + `jwt_secret`.
        Catching this at startup prevents a silent security failure where
        the app runs in production with a publicly known secret.
        """
        placeholder = "change-me-in-production-use-a-256-bit-random-string"
        if self.environment == "production" and self.jwt_secret == placeholder:
            raise ValueError(
                "JWT_SECRET must be changed in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self


# Module-level singleton — imported as `from core.config import settings`
settings = Settings()
