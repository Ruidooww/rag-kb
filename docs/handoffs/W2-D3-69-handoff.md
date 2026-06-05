# Handoff: 任务 #69 - CRM 抽象层 + MockCRM + 工具注册

> **执行者**：Codex
> **完成日期**：2026-06-05
> **分支**：feat/W2-D3-69-crm-abstraction
> **PR**：#15 - https://github.com/Ruidooww/rag-kb/pull/15
> **基于**：docs/handoffs/W2-D1-67-handoff.md

---

## 0. TL;DR

🟡 **总评**：NEEDS_REVIEW（#69 已本地验收通过；#68/#70 未合并导致两处过渡实现）

### 关键数据
- PR：#15
- 主体 commit：`853b228a423be54beab426083e3fffc651fe55c5`
- #69 目标测试：`41 passed`
- 非 integration 全量：`87 passed, 19 deselected`，coverage `80%`
- 完整 pytest：`102 passed, 4 skipped`
- ruff / format / mypy / pip check：全部通过
- 新增第三方依赖：无

### 最大风险
#68 / #70 尚未合并，本任务按 #69 spec §12 使用过渡实现：`app.core.audit` 当前是 no-op 装饰器，`search_docs` / `search_external_docs` 是工具注册占位，不代表真实外部隔离和审计落库已经完成。

### 最大亮点
CRM vendor 选择前已经冻结 `CRMService` ABC、`get_crm()` 工厂、MockCRM fixture 和 `EXTERNAL_TOOLS` / `INTERNAL_TOOLS` 物理隔离，后续业务代码可以先基于 mock 开发。

### 给审查者的 3 个看点
1. `backend/app/services/crm.py:33` 的 `CRMService` 接口是否覆盖 Phase 2 客户对比 / 服务路径的最小数据需求。
2. `backend/app/agents/tools/crm_tools.py:19` 的 `_check_internal()` 是否足够作为 #69 的工具层二次校验。
3. `backend/app/agents/tool_registry.py:14` / `:16` 是否明确保证 CRM 工具只进入 `INTERNAL_TOOLS`。

---

## 1. 任务概述

本任务落地 CLAUDE.md 铁律 #9：业务代码通过统一 CRM 抽象层访问客户、合同、联系人、服务历史，不直接绑定任何 CRM 厂商 SDK。同时建立 LangGraph 工具注册中心，用 `user.is_external` 选择内外工具集，把 CRM 工具物理隔离在内部工具集中。

---

## 2. 完成清单（对应 spec §4）

- [x] `backend/app/core/config.py` 追加 `crm_provider` / `mock_crm_data_path`
- [x] `.env.example` 追加 CRM 配置段
- [x] `backend/app/models/crm.py` 新增 `Customer` / `Contract` / `Contact` / `ServiceHistory`
- [x] `backend/app/services/crm.py` 新增 `CRMService` ABC、`CRMError`、4 个 vendor stub、`get_crm()`
- [x] `backend/app/services/crm_mock.py` 新增 MockCRM YAML fixture loader
- [x] `data/mock_crm/*.yaml` 新增虚构 CRM fixture（5 个客户）
- [x] `backend/app/agents/tools/crm_tools.py` 新增 5 个 CRM tools
- [x] `backend/app/agents/tools/search_tools.py` 新增 search tool 占位
- [x] `backend/app/agents/tool_registry.py` 新增 `EXTERNAL_TOOLS` / `INTERNAL_TOOLS`
- [x] `backend/app/agents/factory.py` 新增 `build_agent(user)`
- [x] `backend/app/core/audit.py` 新增 #70 前置兼容 no-op audit 接口
- [x] `backend/tests/services/test_crm_mock.py`
- [x] `backend/tests/services/test_crm_factory.py`
- [x] `backend/tests/services/test_crm_stubs.py`
- [x] `backend/tests/agents/test_crm_tools.py`
- [x] `backend/tests/agents/test_factory.py`
- [x] `backend/tests/agents/test_tool_registry.py`
- [x] `docs/CODEX_QUICK_REF.md` 新增 CRM 抽象层速查
- [x] `.gitignore` 放行 `data/mock_crm/*.yaml`

