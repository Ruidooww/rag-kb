# Handoff: 任务 #67 - IdP 抽象层 + dept_mapping + LocalIdP

> **执行者**：Codex
> **完成日期**：2026-06-05
> **分支**：feat/W2-D1-67-idp-abstraction
> **PR**：#14
> **基于**：docs/handoffs/W2-D0-65-handoff.md

---

## 0. TL;DR

🔴 **总评**：NEEDS_HUMAN（必须人工 review，禁止自动合并）

### 关键数据
- 新增有效代码：1073 行（按 v2.1 D1-D3 口径，已排除 lock/handoff/tasks/reviews）
- PR：#14 - https://github.com/Ruidooww/rag-kb/pull/14
- 覆盖率：75%（`46 passed, 19 deselected`，CI 路径 `-m "not integration"`）
- #67 新增测试：21 passed（services/api/db）
- #67 DB integration：4 passed
- Alembic：`upgrade head` / `downgrade -1` / `upgrade head` 全部通过，当前 `0001 (head)`
- Self-review：A 部分非集成通过；完整 `pytest -v` 超时；D3/D4/D5/D6 硬触发

### 最大风险
本 PR 初始化 Alembic、增加 SQLAlchemy/IdP 抽象并修改 7 个既有文件，超过 v2.1 自动合并阈值，需要 reviewer 重点看边界和依赖 license。

### 最大亮点
业务代码通过 `get_idp()` 获取身份源，飞书/企微/微信均为 stub，当前不引入任何真实 IdP SDK，LocalIdP 带 production 防呆。

### 给审查者的 3 个看点
1. `backend/app/services/auth.py:78` LocalIdP production 防呆是否符合预期。
2. `backend/app/db/base.py:16` 使用 `NullPool` 是为避免 Windows/pytest asyncpg 跨 event loop 复用连接。
3. `backend/migrations/versions/0001_dept_mapping.py` migration 是否严格对应 ORM 表结构和唯一约束。

---

## 1. 任务概述

本任务建立身份认证抽象层：统一 `IdentityProvider` 接口、`User` schema、`get_idp()` 工厂和开发期可跑的 `LocalIdP`。同时初始化 Alembic，新增 `dept_mapping` 表和 async repository，给后续 #24 数据表迁移、#42 ACL 中间件和外部/内部工具分流提供基础。

真实 OAuth provider 仅保留 `FeishuIdP` / `WeComIdP` / `WeChatOpenIdP` / `WeChatMpIdP` stub，不接入第三方 SDK；LocalIdP 用户来自 `LOCAL_USERS` JSON，并硬编码 `User.is_external=False`。

---

## 2. 完成清单（对应 spec §4）

- [x] `backend/pyproject.toml` 追加 `alembic` / `sqlalchemy[asyncio]` / `asyncpg` / `bcrypt` / `psycopg2-binary`
- [x] `.env.example` 追加 `POSTGRES_URL_SYNC` / `APP_ENV` / `ALLOW_LOCAL_IDP_IN_PROD` / `IDP_PROVIDER` / `LOCAL_USERS`
- [x] `backend/app/core/config.py` 追加 IdP、生产防呆和 PostgreSQL sync URL settings
- [x] `backend/alembic.ini`
- [x] `backend/migrations/env.py`
- [x] `backend/migrations/script.py.mako`
- [x] `backend/migrations/README`
- [x] `backend/migrations/versions/0001_dept_mapping.py`
- [x] `backend/app/db/base.py`
- [x] `backend/app/db/models/dept_mapping.py`
- [x] `backend/app/db/repos/dept_mapping.py`
- [x] `backend/app/services/auth.py`
- [x] `backend/app/services/auth_mock.py`
- [x] `backend/tests/db/test_dept_mapping.py`
- [x] `backend/tests/services/test_auth.py`
- [x] `backend/app/api/auth.py`
- [x] `backend/app/models/auth.py`
- [x] `docs/CODEX_QUICK_REF.md` 新增身份认证速查章节
- [x] `backend/app/api/router.py` 按 spec §4.13 注释注册 `auth.router`
- [x] `backend/app/db/models/__init__.py` / `backend/app/db/repos/__init__.py` 作为包导出支撑

