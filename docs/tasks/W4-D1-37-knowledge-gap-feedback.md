# Task #37: 知识缺口反馈机制

> **Phase**: 1 末（原任务书 Week 4 Day 1）| **位置**: 与文档治理主线解耦的独立功能
> **预估工时**: 1.5-2 天
> **优先级**: 🟡 中（独立任务，不阻塞主线；越早做越早能积累数据）
> **前置任务**: #67（alembic + db/base.py 就位）
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

RAG 系统上线后必然会遇到「召回不到」「召回了但答非所问」这两类问题。如果没有反馈机制，运营完全靠用户主动汇报——主动汇报率通常 < 5%，大量 Bad Case 沉到水里。

本任务建立**双轨反馈机制**：

1. **被动反馈（自动）**：检索时 `max_score < 阈值` 自动写 `knowledge_gaps` 表，标记"没召回到合适内容"
2. **主动反馈（用户触发）**：前端答案旁 👍/👎 按钮，差评写 `feedback` 表

运营每周拉一次 Top-N 报表，反向驱动**补文档** / **调 prompt** / **改 chunk 策略**。

**完全独立**于文档治理主线（#23-#30）。即使现在只有 5 份 demo 文档，反馈机制照常工作；等 400 份入库后立即能产出价值。

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| #67 已合并 | `git log --oneline \| grep "#67"` | PR 合并到 main |
| alembic 已就位 | `ls backend/alembic.ini backend/migrations/env.py` | 文件存在 |
| db/base.py 已就位 | `cat backend/app/db/base.py` | 含 Base + SessionLocal |
| Q1 schema 已合并 | `git log \| grep "anchor document"` | PR #13 在 main |
| Docker postgres healthy | `docker compose ps postgres` | healthy |
| main 干净 | `git status` | clean |

---

## 3. 任务目标

### 3.1 数据模型
- `knowledge_gaps` 表：低置信度查询自动落库
- `feedback` 表：用户主动差评
- alembic migration `0002_knowledge_gaps_and_feedback.py`

### 3.2 自动检测（被动反馈）
- 在 `services/rag_pipeline.py` 的 `retrieve()` 返回后判断 `max(scores) < settings.low_confidence_threshold`
- 命中阈值：异步写 `knowledge_gaps`（不阻塞查询响应）
- 阈值走 settings，默认 0.5（具体值由 #34 Chunk 调优时再校准）

### 3.3 主动反馈 endpoint
- `POST /api/v1/feedback`：接受 `{query, answer, rating, comment, user_id?}`
- `rating` 枚举：`good` / `bad`
- 好评也收（用来对照 bad case 找 prompt 改进空间）

### 3.4 管理后台 endpoint
- `GET /api/v1/admin/knowledge-gaps/top?since=7d&limit=20`：按相似 query 聚合 Top-N
- `GET /api/v1/admin/feedback/recent?rating=bad&limit=100`：最近差评列表
- 简单聚合即可，复杂分析留给运营外部工具

### 3.5 测试覆盖
- ORM CRUD（integration，要 PG）
- 自动检测阈值逻辑（unit，mock RAG pipeline）
- endpoint 集成测试
- 异步落库不阻塞响应

### 3.6 文档
- `docs/CODEX_QUICK_REF.md` 加"反馈机制"小节
- 不写运营 SOP（那是业务方的事，等数据有了再写）

---

## 4. 输出文件清单

### 4.1 `backend/app/core/config.py`（追加字段）

```python
# Settings 类追加：
low_confidence_threshold: float = 0.5  # max_score < 此值视为知识缺口
```

### 4.2 `backend/.env.example`（追加段落）

```env
# ===== 反馈机制 =====
LOW_CONFIDENCE_THRESHOLD=0.5
```

### 4.3 `backend/app/db/models/knowledge_gap.py`（新建）

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeGap(Base):
    __tablename__ = "knowledge_gaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    query_normalized: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True
    )  # lowercased + trimmed，便于聚合
    user_id: Mapped[str | None] = mapped_column(String(64))
    customer_ctx: Mapped[str | None] = mapped_column(String(64))  # 预留客户上下文
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    top_doc_id: Mapped[str | None] = mapped_column(String(128))  # 召回最优但仍不足的文档
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
```

### 4.4 `backend/app/db/models/feedback.py`（新建）

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Rating(StrEnum):
    GOOD = "good"
    BAD = "bad"


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[Rating] = mapped_column(
        Enum(Rating, name="feedback_rating"), nullable=False, index=True
    )
    comment: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
```