---

## 3. 与 Spec 的偏差

- **偏差 1：#70 审计未真实落库**
  - Spec 原文：CRM tools 挂 `@audit(event_type=CRM_QUERY)` 并验证 audit_logs 多 1 条
  - 实际实现：`backend/app/core/audit.py` 提供 no-op 兼容装饰器
  - 理由：#70 尚未合并；#69 spec §12 明确允许未合并时先实现临时 no-op，#70 后切换
  - Commit：`853b228a423be54beab426083e3fffc651fe55c5`
  - 影响：当前不能证明 CRM_QUERY 审计落库；#70 是必须 follow-up

- **偏差 2：`search_docs` / `search_external_docs` 是占位工具**
  - Spec 原文：`tool_registry.py` 导入搜索工具并区分内外
  - 实际实现：`backend/app/agents/tools/search_tools.py` 先返回 placeholder 字符串
  - 理由：#68 external collection / #42 ACL 尚未落地，本任务只冻结工具集边界
  - Commit：`853b228a423be54beab426083e3fffc651fe55c5`
  - 影响：Agent 工具集选择可测，但真实搜索隔离仍待 #68/#42

- **偏差 3：#71 的 JSON snapshot 未在本 PR 落地**
  - Spec 原文：#69 提到 snapshot test；#71 是独立 follow-up，要求 JSON snapshot
  - 实际实现：#69 内先用 `backend/tests/agents/test_tool_registry.py` 固化工具名；JSON snapshot 留给 #71
  - Commit：`853b228a423be54beab426083e3fffc651fe55c5`
  - 影响：#69 已有工具集断言；#71 需要升级为可读 JSON 快照

- **偏差 4：未更新 `docs/architecture.md`**
  - Spec 原文：如已存在则更新
  - 实际实现：当前仓库无 `docs/architecture.md`
  - Commit：`853b228a423be54beab426083e3fffc651fe55c5`
  - 影响：无文件缺失；架构说明先落在 QUICK_REF，后续如新增 architecture.md 再补图

---

## 4. 本地验收结果

| 项目 | 结果 | 备注/原始输出摘要 |
|------|------|------------------|
| `uv sync` | ✅ | `Resolved 130 packages`; `Checked 128 packages` |
| #69 目标测试 | ✅ | `41 passed, 1 warning in 1.49s` |
| 非 integration 全量 + coverage | ✅ | `87 passed, 19 deselected, 2 warnings`; coverage `80%` |
| 完整 `pytest -v` | ✅ | `102 passed, 4 skipped, 2 warnings in 146.79s` |
| `uv run ruff check .` | ✅ | `All checks passed!` |
| `uv run ruff format --check .` | ✅ | `67 files already formatted` |
| `uv run mypy app` | ✅ | `Success: no issues found in 40 source files` |
| `uv pip check` | ✅ | `All installed packages are compatible` |
| 铁律 grep | ✅ | 无 `dashscope` / `print(` / CRM SDK import / `# type: ignore`；无非 llm 直连 OpenAI import |

### 关键命令原始输出摘要

```text
uv run pytest tests/services/test_crm_mock.py tests/services/test_crm_factory.py tests/services/test_crm_stubs.py tests/agents/test_crm_tools.py tests/agents/test_factory.py tests/agents/test_tool_registry.py -v
41 passed, 1 warning in 1.49s

uv run pytest -v -m "not integration" --cov=app --cov-report=term-missing --cov-report=xml
87 passed, 19 deselected, 2 warnings in 31.89s
TOTAL 902 statements, 181 missed, 80%

uv run pytest -v
102 passed, 4 skipped, 2 warnings in 146.79s

uv run ruff check .
All checks passed!

uv run ruff format --check .
67 files already formatted

uv run mypy app
Success: no issues found in 40 source files

uv pip check
Checked 128 packages in 11ms
All installed packages are compatible
```

---

## 5. 已知问题 / 风险