---

## 3. 与 Spec 的偏差

- **偏差 1：env 模板路径**
  - Spec 原文：`backend/.env.example`
  - 实际实现：更新仓库根目录 `.env.example`
  - 理由：当前项目实际只有根目录 `.env.example`，不存在 `backend/.env.example`
  - Commit：39a5c6abb029c4b6659625abcdd1b959b684732c
  - 影响：无运行影响；审查时按现有项目结构看 root `.env.example`

- **偏差 2：`APP_ENV` 兼容旧值**
  - Spec 原文：`Literal["dev", "staging", "production"]`
  - 实际实现：`Literal["dev", "development", "staging", "production"]`
  - 理由：本地历史 `.env` 使用 `APP_ENV=development`，直接删除会导致现有环境启动失败
  - Commit：39a5c6abb029c4b6659625abcdd1b959b684732c
  - 影响：向后兼容；production 防呆仍只对 `production` 生效

- **偏差 3：migration 生成方式**
  - Spec 原文：`alembic revision --autogenerate -m "create dept_mapping table"` 生成后审核
  - 实际实现：首次 autogenerate 时 Docker/Postgres 未启动，连接失败；随后手写 `0001_dept_mapping.py` 并用真实 PG 验证 upgrade/downgrade
  - Commit：39a5c6abb029c4b6659625abcdd1b959b684732c
  - 影响：migration 已通过真实数据库验收；需要 reviewer 对照 ORM 再审一遍

- **偏差 4：AsyncEngine 使用 `NullPool`**
  - Spec 原文：示例未指定 pool
  - 实际实现：`backend/app/db/base.py:16` 使用 `poolclass=NullPool`
  - 理由：Windows + pytest asyncpg 复用 pooled connection 时触发跨 event loop 错误；NullPool 让集成测试稳定
  - Commit：39a5c6abb029c4b6659625abcdd1b959b684732c
  - 影响：低并发 MVP 可接受；生产连接池策略后续可单独优化

- **偏差 5：清理既有测试 `type: ignore`**
  - Spec 原文：未要求修改 `backend/tests/models/test_document_meta.py`
  - 实际实现：把 `DocumentMetaSchema(visibility="secret")  # type: ignore[arg-type]` 改成 `model_validate(...)`
  - 理由：v2.1 C4 要求无未说明的 `# type: ignore`
  - Commit：39a5c6abb029c4b6659625abcdd1b959b684732c
  - 影响：只影响测试表达方式，不影响业务代码

---

## 4. 本地验收结果

| 项目 | 结果 | 备注/原始输出摘要 |
|------|------|------------------|
| `uv sync` | ✅ | `Resolved 130 packages in 3ms; Checked 128 packages in 25ms` |
| #67 新增测试 | ✅ | `21 passed, 1 warning in 8.09s` |
| #67 DB integration | ✅ | `4 passed, 1 warning in 2.70s` |
| `uv run pytest -v -m "not integration" --cov=app` | ✅ | `46 passed, 19 deselected, 2 warnings`; coverage `75%` |
| `uv run pytest -v` | ❌ | 超过 304s 被工具 timeout，无可用输出；当前 Docker 缺 RustFS，历史 storage integration 无法稳定全跑 |
| `uv run ruff check .` | ✅ | `All checks passed!` |
| `uv run ruff format --check .` | ✅ | `52 files already formatted` |
| `uv run mypy app` | ✅ | `Success: no issues found in 31 source files` |
| Alembic `upgrade/downgrade/upgrade/current` | ✅ | `Running downgrade 0001 ->`; `Running upgrade -> 0001`; final `0001 (head)` |
| PG 表结构 | ✅ | `dept_mapping` 含 7 个字段、主键、2 个 index、`uq_provider_dept` |
| `uv pip check` | ✅ | `All installed packages are compatible` |
| `uv pip list --outdated` | ✅ | 列出既有过期包：`boto3` / `botocore` / `openai` / `ruff` 等；非本 PR 新增导致 |
| 铁律 grep | ✅ | `print` / `logging` / `dashscope` / 非 llm OpenAI import / IdP SDK import / API key 全无命中 |
| 配置合规 grep | ⚠️ | #67 无新增硬编码；既有 `backend/app/main.py:35` 仍有 `http://localhost:3000` |
| commit message | ✅ | `feat: add IdP abstraction and dept mapping`，body 含 `Refs: #67` |
| CI workflow | ❌/待重跑 | Handoff 提交前 run 27018727625 失败于 A7：未找到 task #67 handoff；本文件提交后需自动重跑 |