### 4.5 `backend/migrations/versions/0002_knowledge_gaps_and_feedback.py`

`alembic revision --autogenerate -m "knowledge_gaps + feedback"` 生成 + 审。

### 4.6 `backend/app/db/repos/feedback.py`（新建）

CRUD + 聚合查询。

### 4.7 `backend/app/db/repos/knowledge_gap.py`（新建）

CRUD + Top-N 聚合（按 `query_normalized` 聚合 count）。

### 4.8 `backend/app/services/rag_pipeline.py`（修改）

在 `retrieve()` 返回后异步触发知识缺口检测（不阻塞响应）：

```python
# 关键：用 anyio.create_task_group 或 FastAPI BackgroundTasks 异步落库
# 不要 await，不要 try/except 吞，但要 log
```

### 4.9 `backend/app/api/feedback.py`（新建）

```python
"""User feedback endpoint."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.repos import feedback as feedback_repo
from app.models.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    session: AsyncSession = Depends(get_db_session),
) -> FeedbackResponse:
    obj = await feedback_repo.create(session, payload=payload)
    return FeedbackResponse.model_validate(obj)
```

### 4.10 `backend/app/api/admin.py`（新建）

聚合两个 admin endpoint：

- `GET /admin/knowledge-gaps/top`
- `GET /admin/feedback/recent`

Phase 1 阶段不加鉴权，**但要在 spec 注释里明确"Phase 2 #42 ACL 上线后必须挂 admin 权限校验"**。

### 4.11 `backend/app/api/router.py`（修改）

追加：
```python
from app.api import admin, feedback
api_router.include_router(feedback.router)
api_router.include_router(admin.router)
```

### 4.12 `backend/app/api/deps.py`（修改）

追加 `get_db_session` 依赖（从 `SessionLocal()` 拿 session 并自动 close）。

### 4.13 `backend/app/models/feedback.py`（新建 Pydantic）

`FeedbackCreate` / `FeedbackResponse`，对齐 ORM 字段。

### 4.14 测试文件

- `backend/tests/db/test_knowledge_gap.py` (integration)
- `backend/tests/db/test_feedback.py` (integration)
- `backend/tests/services/test_rag_pipeline_gap_detection.py` (unit + mock)
- `backend/tests/api/test_feedback.py` (integration)
- `backend/tests/api/test_admin.py` (integration)

### 4.15 `docs/CODEX_QUICK_REF.md`（新增"反馈机制"小节）

```markdown
## 📢 反馈机制

| 操作 | 方法 |
|------|------|
| 提交差评 | `POST /api/v1/feedback {query, answer, rating: "bad", comment}` |
| 自动捕获知识缺口 | retrieve() max_score < `LOW_CONFIDENCE_THRESHOLD` 自动落库 |
| 查 Top 缺口 | `GET /api/v1/admin/knowledge-gaps/top?since=7d` |
| 查最近差评 | `GET /api/v1/admin/feedback/recent?limit=100` |

**Phase 2 #42 上线后必须给 admin endpoint 挂权限**。
```

---

## 5. 关键实现参考

### 5.1 异步落库（不阻塞查询响应）

`services/rag_pipeline.py` 内：

```python
import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import SessionLocal
from app.db.repos import knowledge_gap as kg_repo


async def _record_knowledge_gap(
    query: str, max_score: float, top_doc_id: str | None
) -> None:
    """异步落知识缺口，失败不抛错（log 即可）。"""
    try:
        async with SessionLocal() as session:
            await kg_repo.create(
                session,
                query=query,
                query_normalized=query.strip().lower()[:512],
                max_score=max_score,
                top_doc_id=top_doc_id,
            )
            await session.commit()
    except Exception as exc:
        logger.warning("Failed to record knowledge gap: {}", exc)


async def retrieve(query: str, *, top_k: int, rerank_n: int) -> list[SourceChunk]:
    sources = await _do_retrieve(query, top_k=top_k, rerank_n=rerank_n)

    # 异步触发缺口检测，不 await
    max_score = max((s.score for s in sources), default=0.0)
    if max_score < settings.low_confidence_threshold:
        top_doc = sources[0].doc_id if sources else None
        asyncio.create_task(_record_knowledge_gap(query, max_score, top_doc))

    return sources
```

