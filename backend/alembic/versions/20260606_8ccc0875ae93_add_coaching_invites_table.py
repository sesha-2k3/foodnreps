"""add_coaching_invites_table

Revision ID: 8ccc0875ae93
Revises: '2bc06fa16cbd'
Create Date: 2026-06-06 17:43:02.911791+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# Revision identifiers used by Alembic.
revision: str = "8ccc0875ae93"
down_revision: Union[str, None] = "2bc06fa16cbd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coaching_invites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("staff_id", sa.UUID(), nullable=False),
        sa.Column(
            "staff_role",
            postgresql.ENUM(
                "fitness_trainer",
                "nutritionist",
                "master_coach",
                name="staff_role_enum",
                create_type=False,  # enum already exists
            ),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=8), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["staff_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("idx_invites_code", "coaching_invites", ["code"])
    op.create_index(
        "idx_invites_staff_id", "coaching_invites", ["staff_id", "expires_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_invites_staff_id", table_name="coaching_invites")
    op.drop_index("idx_invites_code", table_name="coaching_invites")
    op.drop_table("coaching_invites")
    # Do NOT drop staff_role_enum — it belongs to other tables too
