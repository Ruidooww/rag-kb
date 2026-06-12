from __future__ import annotations

from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import ARRAY, delete, func, select
from sqlalchemy.exc import IntegrityError

from app.db.base import Base, SessionLocal, engine
from app.db.models.customer import Customer, CustomerAlias, CustomerProduct
from app.db.models.document_meta import DocumentMeta
from app.db.repos import customer as customer_repo
from app.db.repos import document_meta as document_meta_repo
from app.models.customer import DocumentMetaCreate

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


async def _create_customer(
    *,
    external_id: str | None = "crm-001",
    name: str = "上海示例科技有限公司",
) -> Customer:
    async with SessionLocal() as session:
        customer = await customer_repo.upsert(
            session,
            external_id=external_id,
            name=name,
            region="华东",
            industry="软件",
            owner_dept="sales",
        )
        await session.commit()
        return customer


async def test_upsert_creates_new_customer() -> None:
    customer = await _create_customer()

    assert customer.id is not None
    assert customer.external_id == "crm-001"
    assert customer.name == "上海示例科技有限公司"


async def test_upsert_updates_existing_by_external_id() -> None:
    async with SessionLocal() as session:
        first = await customer_repo.upsert(session, external_id="crm-001", name="旧名称")
        updated = await customer_repo.upsert(
            session,
            external_id="crm-001",
            name="新名称",
            region="华南",
        )
        count = await session.scalar(select(func.count()).select_from(Customer))
        await session.commit()

        assert updated.id == first.id
        assert updated.name == "新名称"
        assert updated.region == "华南"
        assert count == 1


async def test_upsert_without_external_id_always_creates_new() -> None:
    async with SessionLocal() as session:
        await customer_repo.upsert(session, external_id=None, name="本地客户")
        await customer_repo.upsert(session, external_id=None, name="本地客户")
        count = await session.scalar(select(func.count()).select_from(Customer))

        assert count == 2


async def test_get_by_external_id_returns_none_if_missing() -> None:
    async with SessionLocal() as session:
        assert await customer_repo.get_by_external_id(session, "missing") is None


async def test_get_by_id_returns_customer() -> None:
    created = await _create_customer()

    async with SessionLocal() as session:
        found = await customer_repo.get_by_id(session, created.id)

        assert found is not None
        assert found.name == created.name


async def test_list_all_paginates() -> None:
    async with SessionLocal() as session:
        for index in range(3):
            await customer_repo.upsert(
                session,
                external_id=f"crm-{index}",
                name=f"客户 {index}",
            )
        await session.commit()

        page = await customer_repo.list_all(session, limit=1, offset=1)

        assert len(page) == 1
        assert page[0].external_id == "crm-1"


async def test_add_alias_links_to_customer() -> None:
    customer = await _create_customer()

    async with SessionLocal() as session:
        alias = await customer_repo.add_alias(
            session,
            customer_id=customer.id,
            alias="示例科技",
            source="manual",
            confidence=95,
        )
        await session.commit()

        assert alias.customer_id == customer.id
        assert alias.confidence == 95


async def test_alias_unique_constraint_rejects_duplicate() -> None:
    customer = await _create_customer()

    async with SessionLocal() as session:
        session.add_all(
            [
                CustomerAlias(customer_id=customer.id, alias="示例科技"),
                CustomerAlias(customer_id=customer.id, alias="示例科技"),
            ]
        )

        with pytest.raises(IntegrityError):
            await session.flush()


async def test_list_aliases_returns_all_for_customer() -> None:
    customer = await _create_customer()

    async with SessionLocal() as session:
        await customer_repo.add_alias(session, customer_id=customer.id, alias="示例科技")
        await customer_repo.add_alias(session, customer_id=customer.id, alias="上海示例")
        await session.commit()

        aliases = await customer_repo.list_aliases(session, customer.id)

        assert [alias.alias for alias in aliases] == ["上海示例", "示例科技"]


async def test_get_alias_by_value_returns_none_if_missing() -> None:
    async with SessionLocal() as session:
        assert await customer_repo.get_alias_by_value(session, "missing") is None


async def test_upsert_product_creates_and_updates() -> None:
    customer = await _create_customer()

    async with SessionLocal() as session:
        created = await customer_repo.upsert_product(
            session,
            customer_id=customer.id,
            product_code="rag-pro",
            product_name="RAG Pro",
        )
        updated = await customer_repo.upsert_product(
            session,
            customer_id=customer.id,
            product_code="rag-pro",
            product_name="RAG Pro Plus",
            status="paused",
        )
        await session.commit()

        assert updated.id == created.id
        assert updated.product_name == "RAG Pro Plus"
        assert updated.status == "paused"


