from __future__ import annotations

from time import perf_counter
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from app.db.base import Base, SessionLocal, engine
from app.db.models.customer import Customer, CustomerAlias, CustomerProduct
from app.db.models.document_meta import DocumentMeta
from app.db.repos import customer as customer_repo
from app.services import customer_match

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def ensure_customer_master_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(autouse=True)
async def clean_customer_master() -> None:
    async with SessionLocal() as session:
        await session.execute(delete(DocumentMeta))
        await session.execute(delete(CustomerProduct))
        await session.execute(delete(CustomerAlias))
        await session.execute(delete(Customer))
        await session.commit()


async def _seed_customer(
    *,
    external_id: str,
    name: str,
    aliases: tuple[str, ...] = (),
) -> int:
    async with SessionLocal() as session:
        customer = await customer_repo.upsert(session, external_id=external_id, name=name)
        for alias in aliases:
            await customer_repo.add_alias(session, customer_id=customer.id, alias=alias)
        await session.commit()
        return customer.id


async def test_exact_name_match() -> None:
    customer_id = await _seed_customer(
        external_id="crm-001",
        name="上海示例科技有限公司",
    )

    async with SessionLocal() as session:
        results = await customer_match.match(session, "上海示例科技有限公司")

    assert results[0].customer_id == customer_id
    assert results[0].score == 100
    assert results[0].method == "exact"
    assert results[0].matched_alias is None


async def test_alias_exact_match() -> None:
    customer_id = await _seed_customer(
        external_id="crm-001",
        name="上海示例科技有限公司",
        aliases=("示例科技",),
    )

    async with SessionLocal() as session:
        results = await customer_match.match(session, "示例科技")

    assert results[0].customer_id == customer_id
    assert results[0].score == 100
    assert results[0].method == "alias_exact"
    assert results[0].matched_alias == "示例科技"


async def test_fuzzy_match_above_threshold() -> None:
    await _seed_customer(external_id="crm-001", name="上海示例科技有限公司")

    async with SessionLocal() as session:
        results = await customer_match.match(session, "上海示例科技")

    assert results[0].customer_name == "上海示例科技有限公司"
    assert results[0].score >= 80
    assert results[0].method == "fuzzy"


async def test_fuzzy_match_below_threshold_returns_empty() -> None:
    await _seed_customer(external_id="crm-001", name="上海示例科技有限公司")

    async with SessionLocal() as session:
        results = await customer_match.match(session, "完全不相关的客户名")

    assert results == []


async def test_empty_query_returns_empty() -> None:
    async with SessionLocal() as session:
        assert await customer_match.match(session, "  ") == []


async def test_results_sorted_by_score_desc() -> None:
    await _seed_customer(external_id="crm-001", name="上海示例科技有限公司")
    await _seed_customer(external_id="crm-002", name="上海示例技术有限公司")

    async with SessionLocal() as session:
        results = await customer_match.match(
            session,
            "上海示例科技",
            fuzzy_threshold=0,
        )

    assert len(results) == 2
    assert [result.score for result in results] == sorted(
        [result.score for result in results], reverse=True
    )


async def test_default_threshold_and_limit_come_from_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _seed_customer(external_id="crm-001", name="上海示例科技有限公司")
    monkeypatch.setattr(
        customer_match,
        "settings",
        SimpleNamespace(customer_match_fuzzy_threshold=100, customer_match_limit=1),
    )

    async with SessionLocal() as session:
        configured = await customer_match.match(session, "上海示例科")
        overridden = await customer_match.match(
            session,
            "上海示例科",
            fuzzy_threshold=80,
            limit=5,
        )

    assert configured == []
    assert overridden


async def test_fuzzy_match_400_customers_under_50ms_after_warmup() -> None:
    async with SessionLocal() as session:
        for index in range(399):
            await customer_repo.upsert(
                session,
                external_id=f"crm-{index:03d}",
                name=f"虚构客户{index:03d}有限公司",
            )
        await customer_repo.upsert(
            session,
            external_id="crm-target",
            name="上海示例科技有限公司",
        )
        await session.commit()
        await session.execute(select(1))
        await customer_match.match(session, "上海示例科技")

        started = perf_counter()
        results = await customer_match.match(session, "上海示例科技")
        elapsed_ms = (perf_counter() - started) * 1000

    assert results
    assert elapsed_ms < 50