### 关键命令原始输出摘要

```text
uv run pytest tests/services/test_auth.py tests/api/test_auth.py tests/db/test_dept_mapping.py -v
21 passed, 1 warning in 8.09s

uv run pytest -v -m "not integration" --cov=app --cov-report=term-missing --cov-report=xml
46 passed, 19 deselected, 2 warnings in 50.53s
TOTAL 629 statements, 158 missed, 75%

uv run ruff check .
All checks passed!

uv run ruff format --check .
52 files already formatted

uv run mypy app
Success: no issues found in 31 source files

uv pip check
Checked 128 packages in 11ms
All installed packages are compatible
```

---

## 5. 已知问题 / 风险

- **必须人工 review**：Part D 命中 D3/D4/D5/D6。新增有效代码 1073 行、修改 7 个 main 既有文件、新增第三方依赖、修改 `backend/app/core/config.py`。
- **完整 `pytest -v` 未完成**：本地全量跑超过 304s timeout。当前 Docker 缺 RustFS 服务，历史 storage integration 无法稳定全跑；#67 自身 DB integration 已通过。
- **`psycopg2-binary` license 非白名单**：spec §4.1 明确要求 dev dependency；metadata 显示 `LGPL with exceptions`，不在 MIT/Apache/BSD/ISC 白名单，需要 reviewer 确认可接受。
- **既有 CORS 硬编码**：`backend/app/main.py:35` 仍有 `allow_origins=["http://localhost:3000"]`，非 #67 引入；建议 backlog 移到 settings。
- **`NullPool` 性能取舍**：解决测试/Windows event loop 稳定性，牺牲连接复用；生产优化可后续评估。

### 新增第三方依赖

- `alembic==1.18.4`：License-Expression `MIT`；用途：数据库迁移。
- `sqlalchemy==2.0.50`：License `MIT`；用途：ORM、async session。
- `asyncpg==0.31.0`：License-Expression `Apache-2.0`；用途：异步 PostgreSQL driver。
- `bcrypt==5.0.0`：License `Apache-2.0`；用途：LocalIdP 密码 hash 校验。
- `psycopg2-binary==2.9.12`：License `LGPL with exceptions`；用途：Alembic sync migration driver；需 reviewer 关注。

---

## 6. 给审查者的提示

- **重点 1**：`backend/app/services/auth.py:47` `User.is_external` 默认 `False`，`backend/app/services/auth.py:120` LocalIdP 返回时强制 `is_external=False`，这是后续 EXTERNAL_TOOLS / INTERNAL_TOOLS 分流契约。
- **重点 2**：`backend/app/services/auth.py:78` production 防呆会在 `APP_ENV=production` 且 `ALLOW_LOCAL_IDP_IN_PROD=false` 时抛 `AuthError`，避免上线误用本地账号。
- **重点 3**：`backend/app/services/auth.py:150` 和 `backend/app/services/auth.py:164` 的 WeChat stubs 文档明确未来必须返回 `User.is_external=True` 和 `Visibility.PUBLIC`。
- **重点 4**：`backend/migrations/env.py:21` 优先读取 `settings.postgres_url_sync`，否则从 async URL 派生 psycopg2 URL；这是 Alembic 同步迁移路径。
- **重点 5**：`backend/app/db/base.py:16` 使用 `NullPool` 是为了解决 asyncpg pooled connection 在 pytest 多 event loop 下的 Windows 错误。
- **重点 6**：`backend/app/api/auth.py:17` 只把 `AuthError` 映射成 HTTP 401，其他异常保持 FastAPI 默认 500，不吞错。

