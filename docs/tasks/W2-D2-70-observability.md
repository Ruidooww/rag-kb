# Task #70: 可观测性基建 — trace_id middleware + audit_logs

> **Phase**: 1 末（紧跟 #68）| **位置**: 铁律 #10 4 层防御中的层 4（审计）
> **预估工时**: 1.5-2 天
> **优先级**: 🟡 中（横切关注点，所有功能受益；越早做越早积累审计数据）
> **前置任务**: #67（alembic + db/base.py + User schema）；建议 #68 已合并（白名单变更点 + qdrant PermissionError 抛出点是审计的重要钩子）
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

当前缺一条**贯穿请求生命周期的关联线索**：

- 一次 query 跨 API → Agent → 多个 LlamaIndex 工具 → LLM/Embedding/Rerank → Qdrant → PG 落库
- 出问题时（慢查询 / 召回错 / 越权告警）日志散落各层，靠时间戳人工对齐
- #37 #39 已经在做业务层落库（知识缺口 / 用量），但缺一条 trace_id 把它们串起来

本任务建立**两项轻量基建**：

1. **trace_id middleware**：每个请求生成 UUID4，注入 contextvars；loguru 自动带；所有落库表（`usage_records` / `knowledge_gaps` / `feedback` / `audit_logs`）追加 `trace_id` 字段
2. **audit_logs 表 + 审计装饰器**：敏感操作（登录 / 白名单变更 / CRM 查询 / admin 调用 / 外部 user 越权告警）异步落库

这同时落地 CLAUDE.md 铁律 #10「4 层外部访问防御」中的 **层 4 审计日志**。

**为什么不引 opentelemetry**：30 人公司、本期可观测性需求轻量，opentelemetry 学习曲线 + 运维成本不划算。后期需要分布式 trace 再升级（接口兼容设计：`trace_id` 字段命名与 W3C TraceContext 对齐）。

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| #67 已合并 | `git log --oneline \| grep "#67"` | PR 在 main |
| alembic 就位 | `ls backend/alembic.ini` | exists |
| User schema 含 is_external | `grep "is_external" backend/app/services/auth.py` | hit |
| loguru 已是日志方案 | `grep "loguru" backend/pyproject.toml` | hit |
| main 干净 | `git status` | clean |
| #68 合并状态 | `git log \| grep "#68"` | 建议已合 ；未合也可起，但 §3.5 部分钩子待 #68 收尾 |

---

## 3. 任务目标

### 3.1 trace_id 基础设施
- `backend/app/core/tracing.py`：`trace_id_var: ContextVar[str]`
- FastAPI middleware：每请求生成 UUID4，set 到 contextvar
- 透传：请求头有 `X-Trace-Id` → 复用；否则生成
- 响应头自动带 `X-Trace-Id`
- loguru sink 加 filter 自动注入 `trace_id` 到 log record extra

### 3.2 已有落库表追加 trace_id
- `usage_records` / `knowledge_gaps` / `feedback` 表都加 nullable `trace_id` 字段 + 索引
- migration `0005_audit_logs_and_trace_id.py` 一次性完成（避免多个迁移分散）
- ORM 写入侧默认从 contextvar 读 trace_id 填入

### 3.3 audit_logs 表
- 字段：
  - `id` / `trace_id`（索引）/ `event_type`（StrEnum）/ `severity`（info / warning / critical）
  - `actor_user_id` / `actor_external_provider` / `actor_is_external`（冗余，便于审计不依赖 join）
  - `target_resource`（如 `doc_id:abc123` / `customer_id:xyz`）/ `action`（`create` / `delete` / `read` / ...）
  - `request_path` / `request_method` / `status_code` / `latency_ms`
  - `extra`（JSONB：IP / user_agent / query 截断 256 字 / 其他自由字段）
  - `created_at`（索引）
- `event_type` 枚举：
  - `login` / `logout`
  - `whitelist_grant` / `whitelist_revoke`
  - `crm_query` / `crm_write`
  - `admin_call`
  - `external_breach_alert`（外部 user 触达内部资源）
  - `model_call_error`（LLM/Embedding/Rerank 抛错）

