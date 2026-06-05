# Task #39: API 用量与费用监控基建

> **Phase**: 1 末（原任务书 Week 4 Day 4）| **位置**: 与文档治理主线解耦的独立任务
> **预估工时**: 1-1.5 天
> **优先级**: 🟡 中（独立任务；越早做越早开始积累用量数据，月底分析时才有底）
> **前置任务**: #67（alembic + db/base.py 就位）
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

百炼是按 token 计费的云端 LLM。任务书 §5.2 估算稳态月度 < ¥500，但**没有自动化监控就只能事后翻控制台**——出问题时已经超支或被业务方质疑。

本任务建立**轻量级用量监控基建**：

1. **拦截所有 LLM / Rerank / Embedding 调用** → 在 `services/llm.py` 加 wrapper 记录 input/output token + 费用预估
2. **落 `usage_records` 表**：每次调用一条
3. **管理后台聚合**：`/admin/usage/*` endpoint 看按天 / 按模型 / 按 endpoint 的统计
4. **预算告警基础**：spec 留接口，实际通知（邮件/企微）等后续

**完全独立**于文档治理主线。**越早做越值**——上线一周后就有数据可看，等 #34 调优、#38 全员测试时可以直接对比"调优前后费用变化"。

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| #67 已合并 | `git log --oneline \| grep "#67"` | PR 合并到 main |
| alembic 已就位 | `ls backend/alembic.ini` | 文件存在 |
| db/base.py 已就位 | `cat backend/app/db/base.py` | 含 Base + SessionLocal |
| 现有 LLM 抽象层 | `cat backend/app/services/llm.py` | 含 `get_llm` / `get_embedding` / `get_reranker` |
| Docker postgres healthy | `docker compose ps postgres` | healthy |
| main 干净 | `git status` | clean |

---

## 3. 任务目标

### 3.1 数据模型
- `usage_records` 表：每次模型调用一条
- alembic migration `0003_usage_records.py`

### 3.2 调用拦截
- 在 `services/llm.py` 给 `get_llm` / `get_embedding` / `get_reranker` 返回的对象加 wrapper
- wrapper 拦截调用前后：
  - 调用前：记录开始时间、模型名、endpoint（query/ingest/rerank）
  - 调用后：取 input_tokens / output_tokens / latency
  - 异步写 `usage_records`（不阻塞业务）

### 3.3 费用计算
- `app/services/pricing.py`：定价表（从 config.yaml 或 settings 读）
- 计算公式：`cost = input_tokens * input_price + output_tokens * output_price`
- Rerank 按 query 数计费（按百炼实际计费方式）
- Embedding 按 token 计费

### 3.4 管理后台 endpoint
- `GET /api/v1/admin/usage/summary?since=7d`：总览（总 token、总费用、调用次数）
- `GET /api/v1/admin/usage/by-model?since=7d`：按模型聚合
- `GET /api/v1/admin/usage/by-endpoint?since=7d`：按业务 endpoint 聚合（query / ingest / rerank）
- `GET /api/v1/admin/usage/timeline?since=30d&granularity=day`：按天聚合（出图用）

### 3.5 预算告警接口（占位）
- settings 加 `monthly_budget_cny: float = 500.0`
- 提供 `is_over_budget()` 工具函数（不做实际通知）
- 在 admin summary 响应里返回 `budget_utilization_pct`

### 3.6 测试覆盖
- ORM CRUD
- wrapper 拦截正确性（mock LLM call）
- 费用计算 unit tests
- admin endpoint 集成测试
- 异步落库失败不影响主流程

### 3.7 文档
- `docs/CODEX_QUICK_REF.md` 加"用量监控"小节
- `config.yaml` 加默认定价表（含注释来源链接）

---

## 4. 输出文件清单

### 4.1 `backend/app/core/config.py`（追加字段）

```python
# Settings 类追加：
monthly_budget_cny: float = 500.0   # 月度预算 ¥，超出触发告警
usage_tracking_enabled: bool = True  # 总开关（紧急关闭用）
```

### 4.2 `backend/.env.example`（追加段落）

```env
# ===== 用量监控 =====
MONTHLY_BUDGET_CNY=500.0
USAGE_TRACKING_ENABLED=true
```

