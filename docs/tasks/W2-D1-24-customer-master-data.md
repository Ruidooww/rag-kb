# 任务 #24：客户主数据表 + 别名表 + 模糊匹配脚本

> **版本**：v1.0
> **创建日期**：2026-06-05
> **预估工时**：1.5 工作日
> **前置任务**：#67 IdP 抽象（dept_mapping 已落地）+ #69 CRM 抽象（Customer schema 已冻结）
> **后续任务**：#25 Omni 元数据抽取（依赖本任务的 customer_alias 模糊匹配）
> **优先级**：🔴 高（W2 关键周第一个主线任务，阻塞 #25-#30）

---

## §1 任务背景

W2 是 Phase 1 的关键周——700（实际 400）份文档批量入库 + 元数据准确率 ≥ 95% 是 W2 末的硬节点。任何文档要入库，**必须先在 PG 里有客户主数据**，否则 metadata 抽取拿到的"上海示例科技有限公司"无法对应到内部 customer_id，后续 ACL 注入 / 客户档案查询 / 客户对比 Agent 全部失效。

本任务建立客户主数据 4 张 PG 表 + 模糊匹配工具 + 初始化脚本，是 W2 后续所有数据治理任务的基石。

跟 #67 dept_mapping / #69 CRM 抽象的关系：
- **dept_mapping**（#67 已落地）：外部 IdP 部门 ID → 内部 dept code 映射
- **CRM 抽象**（#69 已落地）：vendor 无关的 customer / contract / contact 接口
- **本任务**：建本地 PG **副本**作为 customer 主数据源，CRM 是数据来源之一（不是唯一）
  - 销售总监维护的 Excel / 历史合同 / 用户手工补 → 也是合法数据源
  - 设计上 `customer.external_id` 跟 CRM 的 customer_id 对应，但**不要求强一致**
  - 别名表纯本地维护，CRM 不一定有

---

## §2 范围

- ✅ 4 张 PG 表：`customer` / `customer_alias` / `customer_product` / `document_meta`
- ✅ alembic migration `0002_customer_master_data.py`（沿用 #67 模式）
- ✅ ORM models + 异步 repos（同 #67 / #69 风格）
- ✅ Pydantic schemas（`models/customer.py`）— 跟 #69 `models/crm.py` 的 `Customer` 字段**对齐**但不重叠（DB 视角 vs API 视角分层）
- ✅ `scripts/match_customer.py` 模糊匹配工具（CLI 可独立跑）
- ✅ `scripts/init_customer_master.py` Excel 初始化脚本
- ✅ 单元测试 + DB 集成测试

- ❌ 不做 CRM 同步（CRM 数据进本地表是 Phase 2 #41 的事）
- ❌ 不做 ACL 中间件（#42）
- ❌ 不做 Qdrant filter 注入（#42 配合做）
- ❌ 不做客户档案 API endpoint（#43）
- ❌ 本任务的脚本不连真实云端 / CRM，只读本地 Excel + 写本地 PG

---

## §3 任务目标

实现完成后必须满足：

1. **4 张表创建 + alembic upgrade/downgrade 双向通过**：在干净 PG 上 `alembic upgrade head` 创建 5 张表（dept_mapping + 本任务 4 张），`alembic downgrade -2`（回到 #67 之前 base）后再 `upgrade head` 必须等价
2. **`scripts/init_customer_master.py` 能从样本 Excel 初始化** ≥ 10 个客户主数据 + ≥ 5 个别名，幂等（重跑不重复插入）
3. **`scripts/match_customer.py` 输入 "上海示例科技" 能命中"上海示例科技有限公司"**（基于 rapidfuzz token sort ratio ≥ 80）
4. **document_meta 表强制 5 字段 ACL schema**（Q1 PR #13 锚定）：`audience` / `owner_dept` / `visibility` / `sensitivity` / `shared_depts`
5. **测试覆盖**：4 个 repo 各 ≥ 3 个测试（get / upsert / not_found）+ 模糊匹配 5 个测试场景 + 初始化脚本幂等性 1 个测试
6. **铁律 grep 全过**：无硬编码 Excel 路径、无 print、无 logging stdlib、无 os.getenv 散落
7. **#69 Customer schema 跟 #24 不冲突**：`models/customer.py` 是 DB 视角（`db_id` / `external_id` / `created_at`）；`models/crm.py` 是 CRM 抽象返回（`id` / `name` / `region`）