---

## 7. 给下一轮的提示

- **上下文 1**：后续 ACL / agent tool 分流直接依赖 `backend/app/services/auth.py:47` 的 `User` schema，尤其 `internal_dept_code` / `role` / `max_visibility` / `allowed_depts` / `is_external`。
- **上下文 2**：IdP 切换入口是 `backend/app/services/auth.py:208` 的 `get_idp()`，改 `.env` 的 `IDP_PROVIDER` 即可切 provider；不要在业务代码里直接 import 外部 IdP SDK。
- **上下文 3**：`backend/app/db/repos/dept_mapping.py:11` 提供 `get_internal_code()`，后续 Feishu/WeCom OAuth 实现可用它把外部部门映射为内部 `dept` code。
- **上下文 4**：后续新增业务表从 `backend/migrations/versions/0001_dept_mapping.py` 模式继续，先改 ORM，再生成/审核 migration，最后 `alembic upgrade head`。
- **上下文 5**：外部微信登录 provider 未来必须走 public route 和 public visibility；见 `backend/app/services/auth.py:150` / `backend/app/services/auth.py:164` stub 文档。
- **上下文 6**：LocalIdP 的 `LOCAL_USERS` 格式在 `.env.example`，密码必须 bcrypt hash，测试里使用动态 `bcrypt.hashpw()` 生成，不要提交真实 hash/账号。
- **上下文 7**：RustFS 当前未运行导致完整 integration 不稳定；如果下一轮需要全量 `pytest -v`，先修 9001 端口/RustFS healthcheck。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|----|------|------|
| A1 全项目 pytest | ❌ | `uv run pytest -v` 超过 304s timeout；#67 自身 `21 passed`，CI 路径 `46 passed, 19 deselected`, coverage 75% |
| A2 静态检查 | ✅ | `ruff check`: all passed；`ruff format --check`: 52 files already formatted；`mypy app`: 0 errors |
| A3 七条铁律 + 敏感词 grep | ✅ | `print/logging/dashscope/openai outside llm/IdP SDK/API key` 均无命中；既有 CORS 硬编码另列 C3 |
| A4 spec §4 文件 | ✅ | §2 清单全部完成；必要补充 `router.py` 和 package `__init__.py` |
| A5 依赖安全扫描 | ⚠️ | `uv pip check` 通过；`psycopg2-binary` 为 `LGPL with exceptions`，需 reviewer 审查 |
| A6 commit message | ✅ | `feat: add IdP abstraction and dept mapping`，body `Refs: #67` |
| A7 Handoff 完整性 | ✅ | 本文件含 §0-§8、§3 偏差、§6 6 条、§7 7 条、§8 自审查 |
| A8 CI 复现 | ❌/待重跑 | 首次 CI run 27018727625 因 Handoff 缺失失败；本 commit 推送后应重跑 |

### Part B 软指标

**B1 错误处理**：外部配置解析失败在 `backend/app/services/auth.py:90` 捕获 `json.JSONDecodeError` / `TypeError` 后 `raise AuthError(...) from exc`，保留 stacktrace。Local credential 格式错误在 `backend/app/services/auth.py:96` 捕获 `ValueError` 后同样 `raise ... from exc`。HTTP 层在 `backend/app/api/auth.py:17` 只捕获 `AuthError` 并映射 401，未吞掉未知异常。

Except 列表：
- `backend/app/services/auth.py:90` `except (json.JSONDecodeError, TypeError) as exc` -> `raise AuthError(...) from exc`
- `backend/app/services/auth.py:96` `except ValueError as exc` -> `raise AuthError(...) from exc`
- `backend/app/api/auth.py:17` `except AuthError as exc` -> `raise HTTPException(...) from exc`

