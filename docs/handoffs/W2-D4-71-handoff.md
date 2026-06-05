# Handoff: 任务 #71 - Agent 工具集断言测试

> **执行者**：Codex
> **完成日期**：2026-06-05
> **分支**：feat/W2-D4-71-tool-registry-assertion-test
> **PR**：#16 - https://github.com/Ruidooww/rag-kb/pull/16
> **基于**：docs/handoffs/W2-D3-69-handoff.md

---

## 0. TL;DR

🟢 **总评**：PASS

### 关键数据
- PR：#16
- 主体 commit：`231564e4b1c14db154dd6aff504b759a455119da`
- RED 验证：缺少 `tool_registry_snapshot.json` 时 `test_tool_registry_snapshot` 失败
- #71 目标测试：`3 passed`
- tool_registry 覆盖率：`100%`
- 非 integration 全量：`87 passed, 19 deselected`，coverage `80%`
- 完整 pytest：`102 passed, 4 skipped`
- ruff / format / mypy / pip check：全部通过

### 最大风险
快照测试只能强制工具集变更显式暴露，不能替代 reviewer 判断某个工具是否真的可以对外开放。

### 最大亮点
`EXTERNAL_TOOLS` / `INTERNAL_TOOLS` 当前成员已经固化到 JSON 快照，未来任何工具集增删改都会让测试失败，必须同步更新快照并在 PR 中说明。

### 给审查者的 3 个看点
1. `backend/tests/agents/tool_registry_snapshot.json` 当前工具清单是否符合 #69 设计。
2. `backend/tests/agents/test_tool_registry.py:30` 缺失快照时是否给出明确失败信息。
3. `backend/tests/agents/test_tool_registry.py:46` 是否能覆盖 EXTERNAL / INTERNAL 两组工具快照。

---

## 1. 任务概述

本任务落地 CLAUDE.md 原则 P2：工具集变更必须有断言测试和可 review 的快照。它不修改业务 Agent 或 `tool_registry.py` 本体，只把 #69 已落地的工具集成员固化为 JSON snapshot。

---

## 2. 完成清单（对应 spec §4）

- [x] 修改 `backend/tests/agents/test_tool_registry.py`，从 JSON snapshot 读取期望工具集
- [x] 新增 `backend/tests/agents/tool_registry_snapshot.json`
- [x] `backend/pyproject.toml` 注册 `tool_registry` pytest marker
- [x] 覆盖 CRM / internal search 不得进入 `EXTERNAL_TOOLS`
- [x] 覆盖 EXTERNAL / INTERNAL 无 overlap
- [x] 覆盖工具集快照 diff

---

## 3. 与 Spec 的偏差

无。

---

## 4. 本地验收结果

| 项目 | 结果 | 备注/原始输出摘要 |
|------|------|------------------|
| RED：缺少 snapshot | ✅ | `test_tool_registry_snapshot` failed: `Snapshot file missing...` |
| `uv run pytest tests/agents/test_tool_registry.py -v` | ✅ | `3 passed, 1 warning in 0.44s` |
| `uv run pytest tests/agents/test_tool_registry.py --cov=app.agents.tool_registry --cov-report=term-missing` | ✅ | `tool_registry.py 100%` |
| `uv run pytest -v -m "not integration" --cov=app` | ✅ | `87 passed, 19 deselected`; coverage `80%` |
| `uv run pytest -v` | ✅ | `102 passed, 4 skipped` |
| `uv run ruff check .` | ✅ | `All checks passed!` |
| `uv run ruff format --check .` | ✅ | `67 files already formatted` |
| `uv run mypy app` | ✅ | `Success: no issues found in 40 source files` |
| `uv pip check` | ✅ | `All installed packages are compatible` |

### 关键命令原始输出摘要

```text
uv run pytest tests/agents/test_tool_registry.py -v
3 passed, 1 warning in 0.44s

uv run pytest tests/agents/test_tool_registry.py --cov=app.agents.tool_registry --cov-report=term-missing
app\agents\tool_registry.py 8 statements, 0 missed, 100%

uv run pytest -v -m "not integration" --cov=app --cov-report=term-missing --cov-report=xml
87 passed, 19 deselected, 2 warnings in 40.95s
TOTAL 902 statements, 181 missed, 80%

uv run pytest -v
102 passed, 4 skipped, 2 warnings in 102.94s
```

---

## 5. 已知问题 / 风险

- 快照变更仍需要 PR reviewer 看清楚原因；测试只能防止“悄悄改工具集”。
- `allowed_external` 白名单模式未引入，本任务按当前唯一外部工具 `search_external_docs` 直接固化。
- #69 的 `search_docs` / `search_external_docs` 仍是占位工具；本任务只保护工具集成员，不实现检索能力。