---

## §4 文件清单

### 4.1 `backend/app/db/models/customer.py`（新建）

```python
from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Customer(Base):
    """客户主数据。一份客户记录对应可被多种文档/合同关联的实体。"""
    __tablename__ = "customer"
    __table_args__ = (UniqueConstraint("external_id", name="uq_customer_external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_dept: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    aliases: Mapped[list["CustomerAlias"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    products: Mapped[list["CustomerProduct"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class CustomerAlias(Base):
    """客户别名 / 简称 / 历史名 / OCR 误判常见变体。模糊匹配主入口。"""
    __tablename__ = "customer_alias"
    __table_args__ = (UniqueConstraint("alias", name="uq_alias_unique"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="aliases")


class CustomerProduct(Base):
    """客户 - 产品关联。后续合同 / 服务路径 Agent 都依赖这层。"""
    __tablename__ = "customer_product"
    __table_args__ = (UniqueConstraint("customer_id", "product_code", name="uq_customer_product"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="products")
```

### 4.2 `backend/app/db/models/document_meta.py`（新建）

```python
from __future__ import annotations
from datetime import datetime
from sqlalchemy import ARRAY, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class DocumentMeta(Base):
    """文档元数据 + Q1 5 字段 ACL schema。

    Q1 锚定字段（PR #13）：audience / owner_dept / visibility / sensitivity / shared_depts。
    customer_id 可空 — 通用产品文档不绑定具体客户。
    """
    __tablename__ = "document_meta"

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

    # === Q1 5 字段 ACL schema（PR #13 锚定，不许改字段名 / 类型）===
    audience: Mapped[str] = mapped_column(String(32), nullable=False, default="internal", index=True)
    owner_dept: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="internal", index=True)
    sensitivity: Mapped[str] = mapped_column(String(32), nullable=False, default="normal", index=True)
    shared_depts: Mapped[list[str]] = mapped_column(ARRAY(String(32)), nullable=False, default=list)

    extra: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

### 4.3 `backend/migrations/versions/0002_customer_master_data.py`（新建）

按 #67 `0001_dept_mapping.py` 模式手写（先 ORM、后 migration、再用真实 PG 验 upgrade/downgrade）。包含 4 张表 + 唯一约束 + 索引；`document_meta.shared_depts` 用 `postgresql.ARRAY(String(32))`。downgrade 顺序：document_meta → customer_product → customer_alias → customer。

### 4.4 `backend/app/models/customer.py`（新建 — Pydantic API 视角）

```python
from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class AliasSource(StrEnum):
    MANUAL = "manual"
    CRM_SYNC = "crm_sync"
    OMNI_EXTRACT = "omni_extract"


class CustomerSchema(BaseModel):
    """API 视角的 Customer，与 #69 `models/crm.py` 的 Customer 字段对齐但分层。"""
    id: int
    external_id: str | None = None
    name: str
    region: str | None = None
    industry: str | None = None
    owner_dept: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CustomerAliasSchema(BaseModel):
    id: int
    customer_id: int
    alias: str
    source: AliasSource = AliasSource.MANUAL
    confidence: int = Field(ge=0, le=100, default=100)
    created_at: datetime


class CustomerCreate(BaseModel):
    external_id: str | None = None
    name: str
    region: str | None = None
    industry: str | None = None
    owner_dept: str | None = None
    notes: str | None = None


class AliasCreate(BaseModel):
    alias: str
    source: AliasSource = AliasSource.MANUAL
    confidence: int = Field(ge=0, le=100, default=100)


