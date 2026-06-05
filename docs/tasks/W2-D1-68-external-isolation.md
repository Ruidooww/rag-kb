# Task #68: 外部访问隔离 — external_whitelist + 双 Qdrant collection + 内外路由分流

> **Phase**: 1 末（紧跟 #67）| **位置**: Phase 2 #42 ACL 的物理隔离底座
> **预估工时**: 2-2.5 天
> **优先级**: 🔴 高（决定外部访问安全模型；早做早积累测试数据）
> **前置任务**: #67（User.is_external 字段 + alembic 就位）
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

#67 已经在身份层加了 `User.is_external` 标记。本任务把这个标记**贯穿到数据访问层 + 路由层**，落地 CLAUDE.md 铁律 #10 的「4 层外部访问防御」中的 **层 1（数据隔离）** 和 **层 3（API 路由物理隔离）**。

核心架构决策（已与业务方对齐）：

- **A 方案**：外部可见文档维护一张 `external_whitelist`（白名单，doc_id 粒度）
- **B 方案**：双 Qdrant collection（`docs_internal` / `docs_public`），白名单变更触发增量同步
- **A + B 双保险**：业务代码查 `docs_public` 时已经物理上看不到内部文档；即使 LLM 越权请求 doc_id，rerank / fetch 层再校验白名单
- **路由分流**：FastAPI 拆 `internal_router` / `public_router`，admin / CRM / 内部 search 只挂 internal，公众号端点只挂 public

**为什么不靠 Qdrant payload filter**：filter 是软约束，依赖业务代码每次都加 `is_external` 条件——一旦漏一处就泄露。物理分 collection 是硬约束，错不了。

**为什么要白名单而非黑名单**：默认拒绝，显式放行。新文档入库后默认仅内部可见，业务方明确标"对外可见"后才进白名单 → 同步到 `docs_public`。

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| #67 已合并 | `git log --oneline \| grep "#67"` | PR 在 main |
| User.is_external 字段存在 | `grep "is_external" backend/app/services/auth.py` | hit |
| alembic 就位 | `ls backend/alembic.ini` | 文件存在 |
| 双 Qdrant collection 决策已确认 | 见 §1 | OK |
| 内部 Qdrant collection 已可用 | `curl localhost:6333/collections` | `docs_internal` 存在或可创建 |
| main 干净 | `git status` | clean |

---

## 3. 任务目标

### 3.1 数据模型 + migration
- `external_whitelist` 表（每行 = 一篇对外可见文档）
- alembic migration `0002_external_whitelist.py`
- 字段：`doc_id` / `audience`（reserved 多渠道，先固定 `customer_facing`）/ `approved_by` / `approved_at` / `revoked_at` / `notes`

### 3.2 双 Qdrant collection 基建
- `docs_internal`：现有 collection 重命名（如果当前叫 `docs`），所有文档入这里
- `docs_public`：新建，schema 与 internal 完全一致（同 dim / 同 payload schema）
- 创建脚本：`backend/scripts/setup_qdrant_collections.py`（幂等，可重复跑）

### 3.3 白名单 → docs_public 同步
- `services/external_sync.py`：核心同步逻辑
- 触发点：
  1. `external_whitelist` 表新增/撤销 → 触发器（应用层，PG trigger 不绑死 PG）
  2. 手动全量重建：`backend/scripts/rebuild_public_collection.py`
- 同步语义：白名单加 → 从 `docs_internal` 拉 vectors + payload → upsert 到 `docs_public`
- 白名单撤销 → 从 `docs_public` 删除对应 point
- **不在 docs_public 存任何内部专用 payload 字段**（dept_code / visibility 等照常带，但服务层强制 visibility=PUBLIC 才同步）

### 3.4 路由分流（落地原则 P3）
- `backend/app/api/router.py` 重构：
  ```python
  api_router = APIRouter(prefix="/api/v1")                    # 中性
  internal_router = APIRouter(prefix="/api/v1/internal")      # 仅员工
  public_router = APIRouter(prefix="/api/v1/public")          # 仅外部
  ```
- 已有 endpoint 重新归类：
  - `auth/login` → 中性（顶层）
  - `feedback` → 中性
  - `admin/*`（#37 #39 产出的）→ internal
  - 未来 #69 CRM endpoint → internal
  - 未来公众号 query endpoint → public