### 新增第三方依赖

无。

---

## 6. 给审查者的提示

- **重点 1**：`backend/tests/agents/tool_registry_snapshot.json` 中 `external_tools` 只有 `search_external_docs`。
- **重点 2**：`backend/tests/agents/test_tool_registry.py:14` 固定 snapshot 路径，缺失时 fail，不会静默跳过。
- **重点 3**：`backend/tests/agents/test_tool_registry.py:46` 同时校验 external/internal 两组快照，工具集变更必须更新 JSON。
- **重点 4**：`backend/pyproject.toml:62` 注册 `tool_registry` marker，避免 pytest warning。

---

## 7. 给下一轮的提示

- **上下文 1**：以后改 `backend/app/agents/tool_registry.py` 时，必须同步改 `backend/tests/agents/tool_registry_snapshot.json`。
- **上下文 2**：如果要新增外部工具，除更新 snapshot 外，还要补对应 prompt-injection / 外部访问测试。
- **上下文 3**：#72 Prompt Injection 测试集可以直接读取当前 `EXTERNAL_TOOLS` 快照作为基线。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|----|------|------|
| A1 全项目 pytest | ✅ | `102 passed, 4 skipped, 2 warnings in 102.94s` |
| A2 静态检查 | ✅ | ruff check / format / mypy 全通过 |
| A3 铁律 grep | ✅ | 本任务只改测试/pyproject，无业务代码 SDK import 风险 |
| A4 spec §4 文件 | ✅ | test 文件、snapshot JSON、marker 已完成 |
| A5 依赖安全扫描 | ✅ | 无新增依赖；`uv pip check` 通过 |
| A6 commit message | ✅ | `test: add #71 tool registry snapshot assertions` + `Refs: #71` |
| A7 Handoff 完整性 | ✅ | 本文件含 §0-§8 |
| A8 CI 复现 | ⚠️ | PR #16 创建后远端 self-review 正在运行；需等 checks 完成 |

### Part B 软指标

**B1 错误处理**：`backend/tests/agents/test_tool_registry.py:30` 在 snapshot 缺失时显式 `pytest.fail(...)`，错误信息含修复指引。

**B2 偏差**：无。

**B3 安全**：测试继续阻止 CRM / internal search 类工具进入 `EXTERNAL_TOOLS`。

**B4 性能与副作用**：只读取一个本地 JSON 文件；测试运行 < 1 秒。

**B5 可测性**：RED / GREEN 已验证；缺 snapshot 会 fail，存在 snapshot 时通过。

**B6 配置合规**：仅注册 pytest marker，无 runtime 配置。

**B7 并发与线程安全**：无并发逻辑。

**B8 下一轮暗坑**：snapshot 被更新不代表变更安全，PR 描述必须说明新增/移除工具原因。

### Part C 陷阱核查

- C1 ✅ 无 `print(`
- C2 ✅ 无新增 logging
- C3 ✅ 无硬编码 runtime URL / 端口 / 模型
- C4 ✅ 无 `# type: ignore`
- C5 ✅ 无异常吞掉
- C6 ✅ 无异常重抛场景
- C7 ✅ 无新增 IO 除读取测试 snapshot
- C8 ✅ 无缓存
- C9 ✅ 无 endpoint
- C10 ✅ 无 sleep / requests
- C11 ✅ 无新增 settings
- C12 ✅ 无新增 env
- C13 ✅ 无 config.yaml 改动
- C14 ✅ 无新增依赖
- C15 ✅ 无 mock 外部真实服务
- C16 ✅ 测试自身是交付物
- C17 ✅ import 由 pytest 覆盖
- C18 ✅ 无 router 改动

### Part D 人工触发

- 代码量小，未触发 D2/D3。
- 修改 `pyproject.toml` 仅注册 marker，不涉及 runtime 依赖。
- 该任务可自动合并，仍建议 reviewer 关注 snapshot 内容。

### Part E 自我反思

**E1 三个改进点**：
1. 后续可以把 PR template 加一项“工具集变更原因”，防止只改 snapshot 不解释。
2. #72 可以读取 snapshot 生成 prompt injection fixture 基线。
3. 如果外部工具扩展为多个，可以把 allowed external 名单也 JSON 化，减少测试内硬编码。

**E2 忠告**：不要用环境变量关闭工具集断言测试。工具集是安全边界，任何变更都必须在代码 review 中显式出现。

**E3 新发现反模式**：无新增反模式。

### 总评

🟢 PASS

last_verified_commit: `231564e4b1c14db154dd6aff504b759a455119da`
