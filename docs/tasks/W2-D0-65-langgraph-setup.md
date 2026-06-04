# Task #65: 引入 LangGraph 作为 Agent 编排层

> **Phase**: 1 | **位置**: Week 1-Week 2 之间技术栈调整
> **预估工时**: 1.5-2 小时
> **优先级**: 🔒 关键（影响 Phase 3-4 所有 Agent 设计）
> **前置任务**: #15-#22 + #57 + #58 全部完成
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

Week 1 期间我们规划用 LlamaIndex Workflows 做 Agent 编排，但深入评估后发现 **LangGraph 对我们设计的 6 个 Agent 更友好**：

| Agent | LangGraph 优势 |
|-------|--------------|
| Router | conditional_edges 完美匹配意图分发 |
| Comparison | 状态图清晰表达"识别→检索→抽取→对比"4 步 |
| ServicePath | fan-out/fan-in 内置（事件并发抽取后整合）|
| **FreeQA** | `create_react_agent` 一行代码搞定 ReAct 模式 |
| 多 Agent 协作 | 内置 subgraph + handoff |
| 调试 | LangSmith 可视化（业界标准）|

**关键决策**：LlamaIndex 保留作为 RAG 工具层（embedding / LLM / rerank），LangGraph 作为 Agent 编排层。

切换成本极低，因为**我们还没真用 Workflows 写过任何代码**。

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| Week 1 主线全合并 | `gh pr list --state merged --limit 10` | 看到 PR #1-#8 都 merged |
| main 干净 | `git status` | working tree clean |
| backend 可启动 | `cd backend && uv run uvicorn app.main:app` | 正常启动 |

---

## 3. 任务目标

### 3.1 引入 LangGraph 依赖
- pyproject.toml 加 `langgraph` 依赖
- 验证 `from langgraph.graph import StateGraph` 可 import

### 3.2 更新规程文档
- CLAUDE.md 加新铁律 "Agent 编排走 LangGraph，RAG 工具走 LlamaIndex"
- QUICK_REF.md 同步速查
- ANTIPATTERNS.md 预留 G 类（LangGraph 反模式）

### 3.3 创建技术栈更新说明
- 新增 docs/STACK_UPDATE_V2.2.md 记录变更原因 + 影响范围

### 3.4 验证集成可行性
- 写一个最小可运行的 LangGraph + LlamaIndex 集成 demo
- 证明 LangGraph 节点能调 LlamaIndex 抽象层（get_llm / get_embedding / get_reranker）

---

## 4. 输出文件清单

### 4.1 `backend/pyproject.toml`（追加依赖）

```bash
cd backend
uv add langgraph langgraph-checkpoint-sqlite
```

期望追加到 dependencies：
- `langgraph>=0.2`
- `langgraph-checkpoint-sqlite>=2.0`（用于状态持久化）

### 4.2 `CLAUDE.md`（追加新铁律 + 修改"自审查机制 v2.1"章节）

在"七条迁移友好铁律"中追加第 8 条：

```markdown
### 铁律 #8：Agent 编排走 LangGraph，RAG 工具走 LlamaIndex

- ✅ 允许：`from langgraph.graph import StateGraph`
- ✅ 允许：LangGraph 节点调 `from app.services.llm import get_llm`
- ❌ 禁止：业务代码用 LlamaIndex Workflows（除非有强理由且 spec 明示）
- ❌ 禁止：在 LangGraph 节点里直接 import `openai` / `dashscope`
- 分层原则：
  - **RAG 工具层**：LlamaIndex（embedding / LLM / rerank / chunking）
  - **Agent 编排层**：LangGraph（状态图 / 节点 / 条件边 / 工具调用）
  - **桥接**：LangGraph 节点是 Python 函数，可调任何 LlamaIndex 工具
```

### 4.3 `docs/CODEX_QUICK_REF.md`（更新"七条铁律"为"八条铁律"）

在表格末尾追加：

```markdown
| 8 | Agent 编排走 LangGraph | LlamaIndex Workflows 写 Agent | `StateGraph` + 节点函数 |
```

并在"🔍 CodeGraph 用法"和"📋 任务执行 10 步"之间新增一段：

