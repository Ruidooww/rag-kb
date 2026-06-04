# Handoff: 任务 #65 - 引入 LangGraph 作为 Agent 编排层

> **执行者**：Codex  
> **完成日期**：2026-06-04  
> **分支**：feat/W2-D0-65-langgraph-setup  
> **PR**：#9  
> **PR URL**：https://github.com/Ruidooww/rag-kb/pull/9  
> **基于**：W1-D5-22-handoff.md

---

## 0. TL;DR

✅ **总评**：PASS（需审查者重点确认新增依赖和铁律 #8 文档口径）

### 关键产出

- 新增 `langgraph` / `langgraph-checkpoint-sqlite` 依赖，实际安装版本分别为 `1.2.4` / `3.1.0`。
- 新增 `backend/tests/agents/test_langgraph_setup.py`，验证 LangGraph 可 import 且可 compile 最小图。
- 新增 `backend/scripts/verify_langgraph.py`，证明 LangGraph 节点可调用 `app.services.llm.get_llm()` 抽象层。
- 更新 `CLAUDE.md` / `docs/CODEX_QUICK_REF.md`，新增铁律 #8：Agent 编排走 LangGraph，RAG 工具走 LlamaIndex。
- 新增 `docs/STACK_UPDATE_V2.2.md`，说明 Phase 3-4 的 6 个 Agent 新实现思路。
- `docs/ANTIPATTERNS.md` 新增 G 类 LangGraph 占位。

### 关键数据

- 新增直接依赖：2 个，license 均为 `MIT`。
- 新增/修改文件：9 个，其中 2 个新增 Python 文件，未修改任何既有业务 `.py`。
- D 代码量过滤后新增 248 行，低于 600 行阈值。
- 本地新冒烟测试：`2 passed`。
- 本地非 integration 回归：`15 passed, 11 deselected, 2 warnings`。
- coverage：`TOTAL 316 83 74%`。

### 风险评估

低到中。本任务没有实现任何实际 Agent，也没有改 `backend/app/services/llm.py` 等核心业务逻辑；主要风险是新增 LangGraph 依赖及其传递依赖体量，需要审查者确认技术栈方向符合预期。PR #9 首次 CI 失败根因是 Step 8 前尚未提交 Handoff，非代码失败；本文件提交后应触发重跑。

---

## 1. 任务概述

本任务把 LangGraph 引入为后续 Agent 编排层，同时保留 LlamaIndex 作为 RAG 工具层。实现范围控制在依赖、规程文档、技术栈说明、验证脚本和冒烟测试，没有实现 Router / Comparison / ServicePath / FreeQA 等实际 Agent。

---

## 2. 完成清单

- [x] `backend/pyproject.toml` 追加 `langgraph` / `langgraph-checkpoint-sqlite`
- [x] `backend/uv.lock` 同步锁定依赖
- [x] `CLAUDE.md` 新增铁律 #8
- [x] `docs/CODEX_QUICK_REF.md` 更新八条铁律和 LangGraph 速查章节
- [x] `docs/ANTIPATTERNS.md` 新增 G 类 LangGraph 占位
- [x] `docs/STACK_UPDATE_V2.2.md`
- [x] `backend/scripts/verify_langgraph.py`
- [x] `backend/tests/agents/test_langgraph_setup.py`
- [x] `docs/tasks/W2-D0-65-langgraph-setup.md`
- [x] 未实现任何实际 Agent
- [x] 未修改 `backend/app/services/llm.py`
- [x] 未删除 LlamaIndex 依赖

---

## 3. 与 Spec 的偏差

- **偏差 1**：提交了 `docs/tasks/W2-D0-65-langgraph-setup.md`。
  - Spec §4 输出清单未列本任务 spec 文件，但该文件是本轮必读输入，且当前在本地未跟踪；按前序任务约定补入 PR，避免合并后 Handoff 引用不存在的 spec。
  - 影响：只增加任务记录文档，不影响运行时代码。
  - Commit：`11fb2c21ae22b59430418bbb8350dc05e78423ab`

