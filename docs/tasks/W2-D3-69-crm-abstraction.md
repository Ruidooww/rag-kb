# Task #69: CRM 抽象层 — CRMService ABC + MockCRM + LangGraph 工具骨架

> **Phase**: 1 末 / Phase 2 起步（紧跟 #67 / #68 / #70）
> **预估工时**: 2-2.5 天
> **优先级**: 🟡 中（CRM 厂家拍板前接口冻结，避免业务代码绑死任何一家）
> **前置任务**: #67（User 上下文）；建议 #68 / #70 已合并（router 分流 + 审计装饰器）
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

CLAUDE.md 铁律 #9（CRM 调用走统一抽象层）的落地任务。当前业务方还在销售易 / 纷享销客 / HubSpot 之间评估，但 Phase 2 的「客户对比报告」「服务路径图」「合同到期提醒」都依赖 CRM 数据。

**做法**：在 CRM 厂家拍板前，把接口先冻结：

- `CRMService` ABC：定义所有 CRM 操作的统一接口（拿客户、拉合同、列联系人、查工单等）
- `MockCRM` 实现：基于本地 fixture / `data/mock_crm/` 目录，开发期 + 测试期 100% 不依赖外部
- 4 个 stub provider（`XiaoshouyiCRM` / `FxiaokeCRM` / `HubspotCRM` / `SalesforceCRM`）：仅类骨架 + `raise NotImplementedError`，留给厂家拍板后实现
- LangGraph 工具函数（`get_customer_basic` / `list_contracts` / `get_service_history` / ...）：必须经 `services/crm.py`，节点禁止直连 SDK
- **CRM 工具集物理隔离**（铁律 #10 落地）：所有 CRM 工具只能进 `INTERNAL_TOOLS`，绝不允许进 `EXTERNAL_TOOLS`

**为什么不等厂家拍板再做**：
- 接口冻结后，业务侧（#48-#52 对比报告 / 服务路径）就能基于稳定 ABC 写代码
- MockCRM 让自动化测试 / 演示 / 本地开发不被外部 API 卡住
- 厂家拍板后只改 `services/crm.py` 一个文件，业务零改动（同铁律 #1 思想）

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| #67 已合并 | `git log --oneline \| grep "#67"` | PR 在 main |
| User schema 含 is_external | `grep "is_external" backend/app/services/auth.py` | hit |
| LangGraph 已就位 | `ls backend/app/agents/` | 存在 |
| internal_router 已就位（建议 #68 合并）| `grep "internal_router" backend/app/api/router.py` | hit（未合并也可起，先挂 api_router 加 TODO）|
| 审计装饰器（建议 #70 合并）| `ls backend/app/core/audit.py` | hit（未合并也可起，先留装饰器位置）|
| main 干净 | `git status` | clean |

---

## 3. 任务目标

### 3.1 数据模型（最小集，避免绑死厂家 schema）
- `app/models/crm.py`：Pydantic Schemas
  - `Customer`（id / name / industry / size / region / 自定义 metadata）
  - `Contract`（id / customer_id / start_date / end_date / amount / currency / status / metadata）
  - `Contact`（id / customer_id / name / role / phone / email / metadata）
  - `ServiceHistory`（id / customer_id / type / created_at / summary / metadata）
- 字段命名走 snake_case，避开厂家专有 camelCase
- 敏感字段（phone / email / amount）由 `app.api.utils.sanitize` 在 API 层脱敏（落地原则 P1）

### 3.2 CRMService ABC
- `app/services/crm.py`
- 抽象方法：
  - `async get_customer(customer_id: str) -> Customer | None`
  - `async list_customers(*, region=None, industry=None, limit=100, offset=0) -> list[Customer]`
  - `async list_contracts(customer_id: str) -> list[Contract]`
  - `async list_contacts(customer_id: str) -> list[Contact]`
  - `async list_service_history(customer_id: str, *, since=None, limit=100) -> list[ServiceHistory]`
