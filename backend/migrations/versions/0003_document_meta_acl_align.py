"""align document_meta ACL contract

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE document_meta SET audience = 'internal_only' WHERE audience = 'internal'")
    )
    op.alter_column(
        "document_meta",
        "owner_dept",
        existing_type=sa.String(length=32),
        nullable=True,
    )
    op.alter_column(
        "document_meta",
        "sensitivity",
        existing_type=sa.String(length=32),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="CASE WHEN sensitivity = 'normal' THEN 3 ELSE 3 END",
    )
    op.create_check_constraint(
        "ck_document_meta_audience",
        "document_meta",
        "audience IN ('internal_only', 'customer_facing', 'public')",
    )
    op.create_check_constraint(
        "ck_document_meta_visibility",
        "document_meta",
        "visibility IN ('public', 'internal', 'confidential')",
    )
    op.create_check_constraint(
        "ck_document_meta_sensitivity",
        "document_meta",
        "sensitivity BETWEEN 1 AND 5",
    )


def downgrade() -> None:
    op.drop_constraint("ck_document_meta_sensitivity", "document_meta", type_="check")
    op.drop_constraint("ck_document_meta_visibility", "document_meta", type_="check")
    op.drop_constraint("ck_document_meta_audience", "document_meta", type_="check")
    op.execute(sa.text("UPDATE document_meta SET owner_dept = '' WHERE owner_dept IS NULL"))
    op.alter_column(
        "document_meta",
        "owner_dept",
        existing_type=sa.String(length=32),
        nullable=False,
    )
    op.alter_column(
        "document_meta",
        "sensitivity",
        existing_type=sa.Integer(),
        type_=sa.String(length=32),
        existing_nullable=False,
        postgresql_using="'normal'",
    )
    op.execute(
        sa.text("UPDATE document_meta SET audience = 'internal' WHERE audience = 'internal_only'")
    )
