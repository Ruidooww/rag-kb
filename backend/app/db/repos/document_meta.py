"""Document metadata repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.document_meta import DocumentMeta
from app.models.customer import DocumentMetaCreate


async def get_by_doc_id(session: AsyncSession, doc_id: str) -> DocumentMeta | None:
    result = await session.execute(select(DocumentMeta).where(DocumentMeta.doc_id == doc_id))
    return result.scalar_one_or_none()


async def list_by_customer(session: AsyncSession, customer_id: int) -> list[DocumentMeta]:
    result = await session.execute(
        select(DocumentMeta)
        .where(DocumentMeta.customer_id == customer_id)
        .order_by(DocumentMeta.doc_id)
    )
    return list(result.scalars().all())


async def upsert(session: AsyncSession, *, data: DocumentMetaCreate) -> DocumentMeta:
    existing = await get_by_doc_id(session, data.doc_id)
    values = data.model_dump(exclude={"doc_id"})
    if existing is None:
        existing = DocumentMeta(doc_id=data.doc_id, **values)
        session.add(existing)
    else:
        for field, value in values.items():
            setattr(existing, field, value)
    await session.flush()
    return existing