- 工厂 `get_crm()` 按 `settings.crm_provider` 切换

### 3.3 MockCRM 完整实现
- 数据来源：`data/mock_crm/`（YAML / JSON fixture）
- 启动时 lazy load 到内存（dict 索引）
- 支持 `MOCK_CRM_DATA_PATH` env 覆盖（测试用）
- 写操作（如果未来需要）：内存追加，不持久化

### 3.4 4 个 stub provider
- `XiaoshouyiCRM` / `FxiaokeCRM` / `HubspotCRM` / `SalesforceCRM`
- 仅类骨架 + 所有方法 `raise NotImplementedError("Implement after vendor selection")`
- 工厂 `get_crm()` 已注册分支（switch 全覆盖）

### 3.5 LangGraph 工具函数
- `app/agents/tools/crm_tools.py`
- 5 个工具（最小集）：
  - `get_customer_basic(customer_id)`
  - `list_contracts(customer_id)`
  - `list_contacts(customer_id)`
  - `get_service_history(customer_id, since)`
  - `find_customer_by_name(name_query)`
- 每个工具内部：
  1. `user = ctx.user`（LangGraph state 透传）
  2. `if user.is_external: raise PermissionError`（防御层 2，二次校验）
  3. 调 `crm = get_crm()` + 业务方法
  4. `@audit(event_type=CRM_QUERY, target=...)` 装饰（依赖 #70）
- 工具签名兼容 LangGraph `create_react_agent` 的 tool 协议

### 3.6 工具集注册（落地铁律 #10 + 原则 P2）
- `app/agents/tool_registry.py`
- 单文件集中定义：
  ```python
  EXTERNAL_TOOLS = [search_external_docs]  # 占位，等公众号 Agent 落地
  INTERNAL_TOOLS = [
      search_docs,
      get_customer_basic,
      list_contracts,
      list_contacts,
      get_service_history,
      find_customer_by_name,
  ]
  ```
- 关键断言测试（原则 P2）：
  - `test_no_crm_in_external_tools.py`：CRM 工具名集合 ∩ EXTERNAL_TOOLS 必须为空
  - `test_tool_registry_snapshot.py`：工具集变更必须主动改 snapshot，防止误改

### 3.7 build_agent 工厂
- `app/agents/factory.py`
- `def build_agent(user: User) -> CompiledGraph`
- 内部 `tools = EXTERNAL_TOOLS if user.is_external else INTERNAL_TOOLS`
- 返回 `create_react_agent(get_llm(), tools)`
- 业务方调 Agent 必须经此工厂

### 3.8 Settings 扩展
```python
crm_provider: Literal["mock", "xiaoshouyi", "fxiaoke", "hubspot", "salesforce"] = "mock"
mock_crm_data_path: str = "data/mock_crm"
```

### 3.9 测试覆盖
- MockCRM CRUD（get / list / find）
- 4 个 stub provider 调用全部抛 NotImplementedError
- get_crm 工厂分支
- 工具二次校验：外部 user 调 CRM 工具抛 PermissionError
- 工具集断言（CRM 不在 EXTERNAL_TOOLS）
- build_agent：外部 user 拿到的 Agent 工具列表不含任何 CRM 工具
- end-to-end：内部 user 调 `get_customer_basic` 成功 + audit_logs 多 1 条 event_type=crm_query

### 3.10 文档
- `docs/CODEX_QUICK_REF.md` 加「CRM」章节
- `docs/architecture.md` 更新（如已存在）：标出 CRM 抽象层位置
- 在文件头注释明确说明：当前 MockCRM 是默认实现，厂家拍板后改 `crm_provider`

---

## 4. 输出文件清单

### 4.1 `backend/app/core/config.py`（追加字段）

```python
crm_provider: Literal["mock", "xiaoshouyi", "fxiaoke", "hubspot", "salesforce"] = "mock"
mock_crm_data_path: str = "data/mock_crm"
```

### 4.2 `backend/.env.example`（追加段落）