### 4.3 `backend/config.yaml`（追加定价表）

```yaml
# ===== LLM / Embedding / Rerank 定价（¥ / 千 token，2026-06 百炼公开价）=====
# 来源：https://help.aliyun.com/zh/model-studio/billing
pricing:
  llm:
    "qwen3.5-omni-flash":
      input:  0.0002    # ¥/1k input tokens
      output: 0.0008    # ¥/1k output tokens
  embedding:
    "bge-m3":
      input: 0.0        # 本地部署，零成本
  rerank:
    "gte-rerank-v2":
      per_query: 0.002  # ¥/次（无论 candidates 多少）
```

### 4.4 `backend/app/db/models/usage_record.py`（新建）

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ModelKind(StrEnum):
    LLM = "llm"
    EMBEDDING = "embedding"
    RERANK = "rerank"


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_kind: Mapped[ModelKind] = mapped_column(
        Enum(ModelKind, name="usage_model_kind"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # query / ingest / rerank
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_cny: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
```

### 4.5 `backend/migrations/versions/0003_usage_records.py`

`alembic revision --autogenerate -m "usage_records"` 生成 + 审。

### 4.6 `backend/app/services/pricing.py`（新建）

```python
"""LLM / Embedding / Rerank 费用计算。

定价表来源：config.yaml 的 pricing 段。
所有费用单位：人民币（¥），保留 6 位小数避免精度丢失。
"""

from __future__ import annotations

from typing import Final

import yaml

from app.core.config import settings
from app.db.models.usage_record import ModelKind

_PRICING_CACHE: dict[str, dict[str, dict[str, float]]] | None = None


def _load_pricing() -> dict[str, dict[str, dict[str, float]]]:
    global _PRICING_CACHE
    if _PRICING_CACHE is None:
        with open(settings.config_yaml_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        _PRICING_CACHE = raw.get("pricing", {})
    return _PRICING_CACHE


def calculate_cost(
    *,
    kind: ModelKind,
    model_name: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    query_count: int = 0,
) -> float:
    """按模型种类计算 ¥ 费用。"""
    pricing = _load_pricing()
    table = pricing.get(kind.value, {}).get(model_name)
    if not table:
        return 0.0  # 未配置定价表 → 0，不抛错（避免主流程崩）

    if kind is ModelKind.RERANK:
        return query_count * table.get("per_query", 0.0)

    # LLM / Embedding 按 token 计费（per 1k tokens）
    input_cost = (input_tokens / 1000) * table.get("input", 0.0)
    output_cost = (output_tokens / 1000) * table.get("output", 0.0)
    return round(input_cost + output_cost, 6)


def is_over_budget(current_month_cost: float) -> bool:
    return current_month_cost >= settings.monthly_budget_cny
```

### 4.7 `backend/app/services/usage_tracker.py`（新建拦截 wrapper）

核心拦截器。完整代码见 §5。

### 4.8 `backend/app/services/llm.py`（修改）

`get_llm` / `get_embedding` / `get_reranker` 返回的对象用 `UsageTracker.wrap()` 包装一层：

```python
from app.services.usage_tracker import UsageTracker

def get_llm() -> OpenAILike:
    llm = OpenAILike(...)
    return UsageTracker.wrap_llm(llm, endpoint="query")  # endpoint 由调用方传
```

**注意**：`endpoint` 字段是业务上下文（"这次调用是给 query 还是 ingest 用的"），需要调用方显式传。

### 4.9 `backend/app/db/repos/usage_record.py`（新建）

CRUD + 聚合查询：
- `create()` 单条写入
- `summary(since)` 总览
- `by_model(since)` 按模型分组
- `by_endpoint(since)` 按业务 endpoint 分组
- `timeline(since, granularity)` 按时间桶分组

### 4.10 `backend/app/api/admin.py`（修改 / 共享）

如果 #37 已合并，**追加** 4 个 usage endpoint 到现有 `admin.py`；否则新建。

### 4.11 `backend/app/models/usage.py`（新建 Pydantic）

`UsageSummary` / `UsageByModel` / `UsageByEndpoint` / `UsageTimelinePoint`。

### 4.12 测试文件

- `backend/tests/services/test_pricing.py` (unit)
- `backend/tests/services/test_usage_tracker.py` (unit + mock LLM)
- `backend/tests/db/test_usage_record.py` (integration)
- `backend/tests/api/test_admin_usage.py` (integration)

### 4.13 `docs/CODEX_QUICK_REF.md`（新增"用量监控"小节）

```markdown
## 💰 用量监控

| 操作 | 方法 |
|------|------|
| 拦截已自动启用 | `get_llm()` 返回的对象已被 wrap |
| 关掉监控 | `USAGE_TRACKING_ENABLED=false` |
| 查总览 | `GET /api/v1/admin/usage/summary?since=7d` |
| 按模型 | `GET /api/v1/admin/usage/by-model?since=7d` |
| 按业务 | `GET /api/v1/admin/usage/by-endpoint?since=7d` |
| 时间轴 | `GET /api/v1/admin/usage/timeline?since=30d&granularity=day` |

**调用方必须传 endpoint 上下文**（query / ingest / rerank）以便按业务归类。

定价表在 `config.yaml#pricing`，调价改 yaml + 重启即生效。
```

---

## 5. `usage_tracker.py` 完整实现参考

```python
"""LLM call interception + usage tracking.

Pattern: 给 services/llm.py 返回的对象套一层 wrapper，拦截 .complete / .embed / .rerank
调用，异步落 usage_records 表。

设计原则：
- 落库失败不影响主流程（try/except + log）
- 总开关 settings.usage_tracking_enabled，紧急情况一秒关停
- 不在拦截器里做复杂业务（保持轻量）
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from loguru import logger

from app.core.config import settings
from app.db.base import SessionLocal
from app.db.models.usage_record import ModelKind, UsageRecord
from app.db.repos import usage_record as usage_repo
from app.services.pricing import calculate_cost


class UsageTracker:
    """Wrapper 工厂。每个 wrap_* 方法返回带拦截能力的对象。"""

    @staticmethod
    def wrap_llm(llm: Any, *, endpoint: str) -> Any:
        """包装 OpenAILike LLM 对象，拦截 .complete / .achat 等方法。"""
        if not settings.usage_tracking_enabled:
            return llm
        return _LLMProxy(llm, endpoint=endpoint)

    @staticmethod
    def wrap_embedding(emb: Any, *, endpoint: str) -> Any:
        if not settings.usage_tracking_enabled:
            return emb
        return _EmbeddingProxy(emb, endpoint=endpoint)

    @staticmethod
    def wrap_reranker(rerank: Any, *, endpoint: str) -> Any:
        if not settings.usage_tracking_enabled:
            return rerank
        return _RerankerProxy(rerank, endpoint=endpoint)


class _BaseProxy:
    """共享异步落库。"""

    def __init__(self, inner: Any, *, endpoint: str) -> None:
        self._inner = inner
        self._endpoint = endpoint

    def __getattr__(self, name: str) -> Any:
        # 默认透传非拦截方法
        return getattr(self._inner, name)

    @staticmethod
    async def _persist(record: UsageRecord) -> None:
        try:
            async with SessionLocal() as session:
                await usage_repo.create_from_record(session, record)
                await session.commit()
        except Exception as exc:
            logger.warning("Failed to persist usage record: {}", exc)


class _LLMProxy(_BaseProxy):
    def complete(self, prompt: str, **kwargs: Any) -> Any:
        start = time.perf_counter()
        success = True
        error_msg: str | None = None
        result = None
        try:
            result = self._inner.complete(prompt, **kwargs)
            return result
        except Exception as exc:
            success = False
            error_msg = str(exc)[:512]
            raise
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            input_tokens = _estimate_tokens(prompt)
            output_tokens = _estimate_tokens(getattr(result, "text", "")) if result else 0
            model_name = getattr(self._inner, "model", "unknown")
            cost = calculate_cost(
                kind=ModelKind.LLM,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
            record = UsageRecord(
                model_kind=ModelKind.LLM,
                model_name=model_name,
                endpoint=self._endpoint,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_cny=cost,
                latency_ms=latency_ms,
                success=success,
                error_message=error_msg,
            )
            asyncio.create_task(self._persist(record))


class _EmbeddingProxy(_BaseProxy):
    # 类似实现，但只算 input_tokens
    ...


class _RerankerProxy(_BaseProxy):
    # 按 query 数计费
    ...


def _estimate_tokens(text: str) -> int:
    """粗估 token 数（中文 1.5 字 ≈ 1 token，英文 4 字符 ≈ 1 token）。

    生产应该用百炼 SDK 的 token counter 或 tiktoken，但为了不引依赖，先用粗估。
    误差 < 20%，对预算告警足够；准确成本以百炼控制台为准。
    """
    return max(1, len(text) // 2)
```

**注意事项**：
1. `_estimate_tokens` 是粗估，spec 注释里要说明"准确数以百炼控制台为准"
2. 真实实现还要处理 `achat` / `acomplete` 等异步方法（spec 留 TODO，由 Codex 按 OpenAILike API 补全）
3. wrapper 用 `__getattr__` 透传所有非拦截方法，避免漏行为

---

## 6. 验收标准

### 6.1 数据库
- [ ] `alembic upgrade head` 创建 `usage_records` 表 + enum type 成功
- [ ] PG 里能看到 4 个索引（model_kind / model_name / endpoint / created_at）

### 6.2 费用计算
- [ ] `calculate_cost(kind=LLM, model="qwen3.5-omni-flash", input=1000, output=500)` 返回正确数值
- [ ] 未配置模型返回 0.0（不抛错）
- [ ] Rerank 按 query_count 计费
- [ ] 浮点数保留 6 位

### 6.3 拦截器
- [ ] mock LLM 调 `complete()`，`usage_records` 多 1 条
- [ ] mock LLM 抛异常，`usage_records` 仍记录（success=false + error_message）
- [ ] `USAGE_TRACKING_ENABLED=false` 时 wrap_llm 返回原对象（不拦截）
- [ ] 主调用延迟不增加 > 5ms（拦截在 finally 异步落库）

### 6.4 admin endpoint
- [ ] `summary` 返回 total_tokens / total_cost / call_count / budget_utilization_pct
- [ ] `by-model` 正确按 model_name 分组
- [ ] `by-endpoint` 正确按 endpoint 分组
- [ ] `timeline?granularity=day` 按天聚合
- [ ] 空数据返回 [] 而非 500

### 6.5 静态检查
- [ ] ruff format / check / mypy 全绿
- [ ] coverage 不退化

### 6.6 铁律合规
- [ ] services/llm.py 返回的对象已 wrap，业务方不需要改调用
- [ ] 配置走 settings + config.yaml，无硬编码
- [ ] 不直接 import dashscope / openai

### 6.7 Git / Handoff
- [ ] 分支 `feat/W4-D4-39-usage-monitoring`
- [ ] commit 含 `Refs: #39`
- [ ] PR title 含 `#39`
- [ ] Handoff §0-§8 完整

---

## 7. 禁止事项

- ❌ 在 wrapper 里 `await` 落库（必须 `asyncio.create_task` 异步）
- ❌ 落库失败抛给调用方（必须 try/except + log）
- ❌ 把定价表硬编码到 `pricing.py`（必须从 config.yaml 读）
- ❌ 拦截时假定方法名（用 `__getattr__` 透传，只显式拦截需要打点的方法）
- ❌ 给 `_estimate_tokens` 写 5 行代码就当准确值（spec 注明粗估 + 控制台校准）
- ❌ admin endpoint 加 `@lru_cache` 缓存（反模式 E1）
- ❌ wrap 后修改 `inner` 对象的状态（保持只读）
- ❌ 给 `usage_records` 表设主键以外的唯一约束（每条调用都得记，重复也得记）

---

## 8. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| `_estimate_tokens` 当准确值用 | 月底对账时差距大 | spec 注释说明粗估 + 季度对账百炼控制台 |
| `__getattr__` 漏掉异步方法 | `acomplete` 不被拦截 | 显式列拦截方法清单（complete/achat/acomplete）|
| LLM 抛错时 `result` 仍引用 | NameError | finally 里先判 `if result is not None` |
| YAML 解析失败导致 import 错 | 整个服务起不来 | `pricing.py` 用 lazy load + 异常时返回空字典 |
| 定价单位混淆（per 1k vs per 1） | 费用差 1000 倍 | 函数命名 + 注释都写明 "per 1k tokens" |
| `usage_records.cost_cny` 用 Float | 浮点精度丢失 | 保留 6 位精度 + 注释；或后续可换 NUMERIC(12,6) |
| `endpoint` 不强制 | 业务归类失败 | wrap_llm 强制传 endpoint 参数 |
| BackgroundTasks 关闭场景丢失记录 | shutdown 时 in-flight 落库丢 | 接受丢失（监控数据非业务关键）|

---

## 9. 参考资料

- 百炼计费说明: https://help.aliyun.com/zh/model-studio/billing
- 百炼 token 计算: https://help.aliyun.com/zh/model-studio/get-started/count-tokens
- LlamaIndex OpenAILike: https://docs.llamaindex.ai/en/stable/api_reference/llms/openai_like/
- tiktoken（如未来想精确算 token）: https://github.com/openai/tiktoken
- 本项目：`docs/tasks/W2-D1-67-idp-abstraction.md`（alembic 基建）/ `docs/tasks/W4-D1-37-knowledge-gap-feedback.md`（admin.py 共用）

---

## 10. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 spec + 看现有 services/llm.py | 30 分钟 |
| config.py / .env.example / config.yaml 加字段 | 30 分钟 |
| db/models/usage_record.py | 20 分钟 |
| alembic autogenerate + 审 migration | 30 分钟 |
| services/pricing.py + 单元测试 | 45 分钟 |
| services/usage_tracker.py 三个 Proxy | 90 分钟 |
| services/llm.py 接入 wrap | 30 分钟 |
| db/repos/usage_record.py（聚合查询）| 60 分钟 |
| api/admin.py 加 4 个 usage endpoint | 60 分钟 |
| Pydantic schemas | 20 分钟 |
| 4 个测试文件 | 90 分钟 |
| QUICK_REF 更新 | 15 分钟 |
| Self-Review + Handoff | 60 分钟 |
| 提交 + PR + CI | 20 分钟 |
| **合计** | **~7-8 小时（1-1.5 工作日）** |

---

## 11. 与下一轮的衔接

#39 完成后：

1. **每周看一次** `/admin/usage/summary?since=7d`，掌握每周费用趋势
2. **#34 Chunk 调优**时，对比"调整 chunk_size 前后 token 总量"——直接体现成本影响
3. **#35 Prompt 调优**时，对比"prompt 长度优化前后 input tokens"
4. **#38 全员测试**期间监控用量异常飙升（说明 prompt / Top-K 设置有问题）
5. **#42 ACL 上线**时给 `/admin/*` 挂权限
6. **每月对账**：从 admin endpoint 拉数据 + 百炼控制台对账，校准 `_estimate_tokens` 的偏差
7. **预算告警**作为后续小任务：超 80% 发邮件 / 企微，超 100% 自动降级（如砍 Top-K）

Handoff §7 应说明：

1. `USAGE_TRACKING_ENABLED=true` 默认开启
2. 关停方式：改 .env 重启
3. token 粗估误差 < 20%，准确以百炼控制台为准
4. 定价表在 `config.yaml#pricing`，调价改 yaml 即可
5. 月度预算 `MONTHLY_BUDGET_CNY=500.0`，超 100% summary 响应 `budget_utilization_pct >= 1.0`
6. 真实告警通知（邮件/企微）待后续任务实现
7. `/admin/usage/*` Phase 1 无鉴权，Phase 2 #42 前必须挂

---

## 12. 与 #37 / #67 的集成点

- **#67 alembic**：本任务的 migration 顺延 0003 编号
- **#67 db/base.py**：复用 SessionLocal + AsyncSession
- **#37 api/admin.py**：如果 #37 已合并，**追加** 4 个 usage endpoint 到现有 `admin.py`，共用 `_parse_since` 工具函数
- **#37 与 #39 都依赖 alembic**：可以并行开发，但 PR 合并顺序 → #37 先 #39 后（或反过来），避免 migration 编号冲突

---

_v1.0 | 任务 ID：#39 | 最后更新：2026-06-05_