### 3.4 审计装饰器
- `backend/app/core/audit.py`：`@audit(event_type, severity="info", target=lambda req, resp: ...)` 装饰器
- 自动捕获：当前 trace_id / 当前 user（Depends）/ request_path / request_method / latency / status_code
- 业务方只声明 event_type + target，剩下基础设施自动填
- 落库失败不影响主流程（try/except + log warning）
- 用 `asyncio.create_task` 异步落库
- **必须同时支持 sync + async 函数**（PR #15 N5 警告）：用 `inspect.iscoroutinefunction(fn)` 在装饰器内部分发；
  当前 #69 的 no-op `audit.py` 只有 async wrapper（仅适配 CRM async 工具），#70 真实实现切回去时如果只支持 async，
  会导致未来同步审计入口（如 `audit_breach_alert()` 同步通知 / sync admin endpoint / startup-time check）无法装饰。
  实现参考：
  ```python
  def audit(*, event_type, severity=AuditSeverity.INFO, target=None, action=None):
      def decorator(fn):
          if inspect.iscoroutinefunction(fn):
              @functools.wraps(fn)
              async def async_wrapper(*args, **kwargs):
                  result = await fn(*args, **kwargs)
                  asyncio.create_task(_persist_audit(...))
                  return result
              return async_wrapper
          else:
              @functools.wraps(fn)
              def sync_wrapper(*args, **kwargs):
                  result = fn(*args, **kwargs)
                  # sync 路径用 BackgroundTasks / thread pool 落库，不能用 create_task
                  _enqueue_sync_audit(...)
                  return result
              return sync_wrapper
      return decorator
  ```

### 3.5 外部越权告警（铁律 #10 层 4 落地）
- `services/qdrant.PermissionError` 抛出处：同步插一条 `audit_logs` event_type=`external_breach_alert`, severity=`critical`
- `whitelist_admin` 的 POST / DELETE：挂 `@audit(event_type=whitelist_grant / whitelist_revoke)`
- 后续 #69 CRM endpoint 所有 query 必须挂 `@audit(event_type=crm_query)`

### 3.6 admin endpoint
- `GET /api/v1/internal/admin/audit/recent?event_type=&since=7d&limit=100`
- `GET /api/v1/internal/admin/audit/breaches?since=24h`（仅 severity=critical）
- `GET /api/v1/internal/admin/audit/by-trace/{trace_id}`（按 trace_id 拉一次请求的全链路审计）
- 强制挂 internal_router（对接 #68 + 原则 P3）

### 3.7 测试覆盖
- middleware：请求带 X-Trace-Id 透传 / 不带则生成 / 响应头有 X-Trace-Id
- contextvar 跨 async task 正确传递（关键：`asyncio.create_task` 内部能拿到当前 trace_id）
- audit 装饰器：成功 / 失败 / 异常路径都正确落库
- 异步落库失败不影响主响应
- 外部越权告警端到端：mock 外部 user 查内部 collection → 审计表多 1 条 critical
- by-trace endpoint 聚合正确（同 trace_id 的 audit_logs / usage_records / knowledge_gaps 都能拉出来）

### 3.8 文档
- `docs/CODEX_QUICK_REF.md` 加「可观测性」章节（trace_id 用法 + audit 装饰器示例 + 关键 endpoint）

---

## 4. 输出文件清单

### 4.1 `backend/app/core/config.py`（追加字段）

```python
audit_enabled: bool = True
audit_query_text_max_len: int = 256  # query 截断长度
```

### 4.2 `backend/.env.example`（追加段落）

```env
# ===== 可观测性 =====
AUDIT_ENABLED=true
AUDIT_QUERY_TEXT_MAX_LEN=256
```

### 4.3 `backend/app/core/tracing.py`（新建）

完整代码见 §5.1。

### 4.4 `backend/app/core/audit.py`（新建审计装饰器）

完整代码见 §5.2。