```env
# ===== CRM 抽象层 =====
CRM_PROVIDER=mock                  # mock / xiaoshouyi / fxiaoke / hubspot / salesforce
MOCK_CRM_DATA_PATH=data/mock_crm
```

### 4.3 `backend/app/models/crm.py`（新建 Pydantic schemas）

完整代码见 §5.1。

### 4.4 `backend/app/services/crm.py`（CRMService ABC + 工厂 + 4 个 stub）

完整代码见 §5.2。

### 4.5 `backend/app/services/crm_mock.py`（MockCRM 实现）

完整代码见 §5.3。

### 4.6 `data/mock_crm/`（fixture 数据，gitignore 之外）

- `customers.yaml`（5-10 条样例客户）
- `contracts.yaml`（每客户 1-3 条合同）
- `contacts.yaml`（每客户 1-2 个联系人）
- `service_history.yaml`（每客户 3-5 条历史）

注：数据按虚构客户名编（如「示例科技」/「演示集团」），不含真实客户信息。

### 4.7 `backend/app/agents/tools/crm_tools.py`（LangGraph 工具）

完整代码见 §5.4。

### 4.8 `backend/app/agents/tool_registry.py`（工具集注册中心）

```python
"""统一工具集注册中心（落地 CLAUDE.md 铁律 #10 + 原则 P2）。

⚠️ 任何 CRM / 内部 search / 内部数据查询工具 **绝不** 允许进 EXTERNAL_TOOLS。
变更工具集必须更新 tests/agents/test_tool_registry.py 的 snapshot。
"""

from app.agents.tools.crm_tools import (
    find_customer_by_name,
    get_customer_basic,
    get_service_history,
    list_contacts,
    list_contracts,
)
from app.agents.tools.search_tools import search_docs, search_external_docs

EXTERNAL_TOOLS = [search_external_docs]

INTERNAL_TOOLS = [
    search_docs,
    get_customer_basic,
    list_contracts,
    list_contacts,
    get_service_history,
    find_customer_by_name,
]

# Sanity check：模块加载时自检
_EXTERNAL_NAMES = {t.name for t in EXTERNAL_TOOLS}
_INTERNAL_ONLY_PREFIXES = ("get_customer", "list_contract", "list_contact", "get_service", "find_customer", "search_docs")
for name in _EXTERNAL_NAMES:
    assert not any(name.startswith(p) for p in _INTERNAL_ONLY_PREFIXES), (
        f"Tool {name} looks internal but appears in EXTERNAL_TOOLS"
    )
```

### 4.9 `backend/app/agents/factory.py`（build_agent 工厂）

```python
"""Agent 构建工厂。所有调用方必须经此函数构建 Agent。"""

from langgraph.prebuilt import create_react_agent

from app.agents.tool_registry import EXTERNAL_TOOLS, INTERNAL_TOOLS
from app.services.auth import User
from app.services.llm import get_llm


def build_agent(user: User):
    """根据 user.is_external 选工具集。工具集是安全边界，不是 prompt。"""
    tools = EXTERNAL_TOOLS if user.is_external else INTERNAL_TOOLS
    return create_react_agent(get_llm(endpoint="agent"), tools)
```

### 4.10 测试文件

- `backend/tests/services/test_crm_mock.py`（MockCRM CRUD）
- `backend/tests/services/test_crm_stubs.py`（4 个 stub 抛 NotImplementedError）
- `backend/tests/services/test_crm_factory.py`（get_crm 分支）
- `backend/tests/agents/test_crm_tools.py`（二次校验 + audit 落库）
- `backend/tests/agents/test_tool_registry.py`（断言 CRM 不在 EXTERNAL_TOOLS + snapshot）
- `backend/tests/agents/test_factory.py`（外部 user → 工具列表不含 CRM）

### 4.11 `docs/CODEX_QUICK_REF.md`（新增「CRM 抽象层」章节）