**注意**：用 `asyncio.create_task` 而不是 `await`，让落库在后台跑；用 try/except 包住，落库失败绝不影响查询。

### 5.2 Top-N 聚合查询

`db/repos/knowledge_gap.py`：

```python
from datetime import datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge_gap import KnowledgeGap


async def top_gaps(
    session: AsyncSession, *, since: timedelta, limit: int = 20
) -> list[tuple[str, int, float]]:
    """返回 [(query_normalized, count, avg_max_score), ...]。"""
    since_dt = datetime.now() - since
    stmt = (
        select(
            KnowledgeGap.query_normalized,
            func.count(KnowledgeGap.id).label("cnt"),
            func.avg(KnowledgeGap.max_score).label("avg_score"),
        )
        .where(KnowledgeGap.created_at >= since_dt)
        .group_by(KnowledgeGap.query_normalized)
        .order_by(desc("cnt"))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [(row[0], row[1], float(row[2])) for row in result.all()]
```

### 5.3 admin endpoint

`app/api/admin.py`：

```python
"""Admin endpoints. Phase 1 阶段无鉴权；Phase 2 #42 必须挂 ACL。"""

import re
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.repos import feedback as feedback_repo
from app.db.repos import knowledge_gap as kg_repo
from app.models.feedback import FeedbackResponse

router = APIRouter(prefix="/admin", tags=["admin"])

_SINCE_PATTERN = re.compile(r"^(\d+)([dh])$")


def _parse_since(since: str) -> timedelta:
    m = _SINCE_PATTERN.match(since)
    if not m:
        return timedelta(days=7)
    n = int(m.group(1))
    unit = m.group(2)
    return timedelta(days=n) if unit == "d" else timedelta(hours=n)


@router.get("/knowledge-gaps/top")
async def top_knowledge_gaps(
    since: str = Query("7d", description="时间窗口，如 7d / 24h"),
    limit: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict[str, str | int | float]]:
    rows = await kg_repo.top_gaps(session, since=_parse_since(since), limit=limit)
    return [
        {"query": q, "count": c, "avg_max_score": s}
        for q, c, s in rows
    ]


@router.get("/feedback/recent", response_model=list[FeedbackResponse])
async def recent_feedback(
    rating: str | None = Query(None, regex="^(good|bad)$"),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> list[FeedbackResponse]:
    rows = await feedback_repo.recent(session, rating=rating, limit=limit)
    return [FeedbackResponse.model_validate(r) for r in rows]
```

---

## 6. 验收标准

### 6.1 数据库
- [ ] `alembic upgrade head` 创建 2 张新表成功
- [ ] `alembic downgrade -1` 可回滚
- [ ] PG 里能看到 `knowledge_gaps` / `feedback` 表 + 索引

### 6.2 自动检测
- [ ] mock RAG 返回 `max_score=0.4` → `knowledge_gaps` 表多 1 条
- [ ] mock RAG 返回 `max_score=0.8` → `knowledge_gaps` 表无新增
- [ ] 落库异常时查询响应正常（log warn）
- [ ] 查询响应延迟不增加 > 5ms（落库异步）

### 6.3 反馈 endpoint
- [ ] `POST /api/v1/feedback` 接受 bad/good 都成功
- [ ] 无效 rating 返回 422
- [ ] `comment` 可空
- [ ] 返回 201 + 含 id 的 response body

### 6.4 admin endpoint
- [ ] `GET /admin/knowledge-gaps/top?since=7d&limit=10` 返回聚合数据
- [ ] `GET /admin/feedback/recent?rating=bad` 只返回差评
- [ ] `since` 解析 `1d` / `24h` / 无效串（fallback 7d）

### 6.5 静态检查
- [ ] ruff format / check / mypy 全绿
- [ ] coverage 不退化（核心模块 ≥ 85%）

### 6.6 铁律合规
- [ ] 配置走 settings，无硬编码阈值
- [ ] 不直接 import boto3 / dashscope / openai
- [ ] 落库 SQLAlchemy ORM，无裸 SQL