**B2 偏差**：见 §3。主要偏差为 root `.env.example`、`APP_ENV=development` 兼容、manual migration、`NullPool`、既有测试 type ignore 清理。

**B3 安全**：`grep` 未发现 API key、手机号、身份证/银行卡号、大额金额、直接 IdP SDK import。`backend/app/services/auth.py:78` 防止 production 默认启用 LocalIdP。`backend/app/services/auth.py:101` 会在 LocalIdP unknown user 时回显 username，当前仅开发期 provider，reviewer 可评估是否改成统一错误。

**B4 性能与副作用**：外部 IO 位置为 `backend/app/db/base.py:16` 创建 PostgreSQL AsyncEngine，`backend/app/db/repos/dept_mapping.py:18` / `backend/app/db/repos/dept_mapping.py:35` 执行 DB query，`backend/app/db/repos/dept_mapping.py:50` flush。未新增 HTTP client 或真实 IdP SDK。`get_idp()` 没有 `@lru_cache`，避免切 `.env` 不生效。

**B5 可测性**：
- `User` -> `backend/tests/services/test_auth.py:42`
- `LocalIdP.exchange_code/get_user_info` -> `backend/tests/services/test_auth.py:56`, `backend/tests/services/test_auth.py:91`, `backend/tests/services/test_auth.py:113`, `backend/tests/services/test_auth.py:121`
- `get_idp()` -> `backend/tests/services/test_auth.py:150`, `backend/tests/services/test_auth.py:165`
- 4 stub provider -> `backend/tests/services/test_auth.py:177`
- `/api/v1/auth/login` -> `backend/tests/api/test_auth.py`
- `dept_mapping_repo.get_internal_code/upsert` -> `backend/tests/db/test_dept_mapping.py`

**B6 配置合规**：`backend/app/core/config.py:27` / `:28` / `:38` / `:39` / `:40` / `:41` 集中管理新增配置；`os.getenv/os.environ` grep 无命中。`backend/app/main.py:35` 存在既有硬编码 CORS URL，非 #67 引入。

**B7 并发与线程安全**：所有 API endpoint 为 async：`backend/app/api/auth.py:12`、`health.py:14`、`query.py:13`。`time.sleep` / `requests.get/post` grep 无命中。`backend/app/db/base.py:16` 使用 `NullPool` 避免 asyncpg connection 跨 event loop 复用。

**B8 下一轮暗坑**：
- `backend/app/db/base.py:16` 的 `NullPool` 是测试稳定性取舍；如果后续压测或上线，要重新评估连接池。
- `backend/app/services/auth.py:130` / `:140` / `:150` / `:164` 都是 stub，业务调用这些 provider 会抛 `NotImplementedError`。
- `backend/app/services/auth.py:208` 的 `get_idp()` 每次创建 provider，不要为了“优化”加 `@lru_cache`。

### Part C 陷阱核查（18 项）

- C1 ✅ `print(` grep 无命中
- C2 ✅ stdlib `import logging` grep 无命中
- C3 ❌ 既有 `backend/app/main.py:35` 有 `http://localhost:3000`；#67 未新增硬编码 URL/端口/模型/秘钥
- C4 ✅ `# type: ignore` grep 无命中
- C5 ✅ 无 `except: pass` / `except Exception: pass`
- C6 ✅ 新增异常链使用 `raise X from exc`
- C7 ✅ DB session 在测试中用 `async with SessionLocal()`；未新增文件/HTTP client
- C8 ✅ `get_idp()` 未使用 `@lru_cache`
- C9 ✅ 新增 endpoint `backend/app/api/auth.py:12` 为 `async def`
- C10 ✅ `time.sleep` / `requests.get/post` grep 无命中
- C11 ✅ 新增配置走 `settings`
- C12 ✅ 新增 env 已加入 `.env.example`
- C13 ✅ 本任务无新增业务参数进入 `config.yaml` 的需求
- C14 ⚠️ 新增第三方依赖已在 §5 说明；`psycopg2-binary` 需 reviewer 审查
- C15 ✅ 测试没有 mock 掉应真实验证的 DB migration/repo；DB integration 真实连本地 PG
- C16 ✅ 新增公共函数/endpoint 均有测试映射，见 B5
- C17 ✅ `uv run python -c "import app.main"` 通过
- C18 ✅ 新增 `/api/v1/auth/login` 已在 `backend/app/api/router.py` 注册