```markdown
## 🤝 CRM 抽象层

| 操作 | 方法 |
|------|------|
| 获取当前 CRM | `crm = get_crm()` |
| 拿客户 | `customer = await crm.get_customer(customer_id)` |
| 列合同 | `await crm.list_contracts(customer_id)` |
| 列联系人 | `await crm.list_contacts(customer_id)` |
| 切换 provider | 改 `.env` 的 `CRM_PROVIDER`，业务代码零改动 |

**业务代码禁止直接 import 任何 CRM SDK**（铁律 #9）—— 走 `services/crm.py`。
**CRM 工具绝不允许进 EXTERNAL_TOOLS**（铁律 #10）—— 仅 INTERNAL_TOOLS。
4 个真实 provider（xiaoshouyi / fxiaoke / hubspot / salesforce）当前是 stub，厂家拍板后实现对应类。
```

---

## 5. 关键实现参考

### 5.1 `app/models/crm.py`

```python
"""CRM 数据模型（厂家无关 / snake_case / 最小集）。

设计原则：
- 字段名厂家无关；厂家专有字段塞 metadata（dict）
- 敏感字段（phone / email / amount）由 API 层 sanitize() 脱敏
- ID 一律字符串（不同厂家 ID 类型不一）
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CustomerSize(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class ContractStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    PENDING = "pending"


class Customer(BaseModel):
    id: str
    name: str
    industry: str | None = None
    size: CustomerSize | None = None
    region: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Contract(BaseModel):
    id: str
    customer_id: str
    start_date: date
    end_date: date | None = None
    amount: float
    currency: str = "CNY"
    status: ContractStatus
    metadata: dict[str, Any] = Field(default_factory=dict)


class Contact(BaseModel):
    id: str
    customer_id: str
    name: str
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServiceHistory(BaseModel):
    id: str
    customer_id: str
    type: str  # ticket / visit / call / ...
    created_at: datetime
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### 5.2 `app/services/crm.py`

```python
"""CRM 抽象层（铁律 #9 落地）。

业务代码只调 get_crm()，不直接 import 任何 CRM SDK。
切换厂家只改 .env 的 CRM_PROVIDER，业务零改动。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Final

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.crm import Contact, Contract, Customer, ServiceHistory

__all__ = [
    "CRMError",
    "CRMService",
    "FxiaokeCRM",
    "HubspotCRM",
    "SalesforceCRM",
    "XiaoshouyiCRM",
    "get_crm",
]


class CRMError(AppException):
    error_code = "CRM_ERROR"
    status_code = 502


class CRMService(ABC):
    """所有 CRM provider 必须实现的接口。"""

    @abstractmethod
    async def get_customer(self, customer_id: str) -> Customer | None: ...

    @abstractmethod
    async def list_customers(
        self,
        *,
        region: str | None = None,
        industry: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]: ...

    @abstractmethod
    async def list_contracts(self, customer_id: str) -> list[Contract]: ...

    @abstractmethod
    async def list_contacts(self, customer_id: str) -> list[Contact]: ...

    @abstractmethod
    async def list_service_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[ServiceHistory]: ...

    @abstractmethod
    async def find_customer_by_name(self, name_query: str) -> list[Customer]: ...


# === 4 个 stub provider ===
class XiaoshouyiCRM(CRMService):
    """销售易 CRM。需厂家拍板后实现。"""

    async def get_customer(self, customer_id):
        raise NotImplementedError("XiaoshouyiCRM: implement after vendor selection")

    async def list_customers(self, **kwargs):
        raise NotImplementedError("XiaoshouyiCRM: implement after vendor selection")

    async def list_contracts(self, customer_id):
        raise NotImplementedError("XiaoshouyiCRM: implement after vendor selection")

    async def list_contacts(self, customer_id):
        raise NotImplementedError("XiaoshouyiCRM: implement after vendor selection")

    async def list_service_history(self, customer_id, **kwargs):
        raise NotImplementedError("XiaoshouyiCRM: implement after vendor selection")

    async def find_customer_by_name(self, name_query):
        raise NotImplementedError("XiaoshouyiCRM: implement after vendor selection")


class FxiaokeCRM(CRMService):
    """纷享销客 CRM。需厂家拍板后实现。"""

    # 同 XiaoshouyiCRM 模式，所有方法 raise NotImplementedError("FxiaokeCRM: ...")
    ...


class HubspotCRM(CRMService):
    """HubSpot CRM。需厂家拍板后实现。"""

    ...


class SalesforceCRM(CRMService):
    """Salesforce CRM。需厂家拍板后实现。"""

    ...


# === 工厂 ===
def _build_mock() -> CRMService:
    from app.services.crm_mock import MockCRM

    return MockCRM()


_PROVIDERS: Final[dict[str, callable]] = {
    "mock": _build_mock,
    "xiaoshouyi": XiaoshouyiCRM,
    "fxiaoke": FxiaokeCRM,
    "hubspot": HubspotCRM,
    "salesforce": SalesforceCRM,
}


def get_crm() -> CRMService:
    builder = _PROVIDERS.get(settings.crm_provider)
    if builder is None:
        raise CRMError(f"Unknown CRM_PROVIDER: {settings.crm_provider}")
    return builder()
```

### 5.3 `app/services/crm_mock.py`（MockCRM）

```python
"""Mock CRM 实现。基于 data/mock_crm/ YAML fixture。