- **偏差 2**：`backend/tests/agents/test_langgraph_setup.py` 未保留 spec 示例中的 `import pytest`。
  - 原因：示例 import 未使用，会触发 `ruff F401`；测试不需要 `pytest` 对象。
  - 影响：无行为影响，测试仍覆盖 import 和 compile 两个验收点。
  - Commit：`11fb2c21ae22b59430418bbb8350dc05e78423ab`

- **偏差 3**：未运行完整 integration pytest。
  - 原因：本机当前 Qdrant / infinity 健康探测均为 HTTP status `000`；本任务 spec §5.2 要求整体 `uv run pytest -m "not integration"` 不退化。
  - 影响：不影响本任务 LangGraph 冒烟验收；涉及真实外部服务的 integration 留给服务可用时执行。
  - Commit：N/A

---

## 4. 本地验收结果

| 项目 | 结果 | 备注 |
|------|------|------|
| 分支 | ✅ | `feat/W2-D0-65-langgraph-setup` |
| PR | ✅ | #9, https://github.com/Ruidooww/rag-kb/pull/9 |
| `uv sync` | ✅ | `Resolved 119 packages`, `Checked 117 packages` |
| `uv pip list` | ✅ | `langgraph 1.2.4`, `langgraph-checkpoint-sqlite 3.1.0` |
| LangGraph 冒烟测试 | ✅ | `2 passed, 1 warning in 1.11s` |
| 非 integration 回归 | ✅ | `15 passed, 11 deselected, 2 warnings in 24.66s` |
| coverage | ✅ | `TOTAL 316 83 74%` |
| import 验收 | ✅ | `from app.services.llm import get_llm; from langgraph.graph import StateGraph` 无报错 |
| verify graph compile | ✅ | 输出 `CompiledStateGraph` |
| ruff check | ✅ | `All checks passed!` |
| ruff format --check | ✅ | `31 files already formatted` |
| mypy | ✅ | `Success: no issues found in 19 source files` |
| uv pip check | ✅ | `All installed packages are compatible` |
| 直接依赖 license | ✅ | `langgraph` / `langgraph-checkpoint-sqlite`: `License-Expression: MIT` |
| 铁律 grep 精确扫描 | ✅ | `print` / logging exact / dashscope / Workflows / hardcoded provider / bare openai import / sensitive key 均无命中 |
| GitHub CI | ⚠️ | 首次 run 失败于 A7：Handoff 尚未提交；本提交补齐后需看重跑结果 |

### 关键命令输出

```text
C:\Users\Ruidoww\.local\bin\uv.exe pip list | Select-String -Pattern "langgraph"
langgraph                          1.2.4
langgraph-checkpoint               4.1.1
langgraph-checkpoint-sqlite        3.1.0
langgraph-prebuilt                 1.1.0
langgraph-sdk                      0.4.2
```

```text
C:\Users\Ruidoww\.local\bin\uv.exe run pytest tests/agents/test_langgraph_setup.py -v
tests/agents/test_langgraph_setup.py::test_langgraph_imports PASSED
tests/agents/test_langgraph_setup.py::test_langgraph_can_build_graph PASSED
2 passed, 1 warning in 1.11s
```

```text
C:\Users\Ruidoww\.local\bin\uv.exe run pytest -v -m "not integration"
15 passed, 11 deselected, 2 warnings in 24.66s
```

```text
C:\Users\Ruidoww\.local\bin\uv.exe run pytest -v -m "not integration" --cov=app --cov-report=term-missing --cov-report=xml
TOTAL                            316     83    74%
15 passed, 11 deselected, 2 warnings in 11.46s
```

```text
C:\Users\Ruidoww\.local\bin\uv.exe run ruff check .
All checks passed!

C:\Users\Ruidoww\.local\bin\uv.exe run ruff format --check .
31 files already formatted

C:\Users\Ruidoww\.local\bin\uv.exe run mypy app
Success: no issues found in 19 source files
```

---

## 5. 已知问题 / 风险