- main app 各自 mount

### 3.5 公众号 query endpoint 占位
- `backend/app/api/public_query.py`：`POST /api/v1/public/query`
- 实现仅查 `docs_public` collection
- 调用 Agent 时**强制**注入 `EXTERNAL_TOOLS`（用 #67 的 `user.is_external=True` 标记）
- 当前 Agent 工具集还没分（Phase 2+），暂用 stub Agent + log warning「需补 EXTERNAL_TOOLS 落地」

### 3.6 白名单管理 endpoint（internal）
- `POST /api/v1/internal/external-whitelist`：加白名单（admin role 校验后续 #42 补）
- `DELETE /api/v1/internal/external-whitelist/{doc_id}`：撤销
- `GET /api/v1/internal/external-whitelist?audience=customer_facing&limit=100`：列表
- 每次写操作同步触发 §3.3 sync（异步任务，不阻塞响应）

### 3.7 防御层 2：工具/服务层二次校验
- `services/qdrant.py` 加 `search(collection, ..., user)` 入口
- 内部 collection 调用：`if user.is_external: raise PermissionError`
- 公开 collection 调用：always allow
- 即使路由分流被绕，业务层兜底

### 3.8 测试覆盖
- ORM CRUD（integration）
- 同步逻辑：加白名单 → `docs_public` 点位+1
- 撤销白名单 → `docs_public` 点位-1
- 重复加同 doc_id（幂等）
- `services/qdrant.py` 二次校验：外部 user 查 `docs_internal` 抛 PermissionError
- 路由分流：外部 user 触达 `/internal/*` → 401/403
- 端到端：起 public_query → 只查 docs_public

### 3.9 文档
- `docs/CODEX_QUICK_REF.md` 加「外部访问隔离」章节
- 更新 `docs/architecture.md`（如已存在）的数据流图

---

## 4. 输出文件清单

### 4.1 `backend/app/core/config.py`（追加字段）

```python
qdrant_collection_internal: str = "docs_internal"
qdrant_collection_public: str = "docs_public"
external_audience_default: str = "customer_facing"
```

### 4.2 `backend/.env.example`（追加段落）

```env
# ===== 外部访问隔离 =====
QDRANT_COLLECTION_INTERNAL=docs_internal
QDRANT_COLLECTION_PUBLIC=docs_public
EXTERNAL_AUDIENCE_DEFAULT=customer_facing
```