启动时 lazy load 到内存，无外部依赖。
开发期 / 测试期 / 演示期默认使用。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from app.core.config import settings
from app.models.crm import Contact, Contract, Customer, ServiceHistory
from app.services.crm import CRMService


class MockCRM(CRMService):
    def __init__(self) -> None:
        self._customers: dict[str, Customer] = {}
        self._contracts: dict[str, list[Contract]] = {}
        self._contacts: dict[str, list[Contact]] = {}
        self._history: dict[str, list[ServiceHistory]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        root = Path(settings.mock_crm_data_path)
        if not root.exists():
            logger.warning("MockCRM data path not found: {}", root)
            self._loaded = True
            return

        for cust in _load_yaml(root / "customers.yaml"):
            obj = Customer.model_validate(cust)
            self._customers[obj.id] = obj
        for c in _load_yaml(root / "contracts.yaml"):
            obj = Contract.model_validate(c)
            self._contracts.setdefault(obj.customer_id, []).append(obj)
        for c in _load_yaml(root / "contacts.yaml"):
            obj = Contact.model_validate(c)
            self._contacts.setdefault(obj.customer_id, []).append(obj)
        for h in _load_yaml(root / "service_history.yaml"):
            obj = ServiceHistory.model_validate(h)
            self._history.setdefault(obj.customer_id, []).append(obj)
        self._loaded = True
        logger.info(
            "MockCRM loaded: {} customers / {} contracts",
            len(self._customers),
            sum(len(v) for v in self._contracts.values()),
        )

    async def get_customer(self, customer_id: str) -> Customer | None:
        self._ensure_loaded()
        return self._customers.get(customer_id)

    async def list_customers(self, **kwargs: Any) -> list[Customer]:
        self._ensure_loaded()
        region = kwargs.get("region")
        industry = kwargs.get("industry")
        limit = kwargs.get("limit", 100)
        offset = kwargs.get("offset", 0)
        items = list(self._customers.values())
        if region:
            items = [c for c in items if c.region == region]
        if industry:
            items = [c for c in items if c.industry == industry]
        return items[offset : offset + limit]

    async def list_contracts(self, customer_id: str) -> list[Contract]:
        self._ensure_loaded()
        return self._contracts.get(customer_id, [])

    async def list_contacts(self, customer_id: str) -> list[Contact]:
        self._ensure_loaded()
        return self._contacts.get(customer_id, [])

    async def list_service_history(
        self, customer_id: str, *, since: datetime | None = None, limit: int = 100
    ) -> list[ServiceHistory]:
        self._ensure_loaded()
        items = self._history.get(customer_id, [])
        if since:
            items = [h for h in items if h.created_at >= since]
        return items[:limit]

    async def find_customer_by_name(self, name_query: str) -> list[Customer]:
        self._ensure_loaded()
        q = name_query.strip().lower()
        return [c for c in self._customers.values() if q in c.name.lower()]


def _load_yaml(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or []
```

### 5.4 `app/agents/tools/crm_tools.py`（LangGraph 工具）

```python
"""LangGraph CRM 工具。所有工具内部：
1. 防御层 2：外部 user 直接拒绝（即使路由层 + 工具集隔离被绕）
2. 走 services/crm.py（铁律 #9），不直连 SDK
3. 挂 @audit 装饰器（事后追责，铁律 #10 层 4）
"""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool
from loguru import logger

from app.core.audit import AuditEventType, audit
from app.core.exceptions import AppException
from app.services.auth import User
from app.services.crm import get_crm


class PermissionError(AppException):
    error_code = "PERMISSION_DENIED"
    status_code = 403


def _check_internal(user: User, tool_name: str) -> None:
    if user.is_external:
        logger.warning(
            "External user {} attempted to call internal CRM tool {}",
            user.user_id,
            tool_name,
        )
        raise PermissionError(f"External user cannot call {tool_name}")


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda customer_id, user, **_: f"customer:{customer_id}",
)
async def get_customer_basic(customer_id: str, user: User) -> dict:
    """获取客户基本信息（名称 / 行业 / 规模 / 区域）。"""
    _check_internal(user, "get_customer_basic")
    crm = get_crm()
    customer = await crm.get_customer(customer_id)
    return customer.model_dump() if customer else {}


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda customer_id, user, **_: f"customer:{customer_id}:contracts",
)
async def list_contracts(customer_id: str, user: User) -> list[dict]:
    """列出客户所有合同。"""
    _check_internal(user, "list_contracts")
    crm = get_crm()
    items = await crm.list_contracts(customer_id)
    return [c.model_dump() for c in items]


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda customer_id, user, **_: f"customer:{customer_id}:contacts",
)
async def list_contacts(customer_id: str, user: User) -> list[dict]:
    """列出客户所有联系人。"""
    _check_internal(user, "list_contacts")
    crm = get_crm()
    items = await crm.list_contacts(customer_id)
    return [c.model_dump() for c in items]


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda customer_id, since, user, **_: f"customer:{customer_id}:history",
)
async def get_service_history(
    customer_id: str,
    since: datetime | None,
    user: User,
) -> list[dict]:
    """拉客户服务历史（工单 / 拜访 / 通话）。"""
    _check_internal(user, "get_service_history")
    crm = get_crm()
    items = await crm.list_service_history(customer_id, since=since)
    return [h.model_dump() for h in items]


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda name_query, user, **_: f"search:{name_query[:64]}",
)
async def find_customer_by_name(name_query: str, user: User) -> list[dict]:
    """按客户名模糊搜索。"""
    _check_internal(user, "find_customer_by_name")
    crm = get_crm()
    items = await crm.find_customer_by_name(name_query)
    return [c.model_dump() for c in items]
