# Stack Update v2.2: LangGraph + LlamaIndex 分层架构

## 0. TL;DR

- LlamaIndex：RAG 工具层，继续负责 embedding、LLM、rerank、chunking 和检索工具封装。
- LangGraph：Agent 编排层，负责状态图、节点、条件边、工具调用和多 Agent 协作。
- 切换成本：极低，Phase 1 尚未用 LlamaIndex Workflows 实现任何 Agent。
- 核心原则：模型调用仍走 `app.services.llm`，Agent 节点只组合已有工具，不绕过抽象层。

## 1. 变更原因

Week 1 已经跑通最小 RAG Pipeline，但 Agent 还没有进入真实实现阶段。原计划使用 LlamaIndex Workflows 做编排，适合 RAG 内部流程，但对 Router、Comparison、ServicePath、FreeQA 这类需要状态分支、并发扇出、工具调用和多 Agent 协作的场景不够直观。

LangGraph 的核心抽象是状态图。节点是普通 Python 函数，边显式表达控制流，条件边适合意图分发，`Send` API 适合 fan-out / fan-in，`create_react_agent` 适合 FreeQA 的 ReAct 模式。这些能力与本项目 Phase 3-4 的 Agent 规划更匹配。

本次调整不替换 LlamaIndex。LlamaIndex 仍是 RAG 工具层，继续提供 OpenAI-compatible LLM、Embedding、Rerank、chunking 和检索相关能力。LangGraph 只位于更上层，用来编排这些工具。

## 2. 新分层架构

```text
┌─────────────────────────────────────────────────────────────┐
│ FastAPI API Layer                                            │
│ POST /api/v1/query / future agent endpoints                  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Agent Orchestration Layer: LangGraph                         │
│ StateGraph / nodes / conditional_edges / Send / checkpoint   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ RAG Tool Layer: LlamaIndex + project services                │
│ get_llm / get_embedding / get_reranker / retrieval / chunks  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ Infrastructure                                                │
│ Qdrant / PostgreSQL / MinIO / infinity / Bailian or Ollama    │
└─────────────────────────────────────────────────────────────┘
```

桥接方式很简单：LangGraph 节点是普通 Python 函数，可以调用 `app.services.llm.get_llm()`、`get_embedding()`、`get_reranker()` 和后续服务层函数。节点不直接接触 provider SDK。

## 3. 对比 LlamaIndex Workflows

| 维度 | LlamaIndex Workflows | LangGraph |
|------|----------------------|-----------|
| 定位 | RAG 工作流与事件流 | Agent 状态图与控制流 |
| Router | 需要手写事件和分发 | `add_conditional_edges` 直接表达 |
| 多步对比 | 事件链可做但不够显式 | 节点和边清晰表达阶段 |
| 并发抽取 | 需要额外组织事件 | `Send` API 适合 fan-out / fan-in |
| FreeQA ReAct | 需要自行组装 | `create_react_agent` 成熟可用 |
| 状态持久化 | 可实现但不是核心卖点 | checkpoint 是内置能力 |
| 调试生态 | 偏 RAG 调试 | LangSmith / graph 可视化生态成熟 |

结论：LlamaIndex 继续留在工具层；Agent 编排统一改为 LangGraph。

## 4. 6 个 Agent 的新实现思路

### Router

使用 `StateGraph` 承载用户问题、意图分类结果和路由目标。分类节点调用 `get_llm()` 或本地规则，随后通过 `add_conditional_edges` 分发到 BaseQA、Comparison、ServicePath、FreeQA 或 NetworkAgent。

### BaseQA

使用线性 `StateGraph`：解析问题 → 检索 chunks → rerank → 生成答案 → 格式化来源。该 Agent 可以复用 #20 的 RAG Pipeline，不需要重写底层检索。

### Comparison

使用 4 节点状态图：识别对比对象 → 分别检索证据 → 抽取结构化字段 → 汇总对比。状态中保留对象列表、字段结果、证据引用和最终报告。

### ServicePath

使用 `StateGraph` + `Send` API 做 fan-out。对每个客户、产品或服务事件并发抽取节点信息，再 fan-in 到汇总节点生成服务路径图。

### FreeQA

使用 `create_react_agent(llm, tools)`，工具列表接入检索、文档查看、客户信息查询等能力。需要注意：工具内部仍调用项目服务层，不直接 import provider SDK。

### NetworkAgent

使用简单 `StateGraph` 组织实体抽取、关系抽取、图谱合并和回答生成。后续如果引入 Neo4j 或前端图谱组件，也只影响工具层和展示层。

## 5. 集成约束

- LangGraph 节点禁止直接 import `openai` / `dashscope`。
- 所有 LLM 调用走 `get_llm()`，Embedding 走 `get_embedding()`，Rerank 走 `get_reranker()`。
- 业务代码不留 LlamaIndex Workflows 残留，除非后续 spec 明确说明强理由。
- LangGraph 只作为编排层，不替代 Qdrant、PostgreSQL、MinIO 或 LlamaIndex RAG 工具。
- Agent state 必须用 `TypedDict` 或 Pydantic schema 描述，避免无结构 `dict` 在多节点间漂移。
- 需要持久状态时优先用 `langgraph-checkpoint-sqlite`，生产化前再评估 PostgreSQL checkpoint。

## 6. 后续 Phase 3-4 Agent spec 模板调整

后续 Agent spec 应新增一个“LangGraph 图设计”章节，至少包含：

```text
## LangGraph 图设计

State:
- query: str
- intent: str
- retrieved_nodes: list[...]
- answer: str

Nodes:
1. classify_intent
2. retrieve_context
3. rerank_context
4. generate_answer

Edges:
START -> classify_intent
classify_intent -- conditional_edges --> target agent
target agent -> END

Tools:
- get_llm()
- get_embedding()
- get_reranker()
- qdrant retrieval service
```

每个新 Agent 的验收应包含：

- 最小图可以 compile。
- 至少一个无外部 API Key 的单元测试。
- 如果调用真实 LLM / Embedding，需要标记 `@pytest.mark.integration`。
- 业务代码不得直接 import provider SDK。
- Handoff §7 写清下一轮可复用的节点、state 和工具接口。

---

_v2.2 | 最后更新：2026-06-04 | 任务：#65_
