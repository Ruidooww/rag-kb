# Task #67: IdP 抽象层 + dept_mapping + LocalIdP

> **Phase**: 1 末（Week 4 前）| **位置**: Phase 2 #42 ACL 的前置基建
> **预估工时**: 2-3 天（含 alembic 初始化）
> **优先级**: 🔴 高（Phase 2 ACL 强依赖）
> **前置任务**: Q1 (document_meta schema 已锚定，PR #13)
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

多部门 ACL + 对外客服隔离架构要求身份层支持多 IdP（飞书 / 企微 / 微信开放 / 公众号 / 本地账号），且**业务代码不绑死任何一家**——这是"铁律 #1"思想（统一抽象层）在身份层的延伸。

本任务**只做抽象层 + 一个可跑的实现（LocalIdP）+ 部门映射基建**，4 个真实 OAuth provider（飞书/企微/微信开放/公众号）仅提供接口骨架（`raise NotImplementedError`），留给 #42 阶段按需启用。

**这样做的好处**：
- 现在不引入 4 套 SDK 依赖
- 接口冻结，#42 ACL 中间件可以基于 4 provider 设计写
- LocalIdP 让开发期/测试期不依赖真账号
- alembic 一次性初始化，#24 直接受益

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| Q1 schema 已合并 | `git log --oneline \| grep "anchor document"` | PR #13 在 main |
| main 干净 | `git status` | clean |
| Docker 服务 healthy | `docker compose ps` | postgres 跑着 |
| 当前没有 alembic | `ls backend/alembic.ini` | not exist（本任务首次初始化）|

---

## 3. 任务目标

### 3.1 alembic 初始化（一次性基建）
- 装依赖：`alembic`、`sqlalchemy[asyncio]`、`asyncpg`、`psycopg2-binary`（仅 alembic 用）
- 在 `backend/` 下 `alembic init -t async migrations`
- 配置 `alembic.ini` 走 `settings.postgres_url`
- 创建首个 migration: `0001_dept_mapping.py`

### 3.2 dept_mapping 表
- SQLAlchemy ORM: `backend/app/db/models/dept_mapping.py`
- 字段：`id` / `external_provider` / `external_dept_id` / `internal_code` / `display_name` / `created_at` / `updated_at`
- 唯一约束：`(external_provider, external_dept_id)`
- CRUD repository: `backend/app/db/repos/dept_mapping.py`

### 3.3 IdP 抽象层
- `backend/app/services/auth.py`
- `IdentityProvider` ABC（`exchange_code` / `get_user_info`）
- `User` Pydantic schema（含 `internal_dept_code` / `role` / `max_visibility` / `allowed_depts`）
- `get_idp()` 工厂（按 `settings.idp_provider` 切换）

### 3.4 LocalIdP 完整实现
- 用户来源：env 配 `LOCAL_USERS` JSON 字符串
- 密码：bcrypt hash
- 部门：env 里直接指定 `internal_code`（跳过 dept_mapping，因为本地账号没有外部 dept_id）

### 3.5 4 个 stub providers
- `FeishuIdP` / `WeComIdP` / `WeChatOpenIdP` / `WeChatMpIdP`
- 仅类骨架 + `raise NotImplementedError("Implement in #42 prep task")`
- 在 `get_idp()` 工厂中已注册分支（switch case 全覆盖）

### 3.6 MockIdP for tests
- `backend/app/services/auth_mock.py`
- 测试 fixture 直接返回任意 User 对象

### 3.7 Settings 扩展
- `idp_provider: Literal["local", "feishu", "wecom", "wechat_open", "wechat_mp"] = "local"`
- `local_users: str = "[]"`  # JSON 字符串
- `postgres_url: str`（如未存在）

### 3.8 测试覆盖
- LocalIdP 登录成功/失败
- dept_mapping CRUD
- get_idp 工厂分支
- 4 stub provider 调用抛 NotImplementedError
- User schema 默认值

---

## 4. 输出文件清单

### 4.1 `backend/pyproject.toml`（追加依赖）

```bash
uv add alembic sqlalchemy "sqlalchemy[asyncio]" asyncpg bcrypt
uv add --dev psycopg2-binary  # alembic 同步连接用
```

### 4.2 `backend/.env.example`（追加段落）

```env
# ===== 身份认证（IdP）=====
IDP_PROVIDER=local                # local / feishu / wecom / wechat_open / wechat_mp
LOCAL_USERS=[]                    # JSON: [{"username":"alice","password_hash":"$2b$..","dept":"tech","role":"employee"}]

# ===== PostgreSQL =====
POSTGRES_URL=postgresql+asyncpg://rag:rag@localhost:5432/rag_kb
POSTGRES_URL_SYNC=postgresql+psycopg2://rag:rag@localhost:5432/rag_kb  # alembic 用
```

### 4.3 `backend/app/core/config.py`（追加字段）

```python
from typing import Literal

# 已有 Settings 类内追加：
idp_provider: Literal["local", "feishu", "wecom", "wechat_open", "wechat_mp"] = "local"
local_users: str = "[]"
postgres_url: SecretStr
postgres_url_sync: SecretStr
```

### 4.4 `backend/alembic.ini` + `backend/migrations/`（alembic init）

执行 `cd backend && alembic init -t async migrations` 后调整：

- `alembic.ini` 中 `sqlalchemy.url` 留空，改在 `env.py` 中从 `settings.postgres_url_sync` 读取
- `migrations/env.py` 接入 `from app.db.models import Base`

### 4.5 `backend/app/db/base.py`（新建）

```python
"""SQLAlchemy declarative base + async session factory."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.postgres_url.get_secret_value(), echo=False)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)
```

### 4.6 `backend/app/db/models/dept_mapping.py`（新建）

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeptMapping(Base):
    __tablename__ = "dept_mapping"
    __table_args__ = (
        UniqueConstraint("external_provider", "external_dept_id", name="uq_provider_dept"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_provider: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    external_dept_id: Mapped[str] = mapped_column(String(128), nullable=False)
    internal_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

### 4.7 `backend/migrations/versions/0001_dept_mapping.py`（首个 migration）

`alembic revision --autogenerate -m "create dept_mapping table"` 生成后审核确认。

### 4.8 `backend/app/db/repos/dept_mapping.py`（新建 CRUD）

```python
"""dept_mapping CRUD repository."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.dept_mapping import DeptMapping


async def get_internal_code(
    session: AsyncSession, *, provider: str, external_dept_id: str
) -> str | None:
    stmt = select(DeptMapping.internal_code).where(
        DeptMapping.external_provider == provider,
        DeptMapping.external_dept_id == external_dept_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    *,
    provider: str,
    external_dept_id: str,
    internal_code: str,
    display_name: str,
) -> DeptMapping:
    existing = await session.execute(
        select(DeptMapping).where(
            DeptMapping.external_provider == provider,
            DeptMapping.external_dept_id == external_dept_id,
        )
    )
    obj = existing.scalar_one_or_none()
    if obj is None:
        obj = DeptMapping(
            external_provider=provider,
            external_dept_id=external_dept_id,
            internal_code=internal_code,
            display_name=display_name,
        )
        session.add(obj)
    else:
        obj.internal_code = internal_code
        obj.display_name = display_name
    await session.flush()
    return obj
```

### 4.9 `backend/app/services/auth.py`（IdP 抽象 + User schema + 工厂）

见 §5 完整实现。

### 4.10 `backend/app/services/auth_mock.py`（测试 mock）

```python
"""Mock IdP for unit tests."""

from __future__ import annotations

from app.services.auth import IdentityProvider, Token, User


class MockIdP(IdentityProvider):
    """Always returns a pre-configured user. Used in tests."""

    def __init__(self, user: User) -> None:
        self._user = user

    async def exchange_code(self, code: str) -> Token:
        return Token(access_token=f"mock-token-{code}", expires_in=3600)

    async def get_user_info(self, token: Token) -> User:
        return self._user
```

### 4.11 `backend/tests/db/test_dept_mapping.py`（新建）

Integration tests，要 PG 跑着，标 `@pytest.mark.integration`：

- `test_upsert_creates_new`
- `test_upsert_updates_existing`
- `test_get_internal_code_returns_none_for_missing`
- `test_unique_constraint_blocks_duplicate`

### 4.12 `backend/tests/services/test_auth.py`（新建）

Unit tests（不依赖外部服务）：

- `test_local_idp_login_success`
- `test_local_idp_login_wrong_password`
- `test_local_idp_unknown_user`
- `test_get_idp_returns_local_by_default`
- `test_stub_providers_raise_not_implemented`（4 个 stub 各跑一次）
- `test_user_schema_max_visibility_derived_from_role`

### 4.13 `backend/app/api/auth.py`（最小登录 endpoint）

```python
"""Auth endpoints. Phase 1 仅做本地登录占位，#42 时扩 OAuth 回调。"""

from fastapi import APIRouter, HTTPException, status

from app.models.auth import LoginRequest, LoginResponse
from app.services.auth import get_idp

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    idp = get_idp()
    try:
        token = await idp.exchange_code(payload.code)
        user = await idp.get_user_info(token)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    return LoginResponse(token=token.access_token, user=user)
```

注：`app/api/router.py` 已有 `include_router` 模式，本任务追加 `auth.router`。

### 4.14 `backend/app/models/auth.py`（请求/响应 schema）

```python
from pydantic import BaseModel

from app.services.auth import User


class LoginRequest(BaseModel):
    code: str  # LocalIdP: "username:password"；OAuth: 授权码


class LoginResponse(BaseModel):
    token: str
    user: User
```

### 4.15 `docs/CODEX_QUICK_REF.md`（新增"身份认证"章节）

在"💾 对象存储"后追加：

```markdown
## 🪪 身份认证（IdP 抽象层）

| 操作 | 方法 |
|------|------|
| 获取当前 IdP | `idp = get_idp()` |
| 换 token | `token = await idp.exchange_code(code)` |
| 拿用户 | `user = await idp.get_user_info(token)` |
| 部门映射查询 | `await dept_mapping_repo.get_internal_code(session, provider=..., external_dept_id=...)` |
| 切换 provider | 改 `.env` 的 `IDP_PROVIDER`，业务代码零改动 |

**业务代码禁止直接 import 任何 IdP SDK** —— 走 services/auth.py 抽象。
四个真实 OAuth provider（feishu/wecom/wechat_open/wechat_mp）当前是 stub，需要时按 #42 子任务实现。
```

---

## 5. `services/auth.py` 完整实现参考

```python
"""Identity Provider abstraction layer.

Pattern: 铁律 #1 的身份层版本。业务代码只调 get_idp()，
不直接 import 飞书/企微/微信 SDK。切换 provider 只改 .env。

Phase 1 仅实现 LocalIdP；FeishuIdP / WeComIdP / WeChatOpenIdP / WeChatMpIdP
保留接口骨架，在 #42 ACL 任务前按需实现。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Final

import bcrypt
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.document_meta import Visibility

__all__ = [
    "AuthError",
    "FeishuIdP",
    "IdentityProvider",
    "LocalIdP",
    "Token",
    "User",
    "WeChatMpIdP",
    "WeChatOpenIdP",
    "WeComIdP",
    "get_idp",
]


# === Role → max_visibility 映射 ===
_ROLE_MAX_VISIBILITY: Final[dict[str, Visibility]] = {
    "employee": Visibility.INTERNAL,
    "manager": Visibility.CONFIDENTIAL,
    "admin": Visibility.CONFIDENTIAL,
}


class AuthError(AppException):
    error_code = "AUTH_ERROR"
    status_code = 401


class Token(BaseModel):
    access_token: str
    expires_in: int = 3600


class User(BaseModel):
    """登录后的用户上下文。供 ACL 中间件使用。"""

    user_id: str  # 内部唯一 ID（external_provider:external_user_id）
    external_provider: str  # local / feishu / wecom / ...
    external_user_id: str
    display_name: str
    email: str | None = None
    internal_dept_code: str | None = None  # tech / sales / ...
    role: str = "employee"  # employee / manager / admin
    max_visibility: Visibility = Visibility.INTERNAL
    allowed_depts: list[str] = Field(default_factory=list)


# === ABC ===
class IdentityProvider(ABC):
    """所有 IdP 必须实现的接口。"""

    @abstractmethod
    async def exchange_code(self, code: str) -> Token:
        """把授权码 / 登录凭据换 token。"""

    @abstractmethod
    async def get_user_info(self, token: Token) -> User:
        """根据 token 拿用户信息（含部门映射后的 internal_dept_code）。"""


# === LocalIdP（开发期实现，必做）===
class LocalIdP(IdentityProvider):
    """密码登录。开发期 / 测试期 / IdP 故障兜底用。

    用户来源：settings.local_users (JSON 字符串)
    格式：[{"username": "alice", "password_hash": "$2b$...", "dept": "tech", "role": "employee"}]
    """

    def __init__(self) -> None:
        raw = settings.local_users
        try:
            self._users = {u["username"]: u for u in json.loads(raw)}
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise AuthError(f"Invalid LOCAL_USERS config: {exc}") from exc

    async def exchange_code(self, code: str) -> Token:
        """code 格式：'username:password'。"""
        try:
            username, password = code.split(":", 1)
        except ValueError as exc:
            raise AuthError("Code must be 'username:password' for LocalIdP") from exc

        user = self._users.get(username)
        if user is None:
            raise AuthError(f"Unknown user: {username}")

        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            raise AuthError("Wrong password")

        # token 简单返回 username（生产应该签 JWT；Phase 1 不做）
        return Token(access_token=username, expires_in=86400)

    async def get_user_info(self, token: Token) -> User:
        username = token.access_token
        u = self._users.get(username)
        if u is None:
            raise AuthError(f"Token references unknown user: {username}")

        role = u.get("role", "employee")
        dept = u.get("dept")
        return User(
            user_id=f"local:{username}",
            external_provider="local",
            external_user_id=username,
            display_name=u.get("display_name", username),
            email=u.get("email"),
            internal_dept_code=dept,
            role=role,
            max_visibility=_ROLE_MAX_VISIBILITY.get(role, Visibility.INTERNAL),
            allowed_depts=[dept] if dept else [],
        )


# === 四个 stub providers（接口冻结，实现留给 #42）===
class FeishuIdP(IdentityProvider):
    """飞书 OAuth。需在 #42 启用前实现。"""

    async def exchange_code(self, code: str) -> Token:
        raise NotImplementedError("FeishuIdP: implement in #42 prep task")

    async def get_user_info(self, token: Token) -> User:
        raise NotImplementedError("FeishuIdP: implement in #42 prep task")


class WeComIdP(IdentityProvider):
    """企业微信 OAuth。需在 #42 启用前实现。"""

    async def exchange_code(self, code: str) -> Token:
        raise NotImplementedError("WeComIdP: implement in #42 prep task")

    async def get_user_info(self, token: Token) -> User:
        raise NotImplementedError("WeComIdP: implement in #42 prep task")


class WeChatOpenIdP(IdentityProvider):
    """微信开放平台扫码登录（个人微信）。需手工绑定 openid ↔ user_id。"""

    async def exchange_code(self, code: str) -> Token:
        raise NotImplementedError("WeChatOpenIdP: implement when external login needed")

    async def get_user_info(self, token: Token) -> User:
        raise NotImplementedError("WeChatOpenIdP: implement when external login needed")


class WeChatMpIdP(IdentityProvider):
    """微信公众号匿名访问（强制 audience=customer_facing）。"""

    async def exchange_code(self, code: str) -> Token:
        raise NotImplementedError("WeChatMpIdP: implement for external customer service")

    async def get_user_info(self, token: Token) -> User:
        raise NotImplementedError("WeChatMpIdP: implement for external customer service")


# === 工厂 ===
_PROVIDERS: Final[dict[str, type[IdentityProvider]]] = {
    "local": LocalIdP,
    "feishu": FeishuIdP,
    "wecom": WeComIdP,
    "wechat_open": WeChatOpenIdP,
    "wechat_mp": WeChatMpIdP,
}


def get_idp() -> IdentityProvider:
    """根据 settings.idp_provider 返回实现。"""
    provider_cls = _PROVIDERS.get(settings.idp_provider)
    if provider_cls is None:
        raise AuthError(f"Unknown IDP_PROVIDER: {settings.idp_provider}")
    return provider_cls()
```

---

## 6. 验收标准

### 6.1 alembic 初始化
- [ ] `backend/alembic.ini` 存在，`sqlalchemy.url` 从 settings 读
- [ ] `backend/migrations/env.py` import 了 `app.db.base.Base`
- [ ] `alembic upgrade head` 在干净 PG 上跑通
- [ ] `alembic downgrade -1` 可回滚

### 6.2 dept_mapping 表
- [ ] PG 里能看到 `dept_mapping` 表，含 6 个字段 + 唯一约束
- [ ] `test_dept_mapping.py` integration tests 全绿
- [ ] `upsert` 同 `(provider, external_dept_id)` 第二次调用更新而非插入

### 6.3 IdP 抽象层
- [ ] `get_idp()` 默认返回 `LocalIdP`
- [ ] 修改 `IDP_PROVIDER=feishu` 后 `get_idp()` 返回 `FeishuIdP` 实例
- [ ] 4 个 stub provider 的 `exchange_code` / `get_user_info` 都抛 `NotImplementedError`

### 6.4 LocalIdP
- [ ] `LOCAL_USERS` 配 1 个用户，`exchange_code("alice:correct_pwd")` 返回 Token
- [ ] 密码错抛 `AuthError`
- [ ] 用户名不存在抛 `AuthError`
- [ ] `get_user_info` 返回的 User 含 `internal_dept_code` 和 `max_visibility`

### 6.5 User schema
- [ ] `role=employee` → `max_visibility=internal`
- [ ] `role=manager` → `max_visibility=confidential`
- [ ] `allowed_depts` 默认 `[]`，LocalIdP 自动填 `[dept]`

### 6.6 API endpoint
- [ ] `POST /api/v1/auth/login` 接受 `{"code":"alice:pwd"}` 返回 token + user
- [ ] 密码错返回 401

### 6.7 静态检查
- [ ] ruff format / check 全绿
- [ ] mypy --strict 全绿（含新模块）
- [ ] coverage 不退化

### 6.8 铁律合规
- [ ] grep `import dashscope` / `from openai` / 飞书/企微 SDK：业务代码无残留（auth.py 也不引入 SDK，只留 stub）
- [ ] 配置走 settings，无硬编码

### 6.9 Git / Handoff
- [ ] 分支 `feat/W2-D1-67-idp-abstraction`
- [ ] commit 含 `Refs: #67`
- [ ] PR title 含 `#67`
- [ ] Handoff §0-§8 完整，含 `last_verified_commit`

---

## 7. 禁止事项

- ❌ 业务代码 import 任何 IdP SDK（飞书/企微/微信）——4 个真实 provider 留 stub
- ❌ 在 services/auth.py 内做 ACL 决策（"能不能访问 X"）——那是 #42 的活，本任务只负责"你是谁"
- ❌ commit 真实的 `LOCAL_USERS` 到 `.env.example`（只放占位）
- ❌ commit 任何 bcrypt 真实 hash 到 git
- ❌ 把 token 设计成永久有效（即使 LocalIdP 也设 24h）
- ❌ 在 ABC 里加 sync 方法（必须 async）
- ❌ 跳过 alembic 直接用 `Base.metadata.create_all()`——必须走 migration
- ❌ 把 4 个 stub provider 删掉只留 LocalIdP——接口冻结的目的是让 #42 写 ACL 时心里有数

---

## 8. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| asyncpg URL 写错 driver | engine 创建失败 | `postgresql+asyncpg://...` |
| alembic 用 async URL 跑同步操作 | migration 报错 | 单独配 `postgres_url_sync` 走 psycopg2 |
| LOCAL_USERS JSON 转义 | settings 解析失败 | 用单引号包裹整段 + 内部双引号 |
| bcrypt hash 跨平台 | Windows / Linux 不一致 | 统一用 `bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())` |
| `get_idp()` 加 @lru_cache | 切 .env 不生效 | 禁止缓存（反模式 E1）|
| 4 stub 忘加测试 | 未来真实现时不知道接口契约 | 每个 stub 至少 1 个 NotImplementedError 测试 |
| `max_visibility` 字符串 vs Enum | 比较时类型不匹配 | 永远用 `Visibility` 枚举值 |
| dept_mapping 唯一约束漏 index | 查询慢 | `external_provider` / `internal_code` 都加 index |

---

## 9. 参考资料

- SQLAlchemy 2.0 async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- alembic async pattern: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
- bcrypt 用法: https://github.com/pyca/bcrypt
- 飞书 OAuth（stub 实现参考）: https://open.feishu.cn/document/server-docs/authentication-management/login-state-management/web_app/login_user_oauth
- 企微 OAuth（stub 实现参考）: https://developer.work.weixin.qq.com/document/path/91022
- 微信开放平台扫码登录: https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
- 本项目：`CLAUDE.md` 铁律 #1 #2 / `docs/CODEX_QUICK_REF.md` / `app/models/document_meta.py`（已锚定）

---

## 10. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 spec + SQLAlchemy 2.0 async pattern | 30 分钟 |
| pyproject 加依赖 + .env.example 加段落 | 20 分钟 |
| config.py 加字段 + 校验 | 20 分钟 |
| alembic init + env.py 接入 settings | 45 分钟 |
| db/base.py + db/models/dept_mapping.py | 30 分钟 |
| 首个 migration autogenerate + 审核 | 30 分钟 |
| db/repos/dept_mapping.py | 30 分钟 |
| services/auth.py 完整实现（含 4 stub）| 90 分钟 |
| services/auth_mock.py + models/auth.py | 20 分钟 |
| api/auth.py + router 接入 | 20 分钟 |
| test_dept_mapping.py 4 个 integration | 60 分钟 |
| test_auth.py 6+ 个 unit | 60 分钟 |
| QUICK_REF 更新 | 15 分钟 |
| 验证 alembic upgrade + 端到端登录 | 30 分钟 |
| Self-Review + Handoff | 60 分钟 |
| 提交 + PR + CI | 20 分钟 |
| **合计** | **~9 小时（2-3 工作日）** |

---

## 11. 与下一轮的衔接

#67 完成后，下面任务可以放心启动：

1. **#24 客户主数据表**：alembic 已就位，直接 `alembic revision -m "create customer tables"` 加新表
2. **#42 ACL 中间件（Phase 2 Week 6）**：
   - 用 `Depends(get_current_user)` 拿 `User` 上下文
   - 读 `user.internal_dept_code` / `user.max_visibility` / `user.allowed_depts`
   - 构造 Qdrant filter（结合 document_meta 5 字段）
3. **4 个真实 OAuth provider 落地**：作为 #42 的子任务或独立 chore，按业务方拍板的厂家先实现 1-2 个

Handoff §7 应说明：

1. alembic 已初始化，后续表迁移都走 `alembic revision`
2. IdP 抽象入口：`get_idp()`，切换 provider 改 `IDP_PROVIDER`
3. 4 个 stub provider 等待实现，搜 `NotImplementedError` 找入口
4. `User` schema 是 ACL 中间件的输入契约
5. `dept_mapping` 表为飞书/企微/钉钉部门 ID 提供 internal_code 映射，业务侧统一用 `internal_code`
6. LocalIdP 是开发期 / IdP 故障兜底，**生产部署前应禁用**（settings 加校验）

---

## 12. 与 Q1 (document_meta schema) 的集成点

本任务直接 import 了 `app.models.document_meta.Visibility` 用于：

- `User.max_visibility` 字段类型
- `_ROLE_MAX_VISIBILITY` 映射表

这是 Q1 锚定 schema 的第一个下游消费者。如果 Visibility 枚举值后续需要调整，本任务和 Q1 schema 必须同步改。

---

_v1.0 | 任务 ID：#67 | 最后更新：2026-06-05_