```

---

## 6. 验收标准

### 6.1 CRMService ABC
- [ ] `get_crm()` 默认返回 `MockCRM`
- [ ] 修改 `CRM_PROVIDER=xiaoshouyi` → 返回 `XiaoshouyiCRM`（init OK，调方法才抛 NotImplementedError）
- [ ] 未知 provider → 抛 `CRMError`

### 6.2 MockCRM
- [ ] `data/mock_crm/customers.yaml` 至少 5 条
- [ ] `get_customer("不存在的 ID")` 返回 None（不抛错）
- [ ] `list_customers(region="华东")` 正确过滤
- [ ] `find_customer_by_name` 大小写不敏感
- [ ] fixture 缺失时 log warning 但不抛错（loaded=True）

### 6.3 4 个 stub provider
- [ ] 6 个方法各跑一次都抛 `NotImplementedError`
- [ ] init 不抛错（接口可以实例化）

### 6.4 工具二次校验（防御层 2）
- [ ] 内部 user 调任一 CRM 工具 → 正常返回
- [ ] 外部 user 调任一 CRM 工具 → 抛 `PermissionError`（403）
- [ ] log 中可见 "External user X attempted ..."

### 6.5 工具集断言（原则 P2）
- [ ] `EXTERNAL_TOOLS` 不含任何 CRM 工具名
- [ ] `EXTERNAL_TOOLS` 不含 `search_docs`（内部 search）
- [ ] tool_registry.py 的 sanity check assert 在 import 时通过
- [ ] snapshot test：工具列表变更必须主动改 snapshot

### 6.6 build_agent 工厂
- [ ] 内部 user → tools 含 CRM + search_docs
- [ ] 外部 user → tools 只含 `search_external_docs`
- [ ] 同一 user 多次调返回新 Agent 实例（无缓存，反模式 E1）

### 6.7 审计落库
- [ ] 内部 user 调 `get_customer_basic` 成功 → audit_logs 多 1 条 event_type=crm_query
- [ ] target_resource 含 customer_id
- [ ] 外部 user 被拒绝时也落 1 条 audit（severity=warning 或 critical）

### 6.8 静态检查
- [ ] ruff / mypy 全绿
- [ ] coverage 不退化

### 6.9 铁律合规
- [ ] grep `import xiaoshouyi|fxiaoke|hubspot|salesforce` 业务代码无残留（仅 services/crm.py 内类骨架，stub 不真 import SDK）
- [ ] 业务代码 import CRM 必走 `from app.services.crm import get_crm`
- [ ] 配置走 settings

### 6.10 Git / Handoff
- [ ] 分支 `feat/W2-D3-69-crm-abstraction`
- [ ] commit 含 `Refs: #69`
- [ ] Handoff §0-§8 完整