- 新增直接依赖 `langgraph` 和 `langgraph-checkpoint-sqlite`，license 均为 `MIT`；传递依赖包含 `langchain-core` / `langsmith` 等，但未安装完整 `langchain` 包。
- PR #9 首次 CI run 失败于 A7 Handoff 检查，日志为 `未找到 task #65 的 handoff 文件`。这是 10 步流程中 Step 8/9 之前的预期失败，本文件提交后应解决。
- `backend/scripts/verify_langgraph.py` 的 `main()` 会真实调用 LLM；当前只验了 import 和 graph compile。没有真实 API Key 时直接运行脚本可能因外部调用失败，这是 spec §4.6 允许的。
- 本机当前 `http://localhost:6333/healthz` 和 `http://localhost:8080/health` 返回 status `000`，因此没有运行完整 integration 测试。
- 既有遗留仍存在：`backend/tests/api/test_health.py:20` 命中 D1（共享 app router），`backend/app/services/llm.py:97-99` 命中 A1（rerank retry 内新建 httpx.Client）；本任务未触碰这些文件。

---

## 6. 给审查者的提示

- **重点 1**：看 `CLAUDE.md:96` 到 `CLAUDE.md:105`，确认铁律 #8 的边界是否符合“LangGraph 编排 / LlamaIndex 工具”的长期方向。
- **重点 2**：看 `docs/STACK_UPDATE_V2.2.md:44` 到 `docs/STACK_UPDATE_V2.2.md:56`，确认从 LlamaIndex Workflows 切到 LangGraph 的理由是否足够。
- **重点 3**：看 `backend/tests/agents/test_langgraph_setup.py:13` 到 `backend/tests/agents/test_langgraph_setup.py:32`，确认冒烟测试只验证 LangGraph compile，不依赖外部服务。
- **重点 4**：看 `backend/scripts/verify_langgraph.py:20` 到 `backend/scripts/verify_langgraph.py:31`，确认 LangGraph 节点调用的是 `get_llm()` 抽象层，而不是 provider SDK。
- **重点 5**：依赖审查时重点看 `backend/pyproject.toml` 的两个直接依赖，以及 Handoff §5 里的 license 说明。

---

## 7. 给下一轮的提示

- #44 Comparison Agent 建议从 `docs/STACK_UPDATE_V2.2.md:68` 到 `docs/STACK_UPDATE_V2.2.md:70` 的 4 节点设计开始，State 里保留对象列表、字段结果、证据引用和最终报告。
- #47 ServicePath Agent 建议参考 `docs/STACK_UPDATE_V2.2.md:72` 到 `docs/STACK_UPDATE_V2.2.md:74`，用 `Send` API 做 fan-out / fan-in。
- #49 FreeQA Agent 可基于 `docs/STACK_UPDATE_V2.2.md:76` 到 `docs/STACK_UPDATE_V2.2.md:78`，但工具内部仍必须调用项目 service 层。
- 新 Agent spec 应增加 `LangGraph 图设计` 章节，模板在 `docs/STACK_UPDATE_V2.2.md:93` 到 `docs/STACK_UPDATE_V2.2.md:120`。
- 所有 Agent 节点调用模型时只能走 `backend/app/services/llm.py:34` 的 `get_llm()`，不能直接 import `openai` / `dashscope`。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|----|------|------|
| A1 pytest | ✅ | LangGraph smoke `2 passed`; non-integration `15 passed, 11 deselected` |
| A1 coverage | ✅ | `TOTAL 316 83 74%` |
| A2 静态检查 | ✅ | ruff check / format / mypy 全通过 |
| A3 铁律 + 敏感词 grep | ✅ | 精确扫描无输出；Workflows import 无命中；bare openai import 无命中 |
| A4 spec 文件清单 | ✅ | §2 文件齐全；额外提交 task spec 见 §3 偏差 1 |
| A5 依赖安全扫描 | ✅ | `uv pip check` compatible；直接依赖 license `MIT` |
| A6 commit message | ✅ | `chore: add LangGraph orchestration setup`，body 含 `Refs: #65` |
| A7 Handoff 完整性 | ✅ | 本文件 §0-§8 齐全，含 `last_verified_commit` |
| A8 CI 复现 | ⚠️ | 首次 CI failed: missing Handoff；本提交补齐后需看 PR #9 最新 run |

