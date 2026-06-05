"""dept_mapping

Revision ID: 0001
Revises:
Create Date: 2026-06-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dept_mapping",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_provider", sa.String(length=32), nullable=False),
        sa.Column("external_dept_id", sa.String(length=128), nullable=False),
        sa.Column("internal_code", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_provider", "external_dept_id", name="uq_provider_dept"),
    )
    op.create_index(
        "ix_dept_mapping_external_provider",
        "dept_mapping",
        ["external_provider"],
        unique=False,
    )
    op.create_index(
        "ix_dept_mapping_internal_code",
        "dept_mapping",
        ["internal_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dept_mapping_internal_code", table_name="dept_mapping")
    op.drop_index("ix_dept_mapping_external_provider", table_name="dept_mapping")
    op.drop_table("dept_mapping")