async def test_list_products_returns_customer_products() -> None:
    customer = await _create_customer()

    async with SessionLocal() as session:
        await customer_repo.upsert_product(
            session,
            customer_id=customer.id,
            product_code="rag-pro",
            product_name="RAG Pro",
        )
        await customer_repo.upsert_product(
            session,
            customer_id=customer.id,
            product_code="rag-lite",
            product_name="RAG Lite",
        )
        await session.commit()

        products = await customer_repo.list_products(session, customer.id)

        assert [product.product_code for product in products] == ["rag-lite", "rag-pro"]


async def test_get_product_returns_none_if_missing() -> None:
    customer = await _create_customer()

    async with SessionLocal() as session:
        assert await customer_repo.get_product(session, customer.id, "missing") is None


async def test_cascade_delete_customer_drops_aliases_and_products() -> None:
    customer = await _create_customer()

    async with SessionLocal() as session:
        await customer_repo.add_alias(session, customer_id=customer.id, alias="示例科技")
        await customer_repo.upsert_product(
            session,
            customer_id=customer.id,
            product_code="rag-pro",
            product_name="RAG Pro",
        )
        await session.delete(await session.get(Customer, customer.id))
        await session.commit()

        alias_count = await session.scalar(select(func.count()).select_from(CustomerAlias))
        product_count = await session.scalar(select(func.count()).select_from(CustomerProduct))

        assert alias_count == 0
        assert product_count == 0


async def test_document_meta_upsert_creates_and_updates() -> None:
    customer = await _create_customer()

    async with SessionLocal() as session:
        created = await document_meta_repo.upsert(
            session,
            data=DocumentMetaCreate(
                doc_id="doc-001",
                customer_id=customer.id,
                doc_type="case_study",
                title="示例案例",
                event_date=datetime(2026, 6, 1, tzinfo=UTC),
                storage_key="documents/doc-001",
                owner_dept="sales",
                shared_depts=["tech"],
            ),
        )
        updated = await document_meta_repo.upsert(
            session,
            data=DocumentMetaCreate(
                doc_id="doc-001",
                customer_id=customer.id,
                doc_type="case_study",
                title="示例案例更新",
                storage_key="documents/doc-001-v2",
                owner_dept="sales",
            ),
        )
        await session.commit()

        assert updated.id == created.id
        assert updated.title == "示例案例更新"
        assert updated.storage_key == "documents/doc-001-v2"


async def test_document_meta_get_by_doc_id_returns_none_if_missing() -> None:
    async with SessionLocal() as session:
        assert await document_meta_repo.get_by_doc_id(session, "missing") is None


async def test_document_meta_list_by_customer() -> None:
    customer = await _create_customer()

    async with SessionLocal() as session:
        for index in range(2):
            await document_meta_repo.upsert(
                session,
                data=DocumentMetaCreate(
                    doc_id=f"doc-{index}",
                    customer_id=customer.id,
                    doc_type="case_study",
                    title=f"示例案例 {index}",
                    storage_key=f"documents/doc-{index}",
                    owner_dept="sales",
                ),
            )
        await session.commit()

        docs = await document_meta_repo.list_by_customer(session, customer.id)

        assert [doc.doc_id for doc in docs] == ["doc-0", "doc-1"]


async def test_document_meta_shared_depts_default_empty_list() -> None:
    async with SessionLocal() as session:
        obj = await document_meta_repo.upsert(
            session,
            data=DocumentMetaCreate(
                doc_id="doc-default",
                doc_type="manual",
                title="通用手册",
                storage_key="documents/doc-default",
                owner_dept="tech",
            ),
        )
        await session.commit()

        assert obj.shared_depts == []


async def test_document_meta_acl_5_fields_required() -> None:
    expected_columns = {
        "id",
        "doc_id",
        "customer_id",
        "doc_type",
        "title",
        "event_date",
        "storage_key",
        "status",
        "audience",
        "owner_dept",
        "visibility",
        "sensitivity",
        "shared_depts",
        "extra",
        "created_at",
        "updated_at",
    }
    acl_fields = {"audience", "owner_dept", "visibility", "sensitivity", "shared_depts"}

    assert set(DocumentMeta.__table__.columns.keys()) == expected_columns
    assert acl_fields <= set(DocumentMeta.__table__.columns.keys())
    assert isinstance(DocumentMeta.__table__.columns["shared_depts"].type, ARRAY)
    assert DocumentMeta.__table__.columns["owner_dept"].nullable is True