class MatchResult(BaseModel):
    customer_id: int
    customer_name: str
    matched_alias: str | None = None
    score: int = Field(ge=0, le=100)
    method: str  # "exact" / "alias_exact" / "fuzzy"
```

### 4.5 `backend/app/db/repos/customer.py`（新建）

```python
from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.customer import Customer, CustomerAlias, CustomerProduct


async def get_by_external_id(session: AsyncSession, external_id: str) -> Customer | None:
    stmt = select(Customer).where(Customer.external_id == external_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, customer_id: int) -> Customer | None:
    return await session.get(Customer, customer_id)


async def list_all(session: AsyncSession, *, limit: int = 1000, offset: int = 0) -> list[Customer]:
    stmt = select(Customer).order_by(Customer.id).limit(limit).offset(offset)
    result = await session.execute(stmt)
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
    existing: Customer | None = None
    if external_id is not None:
        existing = await get_by_external_id(session, external_id)
    if existing is None:
        existing = Customer(
            external_id=external_id, name=name, region=region,
            industry=industry, owner_dept=owner_dept, notes=notes,
        )
        session.add(existing)
    else:
        existing.name = name
        existing.region = region
        existing.industry = industry
        existing.owner_dept = owner_dept
        existing.notes = notes
    await session.flush()
    return existing