```markdown
## 🧠 Agent 编排（LangGraph）

| 模式 | 用法 |
|------|------|
| 简单 pipeline（BaseQA）| `StateGraph` + 线性节点 |
| 条件分发（Router）| `add_conditional_edges` |
| 并发抽取（ServicePath）| `Send` API fan-out / fan-in |
| 工具调用（FreeQA）| `create_react_agent(llm, tools)` |
| 状态持久化 | `langgraph-checkpoint-sqlite` |

详情：[STACK_UPDATE_V2.2.md](./STACK_UPDATE_V2.2.md)
```

### 4.4 `docs/STACK_UPDATE_V2.2.md`（新建，技术栈更新说明）

新建文件，~150 行，章节：

```markdown
# Stack Update v2.2: LangGraph + LlamaIndex 分层架构

## 0. TL;DR
- LlamaIndex：RAG 工具层（embedding / LLM / rerank）
- LangGraph：Agent 编排层（状态图 / 节点 / 工具）
- 切换成本：极低（Phase 1 未写过 Workflows 代码）

## 1. 变更原因
[详细说明为什么换 LangGraph]

## 2. 新分层架构
[ASCII 架构图：LangGraph 在上，LlamaIndex 在下]

## 3. 对比 LlamaIndex Workflows
[表格对比]

## 4. 6 个 Agent 的新实现思路
- Router：StateGraph + conditional_edges
- BaseQA：StateGraph 线性
- Comparison：StateGraph 4 节点
- ServicePath：StateGraph + Send API（fan-out）
- FreeQA：create_react_agent
- NetworkAgent：StateGraph 简单

## 5. 集成约束
- LangGraph 节点禁止直接 import openai/dashscope（铁律 #1 不变）
- 所有 LLM 调用走 get_llm()（铁律 #8）
- 业务代码不留 LlamaIndex Workflows 残留

## 6. 后续 Phase 3-4 Agent spec 模板调整
[模板示例]
```

### 4.5 `backend/app/agents/__init__.py`（保留空文件）

无需改动，目录结构已存在。

### 4.6 `backend/scripts/verify_langgraph.py`（新建，验证集成）

~50 行 demo，证明 LangGraph + LlamaIndex 抽象层能跑通：

```python
"""验证 LangGraph 能调 LlamaIndex 抽象层。

用法：
    cd backend
    uv run python scripts/verify_langgraph.py
"""
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.llm import get_llm


class State(TypedDict):
    query: str
    response: str


def call_llm(state: State) -> dict:
    llm = get_llm()
    response = llm.complete(f"用一句话回答：{state['query']}")
    return {"response": response.text}


def build_graph():
    graph = StateGraph(State)
    graph.add_node("call_llm", call_llm)
    graph.add_edge(START, "call_llm")
    graph.add_edge("call_llm", END)
    return graph.compile()


def main() -> None:
    app = build_graph()
    result = app.invoke({"query": "什么是 RAG？", "response": ""})
    print(f"LangGraph + LlamaIndex 集成验证：")  # noqa: T201
    print(f"  Query: {result['query']}")  # noqa: T201
    print(f"  Response: {result['response'][:100]}...")  # noqa: T201


if __name__ == "__main__":
    main()
```

注：占位 API Key 时此脚本会因网络调用失败，**可接受**（验证 import 路径就够）。
如有真实 Key 可跑通完整流程。

### 4.7 `backend/tests/agents/test_langgraph_setup.py`（新建）

最小冒烟测试，证明 LangGraph 安装成功：

```python
"""LangGraph 集成冒烟测试。"""
import pytest


def test_langgraph_imports() -> None:
    """验证 LangGraph 核心 API 可 import。"""
    from langgraph.graph import END, START, StateGraph

    assert StateGraph is not None
    assert START is not None
    assert END is not None


def test_langgraph_can_build_graph() -> None:
    """验证可以构建最小图。"""
    from typing import TypedDict

    from langgraph.graph import END, START, StateGraph

    class State(TypedDict):
        value: int

    def increment(state: State) -> dict:
        return {"value": state["value"] + 1}

    graph = StateGraph(State)
    graph.add_node("inc", increment)
    graph.add_edge(START, "inc")
    graph.add_edge("inc", END)
    app = graph.compile()

    result = app.invoke({"value": 0})
    assert result["value"] == 1
```

这两个测试**不需要 API Key**，CI 能跑过。

### 4.8 `docs/ANTIPATTERNS.md`（预留 G 类占位）

末尾索引表后追加占位段落：

```markdown
## G. LangGraph

（暂无反模式 - 待积累。常见候选：State 设计混乱、节点内调用副作用、checkpoint 缺失等。）
```

---

## 5. 验收标准（Definition of Done）

