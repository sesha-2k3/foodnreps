"""
Alembic environment configuration — async-aware.

Design choice — async Alembic:
    SQLAlchemy 2.0 async requires Alembic to use `async_engine_from_config`
    and run migrations inside `asyncio.run()`. The standard synchronous Alembic
    env.py template does not work with asyncpg. This file is the async-correct
    version.

Design choice — sqlalchemy.url set programmatically:
    The database URL is not in alembic.ini. It is read from `core.config.settings`
    here and injected via `config.set_main_option()`. This ensures there is exactly
    one source of truth for the database URL (the .env file), and prevents Alembic
    from connecting to the wrong database in a misconfigured environment.

Design choice — target_metadata:
    Sprint 0: `target_metadata = None` — no models exist yet.
    Sprint 2: Replace with `from infrastructure.db.models import Base`
              and set `target_metadata = Base.metadata`.
    With `target_metadata` set, `alembic revision --autogenerate` will detect
    schema differences between the ORM models and the actual database.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import application settings — prepend_sys_path = . in alembic.ini
# adds backend/ to sys.path so this import resolves correctly.
from core.config import settings
from infrastructure.db import models as _models  # noqa: F401  registers all models

# ── Sprint 2: uncomment and replace target_metadata ──────────────────────────
# from infrastructure.db.models import Base
# target_metadata = Base.metadata
# ─────────────────────────────────────────────────────────────────────────────
# All ORM models must be imported so SQLAlchemy registers them on Base.metadata.
# autogenerate compares Base.metadata against the live DB — if a model is not
# imported here, its table will not appear in generated migrations.
from infrastructure.db.base import Base  # noqa: F401

target_metadata = Base.metadata
# target_metadata = None  # updated in Sprint 2

# Load the Alembic config and inject our database URL
config = context.config
config.set_main_option("sqlalchemy.url", str(settings.database_url))

# Set up logging from the alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ── Offline mode (no DB connection, generates SQL script) ─────────────────────

def run_migrations_offline() -> None:
    """
    Generates migration SQL without connecting to the database.
    Used for: reviewing migrations before applying, CI dry-runs.

    Usage: alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,          # detect column type changes
        compare_server_default=True, # detect default value changes
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (connects to DB and runs migrations) ──────────────────────────

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Creates an async engine and runs migrations inside an async context.

    Design choice — NullPool for migrations:
        Migrations run as a one-shot command, not a long-lived server.
        `NullPool` disables connection pooling, ensuring the connection
        is closed immediately after the migration completes. Using the
        standard pool for a CLI command would leave connections open.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