- **审计是 no-op**：`backend/app/core/audit.py` 是 #70 前的兼容层，不落库。#70 合并时必须替换为真实 `audit_logs`。
- **搜索工具是 placeholder**：`search_docs` / `search_external_docs` 只用于冻结工具集形态，不能当作真实检索能力。
- **Agent 真实运行未验证**：`build_agent()` 工具集选择已测；但 `create_react_agent(get_llm(), tools)` 的真实模型适配需后续 Agent 任务验证。
- **敏感字段脱敏未落 API**：本任务没有新增 CRM API endpoint，因此 phone/email/amount 暂只存在工具返回；正式 API 必须经 `sanitize(payload, user)`。
- **完整 pytest 有 4 个 skip**：与真实 LLM/Rerank API key 或生成问答依赖有关，非本 PR 新增。

### 新增第三方依赖

无。

---

## 6. 给审查者的提示

- **重点 1**：`backend/app/services/crm.py:33` 的 `CRMService` 是后续 vendor 适配契约；不要在业务层绕过 `get_crm()`。
- **重点 2**：`backend/app/services/crm_mock.py:17` 的 MockCRM lazy load 只读 YAML，不写文件，避免测试间污染。
- **重点 3**：`backend/app/agents/tools/crm_tools.py:19` 的 `_check_internal()` 是工具层冗余防御；即使未来 router/ACL 做了校验也不要删。
- **重点 4**：`backend/app/agents/tool_registry.py:14` 明确 `EXTERNAL_TOOLS = [search_external_docs]`；CRM 工具只在 `INTERNAL_TOOLS`。
- **重点 5**：`backend/app/core/audit.py:11` 是过渡接口，#70 必须替换为真实 enum + decorator + persist。

---

## 7. 给下一轮的提示

- **上下文 1**：#71 直接在 `backend/tests/agents/test_tool_registry.py` 基础上升级，新增 `tool_registry_snapshot.json`，不要改 `tool_registry.py` 本体。
- **上下文 2**：CRM 厂家拍板后，只实现 `backend/app/services/crm.py` 中对应 stub provider；业务代码继续走 `get_crm()`。
- **上下文 3**：#70 合并时替换 `backend/app/core/audit.py`，并给 CRM tools 增加真实 `crm_query` audit 落库验证。
- **上下文 4**：#68/#42 落地后，把 `backend/app/agents/tools/search_tools.py` 的 placeholder 接入真实内部/外部检索。
- **上下文 5**：正式 CRM API endpoint 必须挂 internal router，并在 API 层做 P1 脱敏。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|----|------|------|
| A1 全项目 pytest | ✅ | `102 passed, 4 skipped, 2 warnings in 146.79s` |
| A2 静态检查 | ✅ | ruff check / format / mypy 全通过 |
| A3 铁律 grep | ✅ | 无 dashscope / print / CRM SDK import / type ignore；无非 llm OpenAI 直连 |
| A4 spec §4 文件 | ✅ | 见 §2；`docs/architecture.md` 不存在故未更新 |
| A5 依赖安全扫描 | ✅ | 无新增依赖；`uv pip check` 通过 |
| A6 commit message | ✅ | `feat: add CRM abstraction and tool registry` + `Refs: #69` |
| A7 Handoff 完整性 | ✅ | 本文件含 §0-§8 |
| A8 CI 复现 | ⚠️ | PR #15 当前 `mergeable=MERGEABLE`，`mergeStateStatus=UNSTABLE`，需等远端 checks 稳定 |

### Part B 软指标

**B1 错误处理**：`backend/app/services/crm.py:142` 对未知 `CRM_PROVIDER` 抛 `CRMError`；4 个 vendor stub 均显式 `NotImplementedError`，不会静默返回空数据；CRM tools 对外部 user 抛 `PermissionDeniedError`。

**B2 偏差**：见 §3。主要偏差是 no-op audit、search placeholder、#71 JSON snapshot 延后。

