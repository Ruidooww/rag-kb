"""customer master data

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customer",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("industry", sa.String(length=64), nullable=True),
        sa.Column("owner_dept", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", name="uq_customer_external_id"),
    )
    op.create_index("ix_customer_external_id", "customer", ["external_id"], unique=False)
    op.create_index("ix_customer_name", "customer", ["name"], unique=False)
    op.create_index("ix_customer_owner_dept", "customer", ["owner_dept"], unique=False)

    op.create_table(
        "customer_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alias", name="uq_alias_unique"),
    )
    op.create_index("ix_customer_alias_alias", "customer_alias", ["alias"], unique=False)
    op.create_index(
        "ix_customer_alias_customer_id", "customer_alias", ["customer_id"], unique=False
    )

    op.create_table(
        "customer_product",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("product_code", sa.String(length=64), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "product_code", name="uq_customer_product"),
    )
    op.create_index(
        "ix_customer_product_customer_id", "customer_product", ["customer_id"], unique=False
    )
    op.create_index(
        "ix_customer_product_product_code", "customer_product", ["product_code"], unique=False
    )

    op.create_table(
        "document_meta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doc_id", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("doc_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("audience", sa.String(length=32), nullable=False),
        sa.Column("owner_dept", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("sensitivity", sa.String(length=32), nullable=False),
        sa.Column(
            "shared_depts",
            postgresql.ARRAY(sa.String(length=32)),
            nullable=False,
        ),
        sa.Column("extra", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customer.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_meta_audience", "document_meta", ["audience"], unique=False)
    op.create_index("ix_document_meta_customer_id", "document_meta", ["customer_id"], unique=False)
    op.create_index("ix_document_meta_doc_id", "document_meta", ["doc_id"], unique=True)
    op.create_index("ix_document_meta_doc_type", "document_meta", ["doc_type"], unique=False)
    op.create_index("ix_document_meta_owner_dept", "document_meta", ["owner_dept"], unique=False)
    op.create_index("ix_document_meta_sensitivity", "document_meta", ["sensitivity"], unique=False)
    op.create_index("ix_document_meta_status", "document_meta", ["status"], unique=False)
    op.create_index("ix_document_meta_visibility", "document_meta", ["visibility"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_document_meta_visibility", table_name="document_meta")
    op.drop_index("ix_document_meta_status", table_name="document_meta")
    op.drop_index("ix_document_meta_sensitivity", table_name="document_meta")
    op.drop_index("ix_document_meta_owner_dept", table_name="document_meta")
    op.drop_index("ix_document_meta_doc_type", table_name="document_meta")
    op.drop_index("ix_document_meta_doc_id", table_name="document_meta")
    op.drop_index("ix_document_meta_customer_id", table_name="document_meta")
    op.drop_index("ix_document_meta_audience", table_name="document_meta")
    op.drop_table("document_meta")

    op.drop_index("ix_customer_product_product_code", table_name="customer_product")
    op.drop_index("ix_customer_product_customer_id", table_name="customer_product")
    op.drop_table("customer_product")

    op.drop_index("ix_customer_alias_customer_id", table_name="customer_alias")
    op.drop_index("ix_customer_alias_alias", table_name="customer_alias")
    op.drop_table("customer_alias")

    op.drop_index("ix_customer_owner_dept", table_name="customer")
    op.drop_index("ix_customer_name", table_name="customer")
    op.drop_index("ix_customer_external_id", table_name="customer")
    op.drop_table("customer")
