from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeptMapping(Base):
    __tablename__ = "dept_mapping"
    __table_args__ = (
        UniqueConstraint("external_provider", "external_dept_id", name="uq_provider_dept"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_dept_id: Mapped[str] = mapped_column(String(128), nullable=False)
    internal_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