**B3 安全**：`backend/app/agents/tool_registry.py:14` / `:16` 物理拆分工具集；`backend/app/agents/tools/crm_tools.py:19` 二次校验外部 user；无真实 CRM SDK import。

**B4 性能与副作用**：MockCRM 首次读取 YAML 后缓存在内存；不写文件、不连外部 API。`get_crm()` 未缓存，避免切 `.env` 不生效。

**B5 可测性**：MockCRM、factory、4 个 stub、CRM tools、tool registry、agent factory 均有测试；#69 目标测试 `41 passed`。

**B6 配置合规**：CRM provider 配置集中在 `backend/app/core/config.py:42` / `:43`，`.env.example` 已同步。

**B7 并发与线程安全**：本任务无 DB/HTTP client；MockCRM lazy load 无写操作，测试期安全。

**B8 下一轮暗坑**：#70 替换 `audit.py` 时要保持装饰器签名兼容；#71 改 JSON snapshot 时不要把 CRM 工具误放 `EXTERNAL_TOOLS`。

### Part C 陷阱核查

- C1 ✅ `print(` 无命中
- C2 ✅ 无 `import logging` / `from logging import` 新增；既有 `import logging as stdlib_logging` 非本 PR 引入
- C3 ⚠️ 既有 `backend/app/main.py` CORS localhost 硬编码仍存在，非本 PR 引入
- C4 ✅ `# type: ignore` 无命中
- C5 ✅ 无 `except: pass` / `except Exception: pass`
- C6 ✅ 本任务未新增 except 重抛场景
- C7 ✅ 无新增文件写入 / HTTP client / DB session
- C8 ✅ `get_crm()` / `build_agent()` 均未缓存
- C9 ✅ 本任务无 API endpoint
- C10 ✅ 无 `time.sleep` / `requests.get/post`
- C11 ✅ 新增配置走 settings
- C12 ✅ 新增 env 已加入 `.env.example`
- C13 ✅ 本任务无需改 `config.yaml`
- C14 ✅ 无新增依赖
- C15 ✅ MockCRM 不 mock 外部真实服务；本任务默认就不依赖真实 CRM
- C16 ✅ 公共函数/工具均有测试映射
- C17 ✅ import check 通过
- C18 ✅ 本任务无 endpoint 注册

ANTIPATTERNS 对照：规避 E1（工厂不缓存）、J1（未新增 public/internal router，记录为 #68 后续）、K1（未新增 API response，脱敏留到正式 endpoint）。

### Part D 人工触发

- D1-D2 代码量：985 insertions（含测试/fixture/docs），接近 1000 行，建议 review
- D4 修改已有文件数：4（`.env.example` / `.gitignore` / `config.py` / `CODEX_QUICK_REF.md`），未触发 #67 的 7 文件级别
- D5 新增依赖：否
- D6 核心抽象：是，新增 `CRMService` / tool registry / agent factory，建议 review
- D8 Part A 失败：否
- D11 偏差数：4，需 reviewer 关注，均已在 §3 解释

### Part E 自我反思

**E1 三个改进点**：
1. 如果 #70 已先合并，本任务会直接写真实 audit_logs 验证，而不是 no-op audit。
2. 如果 #68 已先合并，`search_docs` / `search_external_docs` 可以直接接真实内外检索工具，而不是 placeholder。
3. #71 应把当前 inline snapshot 升级为 JSON 文件，使工具集变更 diff 更清楚。

**E2 忠告**：后续不要给 `get_crm()` 加 `@lru_cache`。CRM provider 和测试 monkeypatch 都依赖每次按 settings 构建实例，缓存会重演 IdP 工厂的反模式 E1。

**E3 新发现反模式**：无新增反模式。

### 总评

🟡 NEEDS_REVIEW

原因：#69 自身实现和验证已通过，但 #68/#70 尚未合并，本 PR 含 no-op audit 与搜索 placeholder 两处明确过渡实现。Reviewer 应重点确认这些偏差是否按计划由 #70/#68/#42 收尾。

last_verified_commit: `853b228a423be54beab426083e3fffc651fe55c5`
