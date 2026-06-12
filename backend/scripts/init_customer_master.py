"""Initialize local customer master data and aliases from an Excel workbook."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from anyio import to_thread
from loguru import logger
from pydantic import ValidationError

BACKEND_ROOT = Path(__file__).parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.db.base import SessionLocal  # noqa: E402
from app.db.repos import customer as customer_repo  # noqa: E402
from app.models.customer import AliasCreate  # noqa: E402


def _optional_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    normalized = str(value).strip()
    return normalized or None


def _optional_confidence(value: Any) -> int:
    if value is None or pd.isna(value):
        return 100
    return int(value)


def _read_workbook(xlsx_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        pd.read_excel(xlsx_path, sheet_name="customers"),
        pd.read_excel(xlsx_path, sheet_name="aliases"),
    )


async def _run(xlsx_path: Path) -> int:
    if not await to_thread.run_sync(xlsx_path.exists):
        logger.error("Customer master workbook not found")
        return 1

    try:
        customers_df, aliases_df = await to_thread.run_sync(_read_workbook, xlsx_path)
    except (OSError, ValueError):
        logger.error("Customer master workbook could not be read")
        return 1

    async with SessionLocal() as session:
        customer_count = 0
        for row in customers_df.itertuples(index=False):
            external_id = _optional_text(getattr(row, "external_id", None))
            name = _optional_text(getattr(row, "name", None))
            if external_id is None or name is None:
                logger.warning("Skip customer row with missing required fields")
                continue
            await customer_repo.upsert(
                session,
                external_id=external_id,
                name=name,
                region=_optional_text(getattr(row, "region", None)),
                industry=_optional_text(getattr(row, "industry", None)),
                owner_dept=_optional_text(getattr(row, "owner_dept", None)),
                notes=_optional_text(getattr(row, "notes", None)),
            )
            customer_count += 1

        alias_count = 0
        for row in aliases_df.itertuples(index=False):
            external_id = _optional_text(getattr(row, "external_id", None))
            alias_value = _optional_text(getattr(row, "alias", None))
            if external_id is None or alias_value is None:
                logger.warning("Skip alias row with missing required fields")
                continue
            customer = await customer_repo.get_by_external_id(session, external_id)
            if customer is None:
                logger.warning("Skip alias row because customer was not found")
                continue
            existing = await customer_repo.get_alias_by_value(session, alias_value)
            if existing is not None:
                continue
            try:
                alias = AliasCreate(
                    alias=alias_value,
                    source=_optional_text(getattr(row, "source", None)) or "manual",
                    confidence=_optional_confidence(getattr(row, "confidence", None)),
                )
            except (TypeError, ValueError, ValidationError):
                logger.warning("Skip invalid alias row")
                continue
            await customer_repo.add_alias(
                session,
                customer_id=customer.id,
                alias=alias.alias,
                source=alias.source.value,
                confidence=alias.confidence,
            )
            alias_count += 1

        await session.commit()
        logger.info("Initialized {} customers and {} aliases", customer_count, alias_count)
    return 0


if __name__ == "__main__":
    configured_path = Path(settings.customer_master_excel_path)
    workbook_path = Path(sys.argv[1]) if len(sys.argv) >= 2 else configured_path
    sys.exit(asyncio.run(_run(workbook_path)))