### Part B 软指标

**B1 错误处理**：本轮没有新增 `except` 块。`backend/scripts/verify_langgraph.py:20-23` 让 LLM 调用异常自然上抛，符合验证脚本定位；`backend/tests/agents/test_langgraph_setup.py:22-23` 的测试节点没有外部 IO，也不需要异常处理。既有 `backend/app/services/llm.py:103-108` 保留 `raise LLMServiceError(message) from last_error`。

**B2 偏差**：见 §3，共 3 条。核心偏差是提交本任务 spec、去掉未使用 `pytest` import、未跑 integration。均不改变业务行为。

**B3 安全**：新增脚本没有记录 API Key。`backend/scripts/verify_langgraph.py:20-23` 只调用 `get_llm()` 并返回 response text；`backend/app/services/llm.py:41-44` 继续通过 settings 读取 SecretStr。敏感 key scan 对 `backend/app` / `backend/scripts` / `backend/tests` 源码无命中。

**B4 性能与副作用**：新增外部 IO 只有 `backend/scripts/verify_langgraph.py:21-22` 的 LLM completion，且仅在手动运行脚本时发生。`backend/tests/agents/test_langgraph_setup.py:25-31` 只 compile/invoke 本地内存图，没有网络 IO。没有新增缓存、数据库连接或 N+1 查询。

**B5 可测性**：

```text
backend/tests/agents/test_langgraph_setup.py::test_langgraph_imports
  -> 验证 langgraph.graph 的 END / START / StateGraph 可 import

backend/tests/agents/test_langgraph_setup.py::test_langgraph_can_build_graph
  -> 验证 StateGraph 可 add_node / add_edge / compile / invoke

backend/scripts/verify_langgraph.py::build_graph
  -> 通过 `uv run python -c "from scripts.verify_langgraph import build_graph; app = build_graph()"` 验证 compile
```

测试不依赖真实 API Key 或外部服务。

**B6 配置合规**：新增代码没有 `os.getenv()` / `os.environ`。`backend/scripts/verify_langgraph.py:12` 调用 `get_llm()`，真实 URL、模型名、API Key 仍由 `backend/app/services/llm.py:41-48` 从 settings 注入。没有新增环境变量或 `config.yaml` 参数。

**B7 并发与线程安全**：新增代码没有 `async def`，没有共享可变全局状态。`backend/scripts/verify_langgraph.py:15-17` 和 `backend/tests/agents/test_langgraph_setup.py:19-20` 都用 `TypedDict` 定义 state，避免无结构 dict 漂移。精确扫描 `time.sleep|requests.get|requests.post` 无命中。

**B8 下一轮暗坑**：

1. `backend/scripts/verify_langgraph.py:34-39` 会真实调用 LLM，只适合本地手工验证；CI 不应直接跑 `main()`。
2. `docs/STACK_UPDATE_V2.2.md:90` 要求 Agent state 用 `TypedDict` 或 Pydantic schema，后续不要把无结构 `dict` 传满全图。
3. `docs/STACK_UPDATE_V2.2.md:91` 提到 checkpoint 先用 SQLite，生产化前要评估 PostgreSQL checkpoint，避免本地文件状态成为部署瓶颈。

### Part C 陷阱核查（18 项）

