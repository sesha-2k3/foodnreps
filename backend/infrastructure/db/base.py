"""
SQLAlchemy DeclarativeBase.

Design choice — a dedicated base module, not defined inside models.py:
    alembic/env.py imports Base to set target_metadata.
    Each repository module also imports the specific model it needs.
    If Base were defined inside models.py, alembic/env.py would have to
    import models.py entirely just to get Base — coupling the migration
    config to the full model tree. A dedicated base.py is a clean
    dependency target with no side effects.

Design choice — plain DeclarativeBase, no mixins yet:
    Common timestamp columns (created_at, updated_at) are defined on each
    model individually. A TimestampMixin would save repetition but add an
    abstraction layer before it is needed. Sprint 2 prioritises clarity.
    A mixin can be extracted in a future refactor once the pattern is
    established across all models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Root base class for all SQLAlchemy ORM models in Food 'n' Reps."""
    pass