### 4.5 `backend/app/db/models/audit_log.py`（新建）

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEventType(StrEnum):
    LOGIN = "login"
    LOGOUT = "logout"
    WHITELIST_GRANT = "whitelist_grant"
    WHITELIST_REVOKE = "whitelist_revoke"
    CRM_QUERY = "crm_query"
    CRM_WRITE = "crm_write"
    ADMIN_CALL = "admin_call"
    EXTERNAL_BREACH_ALERT = "external_breach_alert"
    MODEL_CALL_ERROR = "model_call_error"


class AuditSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    trace_id: Mapped[str | None] = mapped_column(String(36), index=True)
    event_type: Mapped[AuditEventType] = mapped_column(
        Enum(AuditEventType, name="audit_event_type"), nullable=False, index=True
    )
    severity: Mapped[AuditSeverity] = mapped_column(
        Enum(AuditSeverity, name="audit_severity"),
        nullable=False,
        default=AuditSeverity.INFO,
        index=True,
    )
    actor_user_id: Mapped[str | None] = mapped_column(String(64), index=True)
    actor_external_provider: Mapped[str | None] = mapped_column(String(32))
    actor_is_external: Mapped[bool | None] = mapped_column()
    target_resource: Mapped[str | None] = mapped_column(String(256))
    action: Mapped[str | None] = mapped_column(String(32))
    request_path: Mapped[str | None] = mapped_column(String(256))
    request_method: Mapped[str | None] = mapped_column(String(8))
    status_code: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
```

### 4.6 `backend/migrations/versions/0005_audit_logs_and_trace_id.py`

`alembic revision --autogenerate -m "audit_logs + trace_id on existing tables"` 生成，确保 migration 包含：
- 创建 `audit_logs` 表 + 索引
- 创建 enum types `audit_event_type` / `audit_severity`
- 给 `usage_records` / `knowledge_gaps` / `feedback` 追加 nullable `trace_id` 字段 + 索引

### 4.7 `backend/app/db/repos/audit_log.py`（新建）

- `create(session, *, payload)` 单条写入
- `recent(session, *, event_type, since, limit)`
- `breaches(session, *, since, limit)`（severity=critical）
- `by_trace(session, *, trace_id)`

### 4.8 `backend/app/db/repos/{usage_record,knowledge_gap,feedback}.py`（修改）

create 时从 `trace_id_var.get()` 取当前 trace_id 自动填入。

### 4.9 `backend/app/api/audit_admin.py`（新建）

3 个 admin endpoint，挂 `internal_router`。

### 4.10 `backend/app/api/router.py`（修改）

```python
from app.api import audit_admin
internal_router.include_router(audit_admin.router)
```

### 4.11 `backend/app/main.py`（修改）

```python
from app.core.tracing import TraceIdMiddleware, setup_loguru_trace_filter

app = FastAPI(...)
setup_loguru_trace_filter()
app.add_middleware(TraceIdMiddleware)
```

### 4.12 `backend/app/services/qdrant.py`（修改：PermissionError 抛出处加越权告警）

```python
if collection == settings.qdrant_collection_internal and user.is_external:
    from app.core.audit import emit_breach_alert

    asyncio.create_task(emit_breach_alert(
        actor=user, target=f"collection:{collection}", action="search"
    ))
    raise PermissionError(...)
```

### 4.13 `backend/app/api/whitelist_admin.py`（修改：写操作挂装饰器）

```python
@router.post("")
@audit(event_type=AuditEventType.WHITELIST_GRANT, target=lambda req, resp: f"doc_id:{req.doc_id}")
async def grant(...): ...
```

### 4.14 测试文件

- `backend/tests/core/test_tracing.py`
- `backend/tests/core/test_audit.py`
- `backend/tests/db/test_audit_log.py`
- `backend/tests/api/test_audit_admin.py`
- `backend/tests/api/test_breach_alert_e2e.py`

### 4.15 `docs/CODEX_QUICK_REF.md`（新增「可观测性」章节）

```markdown
## 🔭 可观测性