async def list_aliases(session: AsyncSession, customer_id: int) -> list[CustomerAlias]:
    stmt = select(CustomerAlias).where(CustomerAlias.customer_id == customer_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def add_alias(
    session: AsyncSession, *, customer_id: int, alias: str,
    source: str = "manual", confidence: int = 100,
) -> CustomerAlias:
    obj = CustomerAlias(
        customer_id=customer_id, alias=alias, source=source, confidence=confidence
    )
    session.add(obj)
    await session.flush()
    return obj
```

### 4.6 `backend/app/db/repos/document_meta.py`（新建）

按 4.5 模式：`get_by_doc_id` / `list_by_customer` / `upsert`，参数走 Pydantic `DocumentMetaCreate`（schema 在 4.4 同文件，按需扩）。

### 4.7 `backend/app/services/customer_match.py`（新建 — 模糊匹配核心）

```python
"""Customer fuzzy matching service.

匹配优先级（高 → 低）：
1. exact: customer.name 精确等值
2. alias_exact: customer_alias.alias 精确等值
3. fuzzy: rapidfuzz token_sort_ratio（默认阈值 80）— 同时查 customer.name 和 customer_alias.alias
"""
from __future__ import annotations

from typing import Final

from rapidfuzz import fuzz, process
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.customer import Customer, CustomerAlias
from app.models.customer import MatchResult

DEFAULT_FUZZY_THRESHOLD: Final[int] = 80


async def match(
    session: AsyncSession,
    query: str,
    *,
    fuzzy_threshold: int = DEFAULT_FUZZY_THRESHOLD,
    limit: int = 5,
) -> list[MatchResult]:
    """按优先级匹配 customer。返回 score 倒序 list。"""
    q = query.strip()
    if not q:
        return []

    # 1. exact name
    exact = await session.execute(select(Customer).where(Customer.name == q))
    exact_one = exact.scalar_one_or_none()
    if exact_one is not None:
        return [MatchResult(
            customer_id=exact_one.id, customer_name=exact_one.name,
            matched_alias=None, score=100, method="exact",
        )]

    # 2. alias exact
    alias_exact = await session.execute(
        select(CustomerAlias).where(CustomerAlias.alias == q)
    )
    alias_one = alias_exact.scalar_one_or_none()
    if alias_one is not None:
        customer = await session.get(Customer, alias_one.customer_id)
        if customer is not None:
            return [MatchResult(
                customer_id=customer.id, customer_name=customer.name,
                matched_alias=alias_one.alias, score=100, method="alias_exact",
            )]

    # 3. fuzzy — 跨 customer.name + alias 全表扫（400 客户级别可接受）
    all_customers = (await session.execute(select(Customer))).scalars().all()
    all_aliases = (await session.execute(select(CustomerAlias))).scalars().all()
    candidates: dict[str, tuple[int, str | None]] = {}  # text -> (customer_id, alias_or_None)
    for c in all_customers:
        candidates[c.name] = (c.id, None)
    for a in all_aliases:
        candidates.setdefault(a.alias, (a.customer_id, a.alias))

    results = process.extract(
        q, list(candidates.keys()),
        scorer=fuzz.token_sort_ratio, limit=limit,
    )
    matches: list[MatchResult] = []
    for text, score, _ in results:
        if score < fuzzy_threshold:
            continue
        cid, matched_alias = candidates[text]
        customer = await session.get(Customer, cid)
        if customer is None:
            continue
        matches.append(MatchResult(
            customer_id=customer.id, customer_name=customer.name,
            matched_alias=matched_alias, score=int(score), method="fuzzy",
        ))
    return matches
```

### 4.8 `backend/scripts/match_customer.py`（新建 — CLI 工具）

```python
"""CLI: 输入客户名（或别名），输出匹配结果。

用法:
    uv run python scripts/match_customer.py "上海示例科技"
"""
from __future__ import annotations
import asyncio
import sys
from app.db.base import SessionLocal
from app.services.customer_match import match


async def _main(query: str) -> int:
    async with SessionLocal() as session:
        results = await match(session, query)
        if not results:
            print(f"NO_MATCH: {query!r}")  # noqa: T201 — CLI 允许 stdout
            return 1
        for r in results:
            print(f"  [{r.method:11s}] score={r.score:3d}  id={r.customer_id}  name={r.customer_name}"
                  f"  alias={r.matched_alias or '-'}")  # noqa: T201
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: match_customer.py <query>")  # noqa: T201
        sys.exit(2)
    sys.exit(asyncio.run(_main(sys.argv[1])))
```

注：CLI 脚本 `print(...)` 是合理出口（与铁律「禁止 print」相区分），加 `# noqa: T201` 标识。

### 4.9 `backend/scripts/init_customer_master.py`（新建 — Excel 初始化脚本）

```python
"""从 Excel 初始化客户主数据 + 别名。幂等。

用法:
    uv run python scripts/init_customer_master.py data/customer_master_init.xlsx

Excel 格式（sheet 名固定）：
  - sheet "customers": external_id / name / region / industry / owner_dept / notes
  - sheet "aliases":   external_id / alias / source(opt) / confidence(opt)
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

from app.db.base import SessionLocal
from app.db.repos import customer as customer_repo


async def _run(xlsx_path: Path) -> int:
    if not xlsx_path.exists():
        logger.error("Excel not found: {}", xlsx_path)
        return 1

    customers_df = pd.read_excel(xlsx_path, sheet_name="customers")
    aliases_df = pd.read_excel(xlsx_path, sheet_name="aliases")

    async with SessionLocal() as session:
        n_cust = 0
        for row in customers_df.itertuples(index=False):
            await customer_repo.upsert(
                session,
                external_id=getattr(row, "external_id", None) or None,
                name=row.name,
                region=getattr(row, "region", None) or None,
                industry=getattr(row, "industry", None) or None,
                owner_dept=getattr(row, "owner_dept", None) or None,
                notes=getattr(row, "notes", None) or None,
            )
            n_cust += 1

        n_alias = 0
        for row in aliases_df.itertuples(index=False):
            customer = await customer_repo.get_by_external_id(session, row.external_id)
            if customer is None:
                logger.warning("Skip alias: external_id {} not found", row.external_id)
                continue
            existing = await customer_repo.list_aliases(session, customer.id)
            if any(a.alias == row.alias for a in existing):
                continue  # 幂等
            await customer_repo.add_alias(
                session, customer_id=customer.id, alias=row.alias,
                source=getattr(row, "source", "manual") or "manual",
                confidence=int(getattr(row, "confidence", 100) or 100),
            )
            n_alias += 1

        await session.commit()
        logger.info("Initialized: {} customers, {} aliases", n_cust, n_alias)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("usage: init_customer_master.py <xlsx_path>")
        sys.exit(2)
    sys.exit(asyncio.run(_run(Path(sys.argv[1]))))
```

### 4.10 `backend/tests/db/test_customer_repo.py`（新建）

测试场景（≥ 12 项）：
- `test_upsert_creates_new_customer`
- `test_upsert_updates_existing_by_external_id`
- `test_upsert_without_external_id_always_creates_new`
- `test_get_by_external_id_returns_none_if_missing`
- `test_get_by_id_returns_customer`
- `test_add_alias_links_to_customer`
- `test_alias_unique_constraint_rejects_duplicate`
- `test_list_aliases_returns_all_for_customer`
- `test_cascade_delete_customer_drops_aliases`
- `test_list_all_paginates`
- `test_document_meta_acl_5_fields_required`（Q1 schema 守卫）
- `test_document_meta_shared_depts_default_empty_list`

### 4.11 `backend/tests/services/test_customer_match.py`（新建）

测试场景（≥ 6 项）：
- `test_exact_name_match` — "上海示例科技有限公司" → score=100 / method="exact"
- `test_alias_exact_match` — "示例科技" → score=100 / method="alias_exact" / matched_alias 不空
- `test_fuzzy_match_above_threshold` — "上海示例科技" → score ≥ 80 / method="fuzzy"
- `test_fuzzy_match_below_threshold_returns_empty` — "完全不相关的客户名" → []
- `test_empty_query_returns_empty`
- `test_results_sorted_by_score_desc`

### 4.12 `backend/tests/scripts/test_init_customer_master.py`（新建）

- `test_init_from_sample_xlsx_creates_all_records`
- `test_init_is_idempotent_on_rerun`（关键：重跑不重复插入）
- `test_init_skips_alias_with_unknown_external_id`

### 4.13 `backend/pyproject.toml`（修改 — 加依赖）

```toml
[project]
dependencies = [
    # ... 既有 ...
    "rapidfuzz>=3.10",   # 模糊匹配（MIT，纯 C 实现，比 fuzzywuzzy 快 10x）
    "pandas>=2.2",       # Excel 读取（BSD-3）
    "openpyxl>=3.1",     # pandas Excel engine（MIT）
]
```

### 4.14 `backend/data/customer_master_init_sample.xlsx`（新建样本）

提交一个虚构样本（10 customer + 5 alias），文件名加 `_sample` 后缀避免被误当作生产数据。**不允许提交真实客户名**。

### 4.15 `docs/CODEX_QUICK_REF.md`（修改 — 加客户主数据速查段）

简短一段（≤ 15 行）说明：4 张表用途 + 模糊匹配 CLI 怎么跑 + 初始化脚本怎么跑。

---

## §5 验收标准

### 硬指标

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'

# 1. alembic 双向迁移
& uv run alembic downgrade base    # 回到空 DB
& uv run alembic upgrade head      # 应用 0001 + 0002
& uv run alembic downgrade -1      # 回到只有 dept_mapping
& uv run alembic upgrade head      # 再次升级，验证幂等
& uv run alembic current           # 必须输出 0002 (head)

# 2. 单测 + 集成测试
& uv run pytest tests/db/test_customer_repo.py tests/services/test_customer_match.py tests/scripts/test_init_customer_master.py -v
# 必须 ≥ 21 个测试全过

# 3. 全量回归
& uv run pytest -m "not integration" --cov=app --cov-report=term-missing
# 92 → ≥ 113 passed；coverage 不下降（≥ 80%）

# 4. lint + 类型
& uv run ruff check .
& uv run ruff format --check .
& uv run mypy app

# 5. CLI 端到端
& uv run python scripts/init_customer_master.py data/customer_master_init_sample.xlsx
& uv run python scripts/match_customer.py "上海示例科技"
# 应输出 score ≥ 80 的匹配
```

### 软指标

- `models/customer.py` 跟 `models/crm.py` Customer 字段对照表（写在 Handoff §6）
- `customer_alias.alias` 必须有 `index=True` + `UNIQUE`（防别名误重复）
- `document_meta.shared_depts` 用 PostgreSQL `ARRAY(String(32))`，**不是** JSON（查询效率 + GIN 索引兼容）
- `customer_match.match()` 在 400 客户级别的全表扫，性能 < 50ms（pytest benchmark 可选）

---

## §6 风险 & 已知问题

| 风险 | 缓解 |
|------|------|
| `rapidfuzz` 在中文 token 切分不准（如"中国移动"≈"中国电信"分数偏高）| `fuzzy_threshold=80` 是初始值，#27 业务方审核 metadata 时调；保留 `confidence` 字段让人工判断 |
| `pandas.read_excel` 对包含合并单元格 / 公式的 Excel 抛 warning | 样本 Excel 必须扁平结构，业务方提交前必须 audit |
| `document_meta.audience` 跟 `visibility` 字段语义重叠 | Q1 锚定（PR #13）：audience 是"内容面向谁"（客户/员工/公开），visibility 是"DB 行级访问控制"（internal/confidential/public）。两者正交，**不许合并** |
| `customer.external_id` 跟 #69 CRM `customer_id` 不强同步 | 设计如此 — CRM 同步是 Phase 2 #41 范围，本任务仅建容器 |
| 全表扫模糊匹配在 1000+ 客户时性能下降 | 当前 400 客户够用；Phase 3 上线前若超 2000 客户，加 PostgreSQL `pg_trgm` GIN 索引（独立 follow-up）|

### 新增依赖审计

- `rapidfuzz==3.10`：MIT，纯 C 实现，比 fuzzywuzzy 快 10x，无外部依赖
- `pandas==2.2`：BSD-3，必装（# 25 / #26 Excel 处理都依赖）
- `openpyxl==3.1`：MIT，pandas 隐式依赖

所有 license 在 MIT/Apache/BSD/ISC 白名单内。

---

## §7 禁止事项

- ❌ 在 `models/customer.py` 加 `import xiaoshouyi / hubspot / fxiaoke`（铁律 #9 — CRM 同步走 Phase 2 #41）
- ❌ 把 `customer.external_id` 设成 `nullable=False`（设计就是允许本地补录无 CRM ID 的客户）
- ❌ 在 `customer_match.py` 加 `@lru_cache`（ANTIPATTERN E1 — DB 查询不缓存）
- ❌ `print()` 出现在非 CLI 文件（scripts/ 下加 `# noqa: T201` 是允许的特例）
- ❌ `document_meta` 表加除 Q1 5 字段之外的 ACL 字段（强制走 #42 ACL 中间件统一管理）
- ❌ 用 `os.getenv` 读 Excel 路径（必须走 CLI 参数）
- ❌ 在 `init_customer_master.py` 提交**真实客户名**到 git（样本必须虚构）
- ❌ 用 `JSON` 类型存 `shared_depts`（必须用 `ARRAY(String(32))`，GIN 索引兼容）
- ❌ 把 4 张表合并到 #67 `0001_dept_mapping.py`（必须独立 `0002_customer_master_data.py`，下游 #25 / #28 可独立回滚本任务）
- ❌ Sub-agent 并行改 `0002_customer_master_data.py` 跟 ORM model（迁移编号 + ORM 必须主 agent 集中维护，原则 P4）

---

## §8 参考

- `CLAUDE.md` v1.2 § 铁律 #2 (config) / #9 (CRM 抽象边界) + § 原则 P1 (脱敏前置)
- `docs/tasks/W2-D1-67-idp-abstraction.md` § migration / ORM / repo 模式
- `docs/tasks/W2-D3-69-crm-abstraction.md` § Customer schema 对照
- PR #13 commit `9761939` — Q1 ACL 5 字段锚定
- `docs/handoffs/W2-D1-67-handoff.md` § migration 双向验证流程
- rapidfuzz 文档：https://rapidfuzz.github.io/RapidFuzz/

---

_v1.0 | 2026-06-05_


