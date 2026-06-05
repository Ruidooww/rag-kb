"""dept_mapping CRUD repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dept_mapping import DeptMapping


async def get_internal_code(
    session: AsyncSession,
    *,
    provider: str,
    external_dept_id: str,
) -> str | None:
    stmt = select(DeptMapping.internal_code).where(
        DeptMapping.external_provider == provider,
        DeptMapping.external_dept_id == external_dept_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    *,
    provider: str,
    external_dept_id: str,
    internal_code: str,
    display_name: str,
) -> DeptMapping:
    existing = await session.execute(
        select(DeptMapping).where(
            DeptMapping.external_provider == provider,
            DeptMapping.external_dept_id == external_dept_id,
        )
    )
    obj = existing.scalar_one_or_none()
    if obj is None:
        obj = DeptMapping(
            external_provider=provider,
            external_dept_id=external_dept_id,
            internal_code=internal_code,
            display_name=display_name,
        )
        session.add(obj)
    else:
        obj.internal_code = internal_code
        obj.display_name = display_name
    await session.flush()
    return obj