### 5.1 依赖安装
- [ ] `cd backend && uv sync` 成功
- [ ] `uv pip list | grep langgraph` 显示已安装

### 5.2 测试通过
- [ ] `uv run pytest tests/agents/test_langgraph_setup.py -v` 全绿
- [ ] 整体 `uv run pytest -m "not integration"` 不退化（保持 #20 的 13 passed）

### 5.3 验证脚本可 import（不强制跑通）
- [ ] `uv run python -c "from backend.app.services.llm import get_llm; from langgraph.graph import StateGraph"` 无报错
- [ ] verify_langgraph.py 至少能 import 成功

### 5.4 规程文档更新
- [ ] CLAUDE.md 含铁律 #8
- [ ] CODEX_QUICK_REF.md 八条铁律 + LangGraph 章节
- [ ] STACK_UPDATE_V2.2.md 6 个章节齐全
- [ ] ANTIPATTERNS.md 含 G 类占位

### 5.5 静态检查
- [ ] ruff check / format / mypy 全绿

### 5.6 七条铁律 grep 仍干净
- [ ] `grep -r "from llama_index.core.workflow" backend/app/` 无命中
- [ ] `grep -rE "import openai|from openai" backend/app/` 仅 llm.py（不变）

### 5.7 Handoff + Git
- [ ] Handoff §0-§8 完整
- [ ] commit message 含 `Refs: #65`
- [ ] PR 标题含 `#65`

---

## 6. 禁止事项

- ❌ 不要**实际实现**任何 Agent（Router / Comparison / 等留到 Phase 3-4）
- ❌ 不要把 LangGraph 引入到 backend/app/services/llm.py（保持纯 LlamaIndex）
- ❌ 不要删除 LlamaIndex 依赖（仍是 RAG 工具层）
- ❌ 不要修改任何已有的 .py 业务逻辑（本任务只加新文件 + 改规程文档）
- ❌ 不要安装 langchain 完整包（只装 langgraph + checkpoint）
- ❌ 不要在 verify_langgraph.py 里硬编码模型名（用 get_llm 抽象）

---

## 7. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| 装错 langgraph 包名 | import 失败 | `langgraph`（不是 `langchain-langgraph`）|
| State 用 dict 而非 TypedDict | 类型不安全 + mypy 报错 | 必须用 TypedDict |
| 在节点函数里 catch 全部异常 | 隐藏 bug | 让异常上抛，由 LangGraph 处理 |
| 误把 verify 脚本算业务代码 | 触发铁律 grep | 放 `scripts/` 而非 `app/` |
| CLAUDE.md 把"七条铁律"标题改成"八条"但漏改 QUICK_REF | 文档不一致 | 两个文档同时改 |
| ANTIPATTERNS G 类直接列反模式 | 没经过实战 | 占位即可（v1.1 维护原则）|

---

## 8. 参考资料

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph + LlamaIndex 集成示例](https://langchain-ai.github.io/langgraph/cloud/how-tos/llamaindex_integration/)
- 本项目：`CLAUDE.md` / `docs/CODEX_QUICK_REF.md`
- `docs/handoffs/W1-D5-22-handoff.md`（Week 1 总结，含 §7 给 Week 2 上下文）

---

## 9. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 QUICK_REF + 本 spec | 15 分钟 |
| `uv add langgraph` + verify import | 5 分钟 |
| 写 verify_langgraph.py + 测试 | 20 分钟 |
| 写 STACK_UPDATE_V2.2.md | 30 分钟 |
| 改 CLAUDE.md / QUICK_REF / ANTIPATTERNS | 20 分钟 |
| Self-Review + Handoff | 30 分钟 |
| 提交 + PR | 10 分钟 |
| **合计** | **~2 小时** |

---

## 10. 与下一轮的衔接

#65 完成后，**Phase 3-4 所有 Agent spec 必须基于 LangGraph 写**：

- #44 Comparison Agent → StateGraph 4 节点
- #47 ServicePath Agent → StateGraph + Send fan-out
- #49 FreeQA Agent → create_react_agent
- #56 NetworkAgent → StateGraph 简单图

Handoff §7 应说明：
1. LangGraph 已就绪可用
2. STACK_UPDATE_V2.2.md 里有 6 个 Agent 的实现思路
3. 任何新 Agent spec 模板都要遵循铁律 #8

---

_v1.0 | 任务 ID：#65 | 最后更新：2026-06-04_