- C1 ✅ 新增 `backend/app` 无 `print()`；脚本中的 `print()` 在 `backend/scripts` 且有 `# noqa: T201`。
- C2 ✅ 精确 grep `^import logging$|^from logging import` 无命中。
- C3 ✅ 新增代码未硬编码 URL/端口/模型名/秘钥。
- C4 ✅ 无 `# type: ignore`。
- C5 ✅ 无 `except: pass` 或 `except Exception: pass`。
- C6 ✅ 本轮无新增异常链；既有 `LLMServiceError` 使用 `from last_error`。
- C7 ✅ 新增测试无文件/连接/HTTP client；脚本只手动调用 LLM。
- C8 ✅ 未给 `get_llm()` / `get_embedding()` / `get_reranker()` 加 `@lru_cache`。
- C9 ✅ 本轮无 API endpoint 新增。
- C10 ✅ 本轮无 async 函数，也无 sync 阻塞调用新增。
- C11 ✅ 新增代码无 `os.getenv()`。
- C12 ✅ 无新增环境变量。
- C13 ✅ 无新增业务参数。
- C14 ✅ 新增第三方依赖已在 §5 说明，license 为 MIT。
- C15 ✅ 冒烟测试真实 compile/invoke LangGraph，不 mock import。
- C16 ✅ 新增公共验证函数 `build_graph()` 已用 import/compile 命令覆盖。
- C17 ✅ `uv run python -c "from app.services.llm import get_llm; from langgraph.graph import StateGraph"` 通过；`mypy app` 通过。
- C18 ✅ 未删除/重命名公共 API。

ANTIPATTERNS 对照结果：

- 已检查反模式总数：6 + G 类占位。
- 新增代码命中数：0。
- 既有命中：`backend/tests/api/test_health.py:20` 命中 D1；`backend/app/services/llm.py:97-99` 命中 A1。二者为历史遗留，本轮未修改。

### Part D 人工触发

- D1-D3 代码量：过滤 lock / handoff / tasks 后新增 248 行 → ✅ 通过。
- D4 修改 main 上已有文件数：5 个（`CLAUDE.md` / `backend/pyproject.toml` / `backend/uv.lock` / `docs/ANTIPATTERNS.md` / `docs/CODEX_QUICK_REF.md`）→ ✅ 未超过 5。
- D5 新增依赖：`langgraph` / `langgraph-checkpoint-sqlite`，license 均为 MIT → ✅ 通过例外条件。
- D6 核心抽象改动：否，未改 `backend/app/core/*` 或 `backend/app/services/llm.py`。
- D7 公共 API 删改：否。
- D8 Part A 失败：否；A8 首次失败为 Handoff 缺失，Step 9 后重跑。
- D9 Part C 失败：否；仅记录历史遗留。
- D10 覆盖率下降：否，保持 74%。
- D11 偏差数：3，不超过阈值。

### Part E 自我反思

**E1 三个改进点**：

1. 当前 `backend/scripts/verify_langgraph.py:26` 的 `build_graph()` 返回类型写成 `object`，足够通过验证但不够精确。重做时可以引入 LangGraph compiled graph 的具体类型注解。没改是因为不同 LangGraph 版本公开类型不稳定，当前 mypy 只检查 `app`。
2. 当前 `docs/STACK_UPDATE_V2.2.md:93-120` 给的是通用 Agent spec 模板。重做时可以为 Router / Comparison / ServicePath 各写一个更具体的 State 草图。没改是因为本任务禁止实际实现 Agent，模板不宜过度展开成设计定稿。
3. 当前 `backend/tests/agents/test_langgraph_setup.py:13-32` 只覆盖本地同步图。重做时可以补一个 checkpoint sqlite 的最小持久化测试。没改是因为 spec 只要求安装 checkpoint 依赖，不要求验证持久化行为。

**E2 忠告**：

- 后续写 Agent 时先画 State，再写节点。LangGraph 代码最容易失控的地方不是 `add_node()`，而是 state 字段没有边界；请从 `docs/STACK_UPDATE_V2.2.md:93-120` 的模板开始。

**E3 新发现反模式**：

- 无新增反模式。G 类目前只放占位，不凭空添加未经实战验证的反模式。

### 修复轨迹

- 无代码 fix_attempt。
- CI 调试记录：PR #9 首次 run `26954555975` 失败于 A7 Handoff 完整性检查，日志显示 `未找到 task #65 的 handoff 文件`；本文件为对应修复。

### 总评

✅ PASS（可合并；新增依赖和铁律 #8 文档口径需审查者确认）

last_verified_commit: 11fb2c21ae22b59430418bbb8350dc05e78423ab