### 6.7 Git / Handoff
- [ ] 分支 `feat/W4-D1-37-knowledge-gap-feedback`
- [ ] commit 含 `Refs: #37`
- [ ] PR title 含 `#37`
- [ ] Handoff §0-§8 完整

---

## 7. 禁止事项

- ❌ 用 `await` 同步等待落库（必须 `asyncio.create_task` 异步）
- ❌ 落库失败抛错给用户（必须 try/except + log）
- ❌ admin endpoint 加 `@lru_cache` 缓存结果（反模式 E1）
- ❌ 给 admin endpoint 加假鉴权（Phase 1 不做鉴权，但要在注释 + Handoff 标 TODO）
- ❌ `query_normalized` 用 `lower()` 跳过 trim（必须 `.strip().lower()`）
- ❌ Feedback `rating` 用 free text（必须 Enum）
- ❌ 把 `low_confidence_threshold` 写死成 0.5（必须 settings 字段）

---

## 8. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| `asyncio.create_task` 任务被 GC 回收 | 落库静默丢失 | 持有 task 引用（FastAPI 用 BackgroundTasks 更稳）|
| `query_normalized` 太长被截 | 索引爆炸 / 唯一性误判 | 限制 512 字符 + 加 index |
| Enum 用字符串比较 | 类型不一致 | `Rating.BAD.value == "bad"` 或永远用 enum 对比 |
| admin endpoint 无分页 | 返回大列表卡死 | 强制 `limit` 上限 200 / 500 |
| 落库阻塞查询响应 | 用户延迟感知 | `asyncio.create_task` + 独立 session |
| `since` 参数注入 | SQL injection | 用正则约束格式 + ORM 参数化（已示例）|
| feedback 表 query+answer 极长 | 单行 MB 级 | Text 字段 OK，但前端要限制长度 |
| autodgenerate 漏 enum type | migration 缺 `feedback_rating` 类型 | 检查 migration 文件确认 `sa.Enum(...)` 出现 |

---

## 9. 参考资料

- SQLAlchemy 2.0 async ORM: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- alembic enum 处理: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- FastAPI BackgroundTasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- 本项目：`docs/tasks/W2-D1-67-idp-abstraction.md`（alembic 初始化在 #67）/ `app/models/document_meta.py`

---

## 10. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 spec + 现有 rag_pipeline 代码 | 30 分钟 |
| config.py + .env.example 加字段 | 15 分钟 |
| db/models/knowledge_gap.py + feedback.py | 30 分钟 |
| alembic autogenerate + 审 migration | 30 分钟 |
| db/repos/knowledge_gap.py + feedback.py | 60 分钟 |
| services/rag_pipeline.py 接入异步检测 | 45 分钟 |
| api/feedback.py + api/admin.py + router 接入 | 60 分钟 |
| models/feedback.py Pydantic | 15 分钟 |
| api/deps.py 加 get_db_session | 15 分钟 |
| 5 个测试文件 | 90 分钟 |
| QUICK_REF 更新 | 15 分钟 |
| Self-Review + Handoff | 60 分钟 |
| 提交 + PR + CI | 20 分钟 |
| **合计** | **~8 小时（1.5-2 工作日）** |

---

## 11. 与下一轮的衔接

#37 完成后：

1. **运营可立刻看到**：哪些查询 RAG 答不好，按 Top-N 排序补文档 / 调 prompt
2. **#34 Chunk 调优时**：用 `low_confidence_threshold` 校准（看真实 max_score 分布）
3. **#42 ACL 上线时**：必须给 `/admin/*` 挂权限校验（spec 注释已标 TODO）
4. **前端 #38 全员测试时**：UI 加 👍/👎 按钮调本 endpoint
5. **数据积累 4 周后**：可起单独任务做"知识缺口报表"前端化

Handoff §7 应说明：

1. `LOW_CONFIDENCE_THRESHOLD` 默认 0.5，待 #34 调优后校准
2. `/admin/*` Phase 1 无鉴权，Phase 2 #42 前必须挂
3. 异步落库失败只 log warn，不影响主流程
4. PG enum type `feedback_rating` 已落库，未来加值需走 alembic 迁移
5. 落 4 周数据后可写一个 dashboard 任务

---

_v1.0 | 任务 ID：#37 | 最后更新：2026-06-05_
