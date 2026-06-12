"""Customer, alias, and product repositories."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.customer import Customer, CustomerAlias, CustomerProduct


async def get_by_external_id(session: AsyncSession, external_id: str) -> Customer | None:
    result = await session.execute(select(Customer).where(Customer.external_id == external_id))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, customer_id: int) -> Customer | None:
    return await session.get(Customer, customer_id)


async def list_all(
    session: AsyncSession,
    *,
    limit: int = 1000,
    offset: int = 0,
) -> list[Customer]:
    result = await session.execute(
        select(Customer).order_by(Customer.id).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


async def upsert(
    session: AsyncSession,
    *,
    external_id: str | None,
    name: str,
    region: str | None = None,
    industry: str | None = None,
    owner_dept: str | None = None,
    notes: str | None = None,
) -> Customer:
    existing = await get_by_external_id(session, external_id) if external_id is not None else None
    if existing is None:
        existing = Customer(external_id=external_id, name=name)
        session.add(existing)
    existing.name = name
    existing.region = region
    existing.industry = industry
    existing.owner_dept = owner_dept
    existing.notes = notes
    await session.flush()
    return existing


async def get_alias_by_value(session: AsyncSession, alias: str) -> CustomerAlias | None:
    result = await session.execute(select(CustomerAlias).where(CustomerAlias.alias == alias))
    return result.scalar_one_or_none()


async def list_aliases(session: AsyncSession, customer_id: int) -> list[CustomerAlias]:
    result = await session.execute(
        select(CustomerAlias)
        .where(CustomerAlias.customer_id == customer_id)
        .order_by(CustomerAlias.alias)
    )
    return list(result.scalars().all())


async def add_alias(
    session: AsyncSession,
    *,
    customer_id: int,
    alias: str,
    source: str = "manual",
    confidence: int = 100,
) -> CustomerAlias:
    obj = CustomerAlias(
        customer_id=customer_id,
        alias=alias,
        source=source,
        confidence=confidence,
    )
    session.add(obj)
    await session.flush()
    return obj


async def get_product(
    session: AsyncSession,
    customer_id: int,
    product_code: str,
) -> CustomerProduct | None:
    result = await session.execute(
        select(CustomerProduct).where(
            CustomerProduct.customer_id == customer_id,
            CustomerProduct.product_code == product_code,
        )
    )
    return result.scalar_one_or_none()


async def list_products(session: AsyncSession, customer_id: int) -> list[CustomerProduct]:
    result = await session.execute(
        select(CustomerProduct)
        .where(CustomerProduct.customer_id == customer_id)
        .order_by(CustomerProduct.product_code)
    )
    return list(result.scalars().all())


async def upsert_product(
    session: AsyncSession,
    *,
    customer_id: int,
    product_code: str,
    product_name: str,
    status: str = "active",
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> CustomerProduct:
    existing = await get_product(session, customer_id, product_code)
    if existing is None:
        existing = CustomerProduct(customer_id=customer_id, product_code=product_code)
        session.add(existing)
    existing.product_name = product_name
    existing.status = status
    existing.started_at = started_at
    existing.ended_at = ended_at
    await session.flush()
    return existing
