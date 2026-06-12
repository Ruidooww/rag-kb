from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from anyio import to_thread
from loguru import logger
from sqlalchemy import delete, func, select

from app.db.base import Base, SessionLocal, engine
from app.db.models.customer import Customer, CustomerAlias, CustomerProduct
from app.db.models.document_meta import DocumentMeta
from scripts.init_customer_master import _run

pytestmark = pytest.mark.asyncio(loop_scope="module")
BACKEND_ROOT = Path(__file__).parents[2]


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


def _write_workbook(
    path: Path,
    *,
    customers: list[dict[str, Any]] | None = None,
    aliases: list[dict[str, Any]] | None = None,
) -> None:
    import pandas as pd

    customer_rows = customers or [
        {
            "external_id": "crm-001",
            "name": "上海示例科技有限公司",
            "region": "华东",
            "industry": "软件",
            "owner_dept": "sales",
            "notes": "虚构样本",
        },
        {
            "external_id": "crm-002",
            "name": "北京演示数据有限公司",
            "region": "华北",
            "industry": "数据服务",
            "owner_dept": "sales",
            "notes": "虚构样本",
        },
    ]
    alias_rows = aliases or [
        {
            "external_id": "crm-001",
            "alias": "示例科技",
            "source": "manual",
            "confidence": 100,
        }
    ]
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame(customer_rows).to_excel(writer, sheet_name="customers", index=False)
        pd.DataFrame(alias_rows).to_excel(writer, sheet_name="aliases", index=False)


async def test_init_from_sample_xlsx_creates_all_records(tmp_path: Path) -> None:
    workbook = tmp_path / "customer_master.xlsx"
    _write_workbook(workbook)

    assert await _run(workbook) == 0

    async with SessionLocal() as session:
        customer_count = await session.scalar(select(func.count()).select_from(Customer))
        alias_count = await session.scalar(select(func.count()).select_from(CustomerAlias))

    assert customer_count == 2
    assert alias_count == 1


async def test_init_is_idempotent_on_rerun(tmp_path: Path) -> None:
    workbook = tmp_path / "customer_master.xlsx"
    _write_workbook(workbook)

    assert await _run(workbook) == 0
    assert await _run(workbook) == 0

    async with SessionLocal() as session:
        customer_count = await session.scalar(select(func.count()).select_from(Customer))
        alias_count = await session.scalar(select(func.count()).select_from(CustomerAlias))

    assert customer_count == 2
    assert alias_count == 1


async def test_init_skips_alias_with_unknown_external_id_without_leaking_id(
    tmp_path: Path,
) -> None:
    workbook = tmp_path / "customer_master.xlsx"
    _write_workbook(
        workbook,
        aliases=[
            {
                "external_id": "secret-ext-999",
                "alias": "不可回显别名",
                "source": "manual",
                "confidence": 100,
            }
        ],
    )
    messages: list[str] = []
    sink_id = logger.add(messages.append, format="{message}")
    try:
        assert await _run(workbook) == 0
    finally:
        logger.remove(sink_id)

    async with SessionLocal() as session:
        alias_count = await session.scalar(select(func.count()).select_from(CustomerAlias))

    assert alias_count == 0
    assert "secret-ext-999" not in "".join(messages)
    assert "不可回显别名" not in "".join(messages)


async def test_init_cli_can_import_app_when_run_by_path(tmp_path: Path) -> None:
    result = await to_thread.run_sync(
        lambda: subprocess.run(
            [sys.executable, "scripts/init_customer_master.py", str(tmp_path / "missing.xlsx")],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    )

    assert result.returncode == 1
    assert "ModuleNotFoundError" not in result.stderr


async def test_match_cli_can_import_app_when_run_by_path() -> None:
    result = await to_thread.run_sync(
        lambda: subprocess.run(
            [sys.executable, "scripts/match_customer.py"],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    )

    assert result.returncode == 2
    assert "usage: match_customer.py <query>" in result.stdout
    assert "ModuleNotFoundError" not in result.stderr