| 操作 | 方法 |
|------|------|
| 拿当前 trace_id | `from app.core.tracing import trace_id_var; trace_id_var.get()` |
| 透传上游 trace_id | 请求带 `X-Trace-Id: <uuid>` header |
| 日志自动带 trace_id | loguru 已配 filter，业务代码 `logger.info(...)` 即可 |
| 给 endpoint 加审计 | `@audit(event_type=AuditEventType.X, target=...)` |
| 查最近审计 | `GET /api/v1/internal/admin/audit/recent?event_type=login&since=7d` |
| 查越权告警 | `GET /api/v1/internal/admin/audit/breaches?since=24h` |
| 按 trace_id 串全链路 | `GET /api/v1/internal/admin/audit/by-trace/{trace_id}` |

紧急关停审计：`AUDIT_ENABLED=false`（仅紧急，业务复盘会丢数据）。
```

---

## 5. 关键实现参考

### 5.1 `app/core/tracing.py`

```python
"""trace_id 基础设施：contextvar + middleware + loguru filter。"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

_HEADER = "X-Trace-Id"


def _new_trace_id() -> str:
    return str(uuid.uuid4())


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(_HEADER)
        trace_id = incoming if incoming else _new_trace_id()
        token = trace_id_var.set(trace_id)
        try:
            response: Response = await call_next(request)
        finally:
            trace_id_var.reset(token)
        response.headers[_HEADER] = trace_id
        return response


def setup_loguru_trace_filter() -> None:
    """让 loguru 自动把当前 trace_id 注入到每条 log 的 extra。"""
    def _patcher(record):
        record["extra"]["trace_id"] = trace_id_var.get() or "-"

    logger.configure(patcher=_patcher)
```

**关键**：`asyncio.create_task` 会复制当前 contextvars，所以异步落库 task 内部 `trace_id_var.get()` 仍是原 trace_id。

### 5.2 `app/core/audit.py`

```python
"""审计装饰器 + 越权告警。

