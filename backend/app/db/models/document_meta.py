from __future__ import annotations

from datetime import datetime

from sqlalchemy import ARRAY, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentMeta(Base):
    """Document metadata with the Q1-locked five-field ACL schema."""

    __tablename__ = "document_meta"
    __table_args__ = (
        CheckConstraint(
            "audience IN ('internal_only', 'customer_facing', 'public')",
            name="ck_document_meta_audience",
        ),
        CheckConstraint(
            "visibility IN ('public', 'internal', 'confidential')",
            name="ck_document_meta_visibility",
        ),
        CheckConstraint(
            "sensitivity BETWEEN 1 AND 5",
            name="ck_document_meta_sensitivity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("customer.id", ondelete="SET NULL"), nullable=True, index=True
    )
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    event_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded", index=True)

    audience: Mapped[str] = mapped_column(
        String(32), nullable=False, default="internal_only", index=True
    )
    owner_dept: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    visibility: Mapped[str] = mapped_column(
        String(32), nullable=False, default="internal", index=True
    )
    sensitivity: Mapped[int] = mapped_column(Integer, nullable=False, default=3, index=True)
    shared_depts: Mapped[list[str]] = mapped_column(ARRAY(String(32)), nullable=False, default=list)

    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