---

## 7. 禁止事项

- ❌ 业务代码直接 `import xiaoshouyi` / `from hubspot import ...`（违反铁律 #9）
- ❌ 在 LangGraph 节点里直连 CRM SDK（必须走 `services/crm.py`）
- ❌ 把任何 CRM 工具加入 `EXTERNAL_TOOLS`（违反铁律 #10）
- ❌ 用 prompt 限制权限取代工具集隔离（"告诉 LLM 不要调"不是安全边界）
- ❌ 给 `get_crm()` 加 `@lru_cache`（反模式 E1，切 .env 不生效）
- ❌ MockCRM 用真实客户数据当 fixture（必须虚构）
- ❌ CRM 工具直接返回 Customer 含 phone / email 给外部（必须经 sanitize，原则 P1）
- ❌ 删掉 4 个 stub provider 只留 mock（接口冻结的意义在于"厂家拍板时心里有数"）
- ❌ Mock CRM 落库 / 写文件（保持纯内存，避免测试间污染）
- ❌ 把厂家专有字段（如 SalesforceId）混到 `Customer.id`（厂家专有塞 metadata）

---

## 8. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| YAML fixture schema 不严 | model_validate 报错 | spec 给完整字段示例 |
| `find_customer_by_name` 全表扫 | 万级数据慢 | mock 阶段无所谓；真实 provider 用厂家搜索 API |
| 工具二次校验漏一个工具 | 外部 user 绕过 | sanity check 测试枚举所有 CRM 工具 |
| stub provider 类骨架忘加 `raise` | 静默返回 None | 测试覆盖每个 stub 每个方法 |
| CRM 厂家字段命名不一 | 业务层切换报错 | 中间层模型 + metadata 字段缓冲 |
| `@tool` + `@audit` 装饰器顺序 | 装饰器嵌套语义混 | `@tool` 在外，`@audit` 在内；测试覆盖 |
| MockCRM lazy load 并发 | 加载竞态 | 简单 if 检查 + 单调 set（Python 解释器锁兜底）|
| 厂家 API 限流 | 超额报错 | spec 注释明确："真实 provider 实现必须加 retry + 速率限制"|