ANTIPATTERNS 对照结果：
- 已检查当前索引：A1, B1, C1, D1, E1, F1, G, H1, H2。
- 命中数：1 个既有命中（C3/CORS 硬编码），非 #67 引入。
- 已规避：B1 `raise ... from exc`、C1 无 `os.getenv`、E1 `get_idp()` 不缓存、I1 未调度 sub-agent 扩范围。

### Part D 人工触发

- D1-D3 代码量：1073 行 -> 🔴 D3 Hard，必须人工 review
- D4 修改已有文件数：7 -> 🔴 Hard，必须人工 review
- D5 新增依赖：`alembic`, `sqlalchemy`, `asyncpg`, `bcrypt`, `psycopg2-binary` -> 🔴 需人工 review；其中 `psycopg2-binary` license 非白名单
- D6 核心抽象改动：是，`backend/app/core/config.py` + `backend/app/services/auth.py` -> 🔴
- D7 公共 API 删改：否，仅新增 `/api/v1/auth/login`
- D8 Part A 失败：是，完整 `pytest -v` timeout
- D9 Part C 失败：是，既有 C3 CORS 硬编码
- D10 覆盖率下降：未与 main coverage.xml 对比；当前 75%，高于 CI 60% 门槛
- D11 偏差数：5 -> 超过 3，需 reviewer 关注

### Part E 自我反思

**E1 三个改进点**：
1. 当前 `backend/app/db/base.py:16` 使用 `NullPool`，重做时会把测试环境和生产环境 engine 配置拆开，让生产继续可用 pool。本次未拆是因为 spec 没定义连接池策略，先保证 Windows/pytest integration 稳定。
2. 当前 `backend/app/services/auth.py:101` 对 unknown user 回显 username，重做时可统一返回 `Invalid credentials` 降低枚举风险。本次保留是为了开发期 LocalIdP debug 直观，且 provider 默认被 production 防呆保护。
3. 当前 `backend/migrations/versions/0001_dept_mapping.py` 是手写 migration，重做时会先确保 Postgres running 后走 autogenerate，再人工审核差异。本次手写后已用真实 PG upgrade/downgrade 验证。

**E2 忠告**：写 IdP 抽象时不要把 provider 实例做全局缓存。`backend/app/services/auth.py:208` 每次按 settings 创建 provider，方便测试 monkeypatch 和 `.env` 切换；这正是 ANTIPATTERNS E1 要规避的问题。

**E3 新发现反模式**：无新增反模式。既有可记录风险是 `psycopg2-binary` license 非白名单，但它是本 spec 明确依赖，不是通用代码反模式。

### 修复轨迹

- fix_attempt:1 (working tree before commit) - DB integration 初次失败：asyncpg pooled connection 跨 pytest event loop；改 `backend/app/db/base.py:16` 为 `NullPool` 后 `tests/db/test_dept_mapping.py` 4 passed。
- fix_attempt:2 (working tree before commit) - C4 命中既有 `# type: ignore`；改 `backend/tests/models/test_document_meta.py` 使用 `model_validate()` 后 grep 无命中。

### 总评

🔴 NEEDS_HUMAN

原因：D3/D4/D5/D6 硬触发，完整 `pytest -v` timeout，且存在既有 C3 CORS 硬编码。#67 自身实现、非集成 CI 路径、DB integration、lint、format、mypy、Alembic 验收均已通过，但必须由 reviewer 审查后再决定合并。

last_verified_commit: 39a5c6abb029c4b6659625abcdd1b959b684732c