### 4.3 `backend/app/db/models/external_whitelist.py`（新建）

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExternalWhitelist(Base):
    __tablename__ = "external_whitelist"
    __table_args__ = (
        UniqueConstraint("doc_id", "audience", name="uq_doc_audience"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    audience: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True, default="customer_facing"
    )
    approved_by: Mapped[str] = mapped_column(String(64), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
```

### 4.4 `backend/migrations/versions/0002_external_whitelist.py`

`alembic revision --autogenerate -m "external_whitelist"` 生成后审核。

### 4.5 `backend/app/db/repos/external_whitelist.py`（新建 CRUD）

- `grant(session, *, doc_id, audience, approved_by, notes)` 幂等
- `revoke(session, *, doc_id, audience)` 软删（写 revoked_at）
- `list_active(session, *, audience, limit, offset)`
- `is_whitelisted(session, *, doc_id, audience) -> bool`

### 4.6 `backend/scripts/setup_qdrant_collections.py`（幂等创建脚本）

- 读 `settings.qdrant_collection_internal` / `qdrant_collection_public`
- 不存在则按统一 schema 创建（dim=1024 / cosine / payload schema 与既有一致）
- 已存在不动
- 日志输出每个 collection 状态

### 4.7 `backend/app/services/external_sync.py`（同步核心）

完整代码见 §5.1。

### 4.8 `backend/app/services/qdrant.py`（修改：加 user 二次校验入口）

完整代码见 §5.2。

### 4.9 `backend/app/api/router.py`（重构：拆 internal / public）

```python
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
internal_router = APIRouter(prefix="/api/v1/internal", tags=["internal"])
public_router = APIRouter(prefix="/api/v1/public", tags=["public"])

# 中性
from app.api import auth, feedback
api_router.include_router(auth.router)
api_router.include_router(feedback.router)

# 内部（员工）
from app.api import admin, whitelist_admin
internal_router.include_router(admin.router)
internal_router.include_router(whitelist_admin.router)

# 外部（公众号 / 客服）
from app.api import public_query
public_router.include_router(public_query.router)
```

`backend/app/main.py` mount 三个 router。

### 4.10 `backend/app/api/whitelist_admin.py`（新建）

POST / DELETE / GET endpoint，写操作触发 `external_sync.sync_doc(doc_id, action)` 异步任务。

### 4.11 `backend/app/api/public_query.py`（新建占位）

```python
"""公众号 / 外部客服查询入口。

- 强制只查 docs_public collection
- 调用 Agent 时强制 EXTERNAL_TOOLS（Phase 2+ 落地）
- 当前 Phase 1 仅占位 + 调通最小链路
"""
```

### 4.12 测试文件

- `backend/tests/db/test_external_whitelist.py`（integration CRUD + 唯一约束）
- `backend/tests/services/test_external_sync.py`（mock qdrant，校验 upsert / delete 调用）
- `backend/tests/services/test_qdrant_user_check.py`（外部 user 查 internal collection 抛 PermissionError）
- `backend/tests/api/test_router_isolation.py`（外部 user 触达 `/internal/*` 返回 403）
- `backend/tests/api/test_public_query.py`(端到端 public_query 只查 docs_public)
- `backend/tests/api/test_whitelist_admin.py`（grant / revoke / list）

### 4.13 `docs/CODEX_QUICK_REF.md`（新增「外部访问隔离」章节）

```markdown
## 🚧 外部访问隔离（4 层防御落地）

| 层 | 落地位置 |
|----|---------|
| 1 数据隔离 | 双 Qdrant collection：`docs_internal` / `docs_public`，白名单触发同步 |
| 2 服务校验 | `services/qdrant.py` 的 `search(collection, ..., user)` 入口断言 |
| 3 路由隔离 | `internal_router` / `public_router` 物理拆分 |
| 4 审计日志 | #70 落地（trace_id + audit_logs）|

加白名单：`POST /api/v1/internal/external-whitelist {doc_id, audience, notes}`
撤白名单：`DELETE /api/v1/internal/external-whitelist/{doc_id}?audience=customer_facing`
全量重建 public collection：`uv run python scripts/rebuild_public_collection.py`
```

---

## 5. 关键实现参考

### 5.1 `services/external_sync.py`

```python
"""external_whitelist → docs_public 同步。

设计原则：
- 白名单 grant → 从 docs_internal 拉 vector + payload → upsert 到 docs_public
- 白名单 revoke → 从 docs_public 删除对应 points
- 同步失败不影响主响应（异步 + log）
- 重复 grant 幂等（upsert 覆盖）
"""

from __future__ import annotations

from loguru import logger

from app.core.config import settings
from app.services.qdrant import get_qdrant_client


async def sync_grant(doc_id: str) -> None:
    """白名单加 → 把 doc 的 points 从 internal 复制到 public。"""
    client = get_qdrant_client()
    try:
        # 1. 从 docs_internal 拉所有属于 doc_id 的 points
        points, _ = await client.scroll(
            collection_name=settings.qdrant_collection_internal,
            scroll_filter={"must": [{"key": "doc_id", "match": {"value": doc_id}}]},
            with_vectors=True,
            with_payload=True,
            limit=10_000,
        )
        if not points:
            logger.warning("sync_grant: doc_id={} has no points in internal", doc_id)
            return

        # 2. upsert 到 docs_public（同 id 覆盖）
        await client.upsert(
            collection_name=settings.qdrant_collection_public,
            points=points,
        )
        logger.info("sync_grant: copied {} points for doc_id={}", len(points), doc_id)
    except Exception as exc:
        logger.warning("sync_grant failed for doc_id={}: {}", doc_id, exc)


async def sync_revoke(doc_id: str) -> None:
    """白名单撤销 → 从 docs_public 删除 doc 的所有 points。"""
    client = get_qdrant_client()
    try:
        await client.delete(
            collection_name=settings.qdrant_collection_public,
            points_selector={"filter": {"must": [{"key": "doc_id", "match": {"value": doc_id}}]}},
        )
        logger.info("sync_revoke: deleted points for doc_id={}", doc_id)
    except Exception as exc:
        logger.warning("sync_revoke failed for doc_id={}: {}", doc_id, exc)
```

### 5.2 `services/qdrant.py` 加 user 校验入口

```python
"""Qdrant 客户端封装 + 外部用户访问校验（铁律 #10 层 2）。"""

from app.core.config import settings
from app.core.exceptions import AppException
from app.services.auth import User


class PermissionError(AppException):
    error_code = "PERMISSION_DENIED"
    status_code = 403


async def search(
    *, collection: str, query_vector: list[float], user: User, **kwargs
) -> list[dict]:
    """统一 search 入口，强制做 user / collection 匹配校验。"""
    if collection == settings.qdrant_collection_internal and user.is_external:
        raise PermissionError(
            f"External user {user.user_id} cannot query internal collection"
        )
    client = get_qdrant_client()
    return await client.search(collection_name=collection, query_vector=query_vector, **kwargs)
```

### 5.3 路由分流 main app 装载

```python
# backend/app/main.py
from app.api.router import api_router, internal_router, public_router

app = FastAPI(...)
app.include_router(api_router)
app.include_router(internal_router)
app.include_router(public_router)
```

---

## 6. 验收标准

### 6.1 数据库
- [ ] `alembic upgrade head` 创建 `external_whitelist` 表 + 唯一约束 + 索引
- [ ] `alembic downgrade -1` 可回滚

### 6.2 双 Qdrant collection
- [ ] `scripts/setup_qdrant_collections.py` 可重复跑（幂等）
- [ ] `docs_internal` / `docs_public` schema 完全一致（同 dim / 同 distance）

### 6.3 同步逻辑
- [ ] grant doc_id → docs_public 新增 N 个 points（N = 该 doc 在 internal 的 points）
- [ ] revoke doc_id → docs_public 对应 points 全删
- [ ] 重复 grant 幂等（不出错，点位数不变）
- [ ] 同步失败不抛错给主流程

### 6.4 路由分流
- [ ] `/api/v1/internal/*` 走 internal_router
- [ ] `/api/v1/public/*` 走 public_router
- [ ] `/api/v1/auth/login` 仍在中性顶层
- [ ] admin / whitelist_admin 物理上不暴露在 `/public/*`

### 6.5 二次校验
- [ ] 外部 user 调 `services.qdrant.search(collection=internal, ...)` 抛 `PermissionError`
- [ ] 内部 user 调同样接口正常返回
- [ ] 公开 collection 任何 user 都能调

### 6.6 公众号 endpoint
- [ ] `POST /api/v1/public/query` 只查 `docs_public`

### 6.7 白名单管理 endpoint
- [ ] POST 加白名单 → 异步触发 sync_grant
- [ ] DELETE → 异步触发 sync_revoke
- [ ] GET 分页可用
- [ ] 重复 POST 同 doc_id 返回 200 + 幂等

### 6.8 静态检查
- [ ] ruff format / check / mypy 全绿
- [ ] coverage 不退化

### 6.9 铁律合规
- [ ] services/qdrant.py 是 Qdrant 唯一入口
- [ ] 业务代码无硬编码 collection 名
- [ ] 落地铁律 #10 层 1-3（层 4 待 #70）

### 6.10 Git / Handoff
- [ ] 分支 `feat/W2-D1-68-external-isolation`
- [ ] commit 含 `Refs: #68`
- [ ] PR title 含 `#68`
- [ ] Handoff §0-§8 完整

---

## 7. 禁止事项

- ❌ 用 Qdrant payload filter 取代物理 collection 分离（filter 是软约束）
- ❌ 业务代码绕过 `services/qdrant.py` 直连 client
- ❌ admin / whitelist_admin endpoint 挂到 `/public/*` 或顶层 router
- ❌ 同步逻辑用 await（必须 `asyncio.create_task` 异步）
- ❌ 在 docs_public 写入 visibility=internal 的 chunk
- ❌ 用黑名单逻辑（必须白名单）
- ❌ 让 public_query endpoint 接受 `collection` 参数（强制走 `docs_public`）
- ❌ 把外部 user 直连内部 collection 当 bug 修（这是设计：必须报警 + 拒绝）

---

## 8. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| grant 同步前 doc 未入库 | docs_public 空同步 | 同步逻辑兼容（log warning 不抛错）|
| revoke 后忘删 docs_public 残留 | 外部仍能搜到 | revoke 必须等 sync_revoke 完成，失败告警 |
| 双 collection schema 不同步 | 切换查询路径报错 | setup 脚本统一模板 |
| 白名单字段加 `is_active` 而非 revoked_at | 软删边界不清 | 用 nullable `revoked_at` |
| 路由分流后忘改前端 | 公众号请求 404 | §11 衔接段提醒前端 |
| `PermissionError` 与 Python 内建重名 | 引用混乱 | 用 `app.core.exceptions.PermissionError` |
| Agent 工具集还没分但已起 public_query | LLM 可能调到内部工具 | Phase 1 用 stub Agent + 注释 |
| docs_public 含 visibility=confidential 残留 | 外部能搜到机密 | sync_grant 前断言 visibility ∈ {public, customer_facing} |

---

## 9. 参考资料

- Qdrant collections API: https://qdrant.tech/documentation/concepts/collections/
- Qdrant scroll + filter: https://qdrant.tech/documentation/concepts/points/#scroll-points
- FastAPI router include 模式: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- 本项目：`CLAUDE.md` 铁律 #10 / 原则 P3 / `docs/tasks/W2-D1-67-idp-abstraction.md`

---

## 10. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 spec + 现有 qdrant.py / router.py | 30 分钟 |
| config.py + .env.example 加字段 | 20 分钟 |
| db/models/external_whitelist.py + migration | 45 分钟 |
| db/repos/external_whitelist.py | 45 分钟 |
| scripts/setup_qdrant_collections.py | 45 分钟 |
| services/external_sync.py | 60 分钟 |
| services/qdrant.py 加 user 校验入口 | 45 分钟 |
| api/router.py 重构 internal / public | 60 分钟 |
| api/whitelist_admin.py | 45 分钟 |
| api/public_query.py 占位 | 30 分钟 |
| 6 个测试文件 | 150 分钟 |
| QUICK_REF + architecture.md 更新 | 30 分钟 |
| 验证端到端 + 重建脚本 | 45 分钟 |
| Self-Review + Handoff | 75 分钟 |
| 提交 + PR + CI | 20 分钟 |
| **合计** | **~12 小时（2-2.5 工作日）** |

---

## 11. 与下一轮的衔接

#68 完成后：

1. **#42 ACL 中间件**：可直接消费 `internal_router` 树，加 `Depends(require_internal_user)` 即可
2. **#70 可观测性**：审计装饰器挂到 `whitelist_admin` 所有 write endpoint + `qdrant.search` 抛 PermissionError 处
3. **#69 CRM endpoint**：直接挂 `internal_router`，不会有外部可达风险
4. **公众号正式上线**：起独立任务把 `EXTERNAL_TOOLS` 列表落地（Phase 2+）
5. **400 份文档入库**：默认全进 `docs_internal`，业务方逐篇审核进白名单

Handoff §7 应说明：

1. 双 collection 必须保持 schema 同步，未来加 payload 字段两边一起改
2. 白名单是源头，docs_public 是缓存/副本，不要绕过白名单直写 docs_public
3. 同步是异步，可能有秒级延迟，前端如有「立即生效」需求需轮询
4. PermissionError 当前返回 403，未来 ACL 上线后边界更复杂
5. `EXTERNAL_TOOLS` 落地是 Phase 2+ 的事，本任务仅占位

---

## 12. 与 #67 / #37 / #39 / #70 的集成点

- **#67 User.is_external**：本任务 `services/qdrant.py` 二次校验直接读 `user.is_external`
- **#37 admin endpoint**：必须挂 `internal_router`，本任务的 router 重构会迁移现有 admin
- **#39 usage admin endpoint**：同 #37，归 internal 子树
- **#70 审计日志**：本任务的 `services/qdrant.PermissionError` 抛出点 + `whitelist_admin` 写操作必须挂 #70 的 audit 装饰器（grant_audit / revoke_audit / breach_alert）
- **migration 编号**：#67 = 0001 / 本任务 = 0002 / #37 = 0003 / #39 = 0004 / #70 = 0005

---

_v1.0 | 任务 ID：#68 | 最后更新：2026-06-05_