设计原则：
- 业务方只声明 event_type + target，剩下基础设施自动填
- 落库失败不影响主流程
- 用 asyncio.create_task 异步
- 默认 severity=info，越权告警显式传 critical
"""

from __future__ import annotations

import asyncio
import time
from functools import wraps
from typing import Any, Callable

from fastapi import Request
from loguru import logger

from app.core.config import settings
from app.core.tracing import trace_id_var
from app.db.base import SessionLocal
from app.db.models.audit_log import AuditEventType, AuditLog, AuditSeverity
from app.db.repos import audit_log as audit_repo
from app.services.auth import User


async def _persist(payload: dict[str, Any]) -> None:
    try:
        async with SessionLocal() as session:
            await audit_repo.create(session, payload=payload)
            await session.commit()
    except Exception as exc:
        logger.warning("audit persist failed: {}", exc)


def audit(
    *,
    event_type: AuditEventType,
    severity: AuditSeverity = AuditSeverity.INFO,
    target: Callable[..., str] | None = None,
    action: str | None = None,
):
    """挂在 FastAPI endpoint 上，自动捕获 user / path / latency / status。

    target: lambda(*args, **kwargs) -> str，从入参里拼出资源标识。
    """
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            if not settings.audit_enabled:
                return await fn(*args, **kwargs)

            start = time.perf_counter()
            request: Request | None = next(
                (a for a in args if isinstance(a, Request)),
                kwargs.get("request"),
            )
            user: User | None = kwargs.get("user")
            status_code = 200
            try:
                result = await fn(*args, **kwargs)
                return result
            except Exception as exc:
                status_code = getattr(exc, "status_code", 500)
                raise
            finally:
                latency_ms = int((time.perf_counter() - start) * 1000)
                payload = {
                    "trace_id": trace_id_var.get() or None,
                    "event_type": event_type,
                    "severity": severity,
                    "actor_user_id": user.user_id if user else None,
                    "actor_external_provider": user.external_provider if user else None,
                    "actor_is_external": user.is_external if user else None,
                    "target_resource": target(*args, **kwargs) if target else None,
                    "action": action,
                    "request_path": request.url.path if request else None,
                    "request_method": request.method if request else None,
                    "status_code": status_code,
                    "latency_ms": latency_ms,
                    "extra": None,
                }
                asyncio.create_task(_persist(payload))

        return wrapper
    return decorator


async def emit_breach_alert(*, actor: User, target: str, action: str) -> None:
    """外部 user 触达内部资源 → critical 告警。"""
    payload = {
        "trace_id": trace_id_var.get() or None,
        "event_type": AuditEventType.EXTERNAL_BREACH_ALERT,
        "severity": AuditSeverity.CRITICAL,
        "actor_user_id": actor.user_id,
        "actor_external_provider": actor.external_provider,
        "actor_is_external": actor.is_external,
        "target_resource": target,
        "action": action,
        "request_path": None,
        "request_method": None,
        "status_code": 403,
        "latency_ms": None,
        "extra": None,
    }
    await _persist(payload)
    logger.warning(
        "EXTERNAL BREACH: user={} target={} action={}",
        actor.user_id, target, action,
    )
```

---

## 6. 验收标准

### 6.1 trace_id middleware
- [ ] 请求带 `X-Trace-Id: abc` → 响应头同值 + log 中出现 abc
- [ ] 请求不带 → 生成 UUID4 + 响应头返回 + log 出现该 ID
- [ ] `asyncio.create_task` 内部 `trace_id_var.get()` 仍是父请求 trace_id

### 6.2 已有表加 trace_id
- [ ] `usage_records` / `knowledge_gaps` / `feedback` 都新增 nullable `trace_id` + 索引
- [ ] 写入时自动填 contextvar 值
- [ ] migration up / down 都成功

### 6.3 audit_logs 表
- [ ] `alembic upgrade head` 创建表 + 2 个 enum types + 4 个索引
- [ ] CRUD integration tests 全绿

### 6.4 审计装饰器
- [ ] 装饰 endpoint，正常返回 → 落库 1 条 status=200
- [ ] 装饰 endpoint 抛 401 → 落库 1 条 status=401
- [ ] 装饰 endpoint 抛 500 → 落库 1 条 status=500
- [ ] AUDIT_ENABLED=false → 落库 0 条（透传调用）

### 6.5 越权告警
- [ ] mock 外部 user 调 `services/qdrant.search(internal)` → audit_logs 多 1 条 critical
- [ ] event_type=`external_breach_alert`，target_resource 含 collection 名

### 6.6 admin endpoint
- [ ] `recent` 按 event_type 过滤可用
- [ ] `breaches` 仅返回 severity=critical
- [ ] `by-trace/{trace_id}` 返回该 trace 全部 audit + 关联表（usage / kg / feedback）

### 6.7 静态检查
- [ ] ruff / mypy 全绿
- [ ] coverage 不退化

### 6.8 铁律合规
- [ ] 落地铁律 #10 层 4
- [ ] audit endpoint 强制挂 internal_router（对接原则 P3）
- [ ] 配置走 settings

### 6.9 Git / Handoff
- [ ] 分支 `feat/W2-D2-70-observability`
- [ ] commit 含 `Refs: #70`
- [ ] PR title 含 `#70`
- [ ] Handoff §0-§8 完整

---

## 7. 禁止事项

- ❌ 用 `threading.local` 替代 `ContextVar`（async 不安全）
- ❌ 在 middleware 里 `await` 落库（不阻塞响应）
- ❌ 装饰器同步落库（必须 `asyncio.create_task`）
- ❌ 落库失败抛错（必须 try/except + log）
- ❌ 把 audit_logs 表设其他唯一约束（每条都得记）
- ❌ 在装饰器里读取 `request.body()`（会破坏后续 endpoint 读流）
- ❌ admin/audit endpoint 挂到 `/public/*` 或顶层 router
- ❌ trace_id 字段类型用 int / 自增（必须 UUID 字符串，便于跨系统）
- ❌ 引入 opentelemetry（保持轻量自建）
- ❌ 装饰器吞异常不重抛（必须 `raise`，只是在 finally 里捕快照）

---

## 8. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| contextvar 在线程池中丢失 | trace_id 为空 | FastAPI 默认在主事件循环 OK；线程池要手动 copy |
| `asyncio.create_task` 任务被 GC | 异步落库静默丢 | task 即时 schedule + log warning 保留 |
| `Request.body()` 在装饰器读 | endpoint 拿不到 body | 不读 body，只取 path/method/headers |
| middleware 顺序错 | trace_id 没生效就被 log | TraceIdMiddleware 必须最先 add |
| loguru patcher 全局生效 | 测试间互相污染 | 测试用 fixture reset patcher |
| audit_logs.extra JSONB 写非可序列化对象 | 落库报错 | 写入前 json.dumps 试转 / 仅放原始类型 |
| 越权告警同步落库阻塞 raise | 用户感知慢 | emit_breach_alert 也走 asyncio.create_task |
| `trace_id_var` 默认空字符串 vs None | 索引膨胀 | 入库时空串转 None |

---

## 9. 参考资料

- Python contextvars: https://docs.python.org/3/library/contextvars.html
- Starlette middleware: https://www.starlette.io/middleware/
- loguru patcher: https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.configure
- W3C TraceContext（trace_id 命名对齐）: https://www.w3.org/TR/trace-context/
- 本项目：`CLAUDE.md` 铁律 #10 / 原则 P3 / `docs/tasks/W2-D1-68-external-isolation.md`

---

## 10. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 spec + 现有 main / loguru 配置 | 30 分钟 |
| config.py + .env.example | 15 分钟 |
| core/tracing.py + middleware | 60 分钟 |
| loguru patcher 接入 + 验证日志格式 | 30 分钟 |
| db/models/audit_log.py + enum types | 30 分钟 |
| alembic migration (audit_logs + trace_id on 3 tables) | 60 分钟 |
| 3 个已有 repo 加 trace_id 自动填 | 45 分钟 |
| db/repos/audit_log.py（CRUD + 聚合）| 60 分钟 |
| core/audit.py 装饰器 + emit_breach_alert | 90 分钟 |
| qdrant.py PermissionError 处加告警 | 30 分钟 |
| whitelist_admin / admin endpoint 挂装饰器 | 30 分钟 |
| api/audit_admin.py 三个 endpoint | 60 分钟 |
| 5 个测试文件 | 150 分钟 |
| QUICK_REF 更新 | 15 分钟 |
| Self-Review + Handoff | 75 分钟 |
| 提交 + PR + CI | 20 分钟 |
| **合计** | **~12 小时（1.5-2 工作日）** |

---

## 11. 与下一轮的衔接

#70 完成后：

1. **#69 CRM endpoint**：所有 endpoint 必须挂 `@audit(event_type=crm_query)` 或 `crm_write`
2. **#42 ACL 中间件**：ACL 拒绝时也应落 `external_breach_alert` 或新增 `acl_denied` event_type
3. **数据积累 4 周后**：起 dashboard 任务可视化越权告警 / 用量趋势 / 慢查询
4. **预算告警（#39 后续）**：可用 by-trace 反查超额请求溯源
5. **正式接入 opentelemetry**：trace_id 字段命名已对齐 W3C TraceContext，未来切换零业务改动

Handoff §7 应说明：

1. trace_id 在 `asyncio.create_task` 内部仍可读（contextvars 自动 copy 验证过）
2. AUDIT_ENABLED=false 仅紧急用，复盘会丢数据
3. audit_logs 表是 append-only，不要做更新；过期数据按月分区或冷备（后续）
4. by-trace endpoint 跨表聚合，单 trace 数据量大时需分页
5. 装饰器 target lambda 拼接资源标识，长度限制 256 字（DB 字段约束）

---

## 12. 与 #67 / #68 / #37 / #39 的集成点

- **#67 User.is_external**：装饰器与 emit_breach_alert 都消费 `user.is_external` 字段
- **#68 services/qdrant.PermissionError**：抛出处加 `emit_breach_alert`（本任务实现）；如 #68 未合，本任务先建 emit 接口，由 #68 PR 接入
- **#68 whitelist_admin**：grant / revoke endpoint 挂 audit 装饰器
- **#37 知识缺口落库**：repo 自动填 trace_id（本任务统一改）
- **#39 用量记录落库**：repo 自动填 trace_id（本任务统一改）
- **#39 admin/usage/* + #37 admin/* + 本任务 admin/audit/***：共用 internal_router
- **migration 编号**：#67=0001 / #68=0002 / #37=0003 / #39=0004 / 本任务=0005

---

_v1.0 | 任务 ID：#70 | 最后更新：2026-06-05_
