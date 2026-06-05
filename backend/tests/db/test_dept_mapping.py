import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from app.db.base import SessionLocal
from app.db.models.dept_mapping import DeptMapping
from app.db.repos import dept_mapping as dept_mapping_repo

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]


@pytest_asyncio.fixture(autouse=True)
async def clean_dept_mapping() -> None:
    async with SessionLocal() as session:
        await session.execute(delete(DeptMapping))
        await session.commit()


async def test_upsert_creates_new() -> None:
    async with SessionLocal() as session:
        obj = await dept_mapping_repo.upsert(
            session,
            provider="feishu",
            external_dept_id="dept-001",
            internal_code="tech",
            display_name="Technology",
        )
        await session.commit()

        assert obj.id is not None
        assert obj.external_provider == "feishu"
        assert obj.internal_code == "tech"


async def test_upsert_updates_existing() -> None:
    async with SessionLocal() as session:
        first = await dept_mapping_repo.upsert(
            session,
            provider="wecom",
            external_dept_id="dept-002",
            internal_code="sales",
            display_name="Sales",
        )
        await dept_mapping_repo.upsert(
            session,
            provider="wecom",
            external_dept_id="dept-002",
            internal_code="customer_success",
            display_name="Customer Success",
        )
        count = await session.scalar(select(func.count()).select_from(DeptMapping))
        await session.commit()

        assert count == 1
        assert first.internal_code == "customer_success"
        assert first.display_name == "Customer Success"


async def test_get_internal_code_returns_none_for_missing() -> None:
    async with SessionLocal() as session:
        result = await dept_mapping_repo.get_internal_code(
            session,
            provider="feishu",
            external_dept_id="missing",
        )

        assert result is None


async def test_unique_constraint_blocks_duplicate() -> None:
    async with SessionLocal() as session:
        session.add_all(
            [
                DeptMapping(
                    external_provider="feishu",
                    external_dept_id="dept-003",
                    internal_code="finance",
                    display_name="Finance",
                ),
                DeptMapping(
                    external_provider="feishu",
                    external_dept_id="dept-003",
                    internal_code="finance-2",
                    display_name="Finance 2",
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            await session.flush()