---

## 9. 参考资料

- LangChain `@tool` 装饰器: https://python.langchain.com/docs/concepts/tools/
- LangGraph create_react_agent: https://langchain-ai.github.io/langgraph/reference/prebuilt/
- Pydantic v2 model_validate: https://docs.pydantic.dev/latest/api/base_model/#pydantic.BaseModel.model_validate
- 销售易 API: https://open.xiaoshouyi.com/
- 纷享销客 API: https://open.fxiaoke.com/
- HubSpot API: https://developers.hubspot.com/docs/api/overview
- Salesforce REST API: https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/
- 本项目：`CLAUDE.md` 铁律 #9 #10 / 原则 P1 P2 / `docs/tasks/W2-D1-67-idp-abstraction.md` / `W2-D2-70-observability.md`

---

## 10. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 spec + 现有 services/llm.py 抽象模式 | 30 分钟 |
| config.py + .env.example | 20 分钟 |
| models/crm.py（4 个 Pydantic schema）| 45 分钟 |
| services/crm.py ABC + 4 stub provider + 工厂 | 60 分钟 |
| services/crm_mock.py + YAML loader | 75 分钟 |
| data/mock_crm/ 4 份 fixture（虚构客户）| 60 分钟 |
| agents/tools/crm_tools.py 5 个工具 + 装饰器 | 90 分钟 |
| agents/tool_registry.py + sanity check | 30 分钟 |
| agents/factory.py build_agent | 30 分钟 |
| 6 个测试文件 | 150 分钟 |
| QUICK_REF 更新 | 15 分钟 |
| Self-Review + Handoff | 75 分钟 |
| 提交 + PR + CI | 20 分钟 |
| **合计** | **~12 小时（2-2.5 工作日）** |

---

## 11. 与下一轮的衔接

#69 完成后：

1. **#48-#52 客户对比报告 / 服务路径**：可直接消费 CRM ABC 接口写 LangGraph 节点
2. **CRM 厂家拍板**：实现对应 stub provider，业务零改动
3. **公众号 Agent 上线**（Phase 2+）：直接复用 `build_agent(user)`，外部 user 自动只拿到 `search_external_docs`
4. **#42 ACL 中间件**：CRM 工具已经有防御层 2 校验，#42 加防御层 1 路由层兜底
5. **数据治理**：Mock 数据后续可换成 fixture 子集，便于 demo / 训练评估集

Handoff §7 应说明：

1. CRM 厂家拍板后实现路径：填 stub provider 类即可，业务零改动
2. MockCRM fixture 在 `data/mock_crm/`，加客户改 YAML
3. 4 个 stub 必须保留，删任何一个会破坏接口冻结的初衷
4. 工具集变更必须改 snapshot test，防止误把内部工具加入 EXTERNAL_TOOLS
5. CRM 工具二次校验是冗余防御，不要因为 router 层已校验就删掉

---

## 12. 与 #67 / #68 / #70 / #37 / #39 的集成点

- **#67 User.is_external**：CRM 工具二次校验 + build_agent 工厂都消费此字段
- **#68 internal_router**：未来 CRM endpoint（如 `/internal/customers`）挂 internal_router
- **#68 services/qdrant.PermissionError**：本任务的 `tools.crm_tools.PermissionError` 复用同模式
- **#70 @audit 装饰器**：CRM 工具强依赖；若 #70 未合并，本任务实现一个临时 no-op 装饰器，#70 合并后切换
- **#70 audit_logs.event_type**：`CRM_QUERY` / `CRM_WRITE` 已在 #70 spec 枚举中
- **#37 admin endpoint 模式**：未来 `/internal/crm/health` 等管理 endpoint 走相同 router 树
- **#39 用量记录**：CRM 调用不计入 LLM 用量，但本任务可未来扩展 CRM 调用计数

---

_v1.0 | 任务 ID：#69 | 最后更新：2026-06-05_
