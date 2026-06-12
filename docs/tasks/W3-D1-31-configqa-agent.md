# 任务 #31：ConfigQA Agent（lean MVP 核心问答）

> **版本**：v1.0
> **创建日期**：2026-06-12
> **预估工时**：2 工作日
> **前置任务**：#25 抽取 + #26 批量 + #28 入库 + #30 实际跑批（199 份已在 Qdrant）
> **后续任务**：#32 OpenWebUI 套壳对接（W4 UI MVP）
> **优先级**：🔴 高（W3 核心，lean MVP 的产品交付物）

---

## §1 任务背景

199 份 IP-Guard 产品资料入库后，需要 Agent 接收实施 / 售后的自然语言问题，返回带引用的答案。

跟早期 spec 计划的 BaseQA（任务清单 #20 那一份）的差异：
- ✅ 引用 + 置信度 + 拒答（新加）
- ✅ Bad Case 反馈回流（feedback 表）
- ✅ 流式响应（前端体验 + OpenWebUI 套壳兼容）
- ❌ 不做 Router 分发（lean MVP 只有 ConfigQA 一个 Agent）
- ❌ 不做 ACL filter 注入（customer 表留空 + 所有用户看全部 199 份）
- ❌ 不做对话上下文（单轮问答足够，多轮上下文 Phase 2 加）

---

## §2 范围

- ✅ `backend/app/agents/configqa.py`（LangGraph StateGraph 实现）
- ✅ `backend/app/api/qa.py`（`POST /api/v1/internal/qa` endpoint，流式 SSE）
- ✅ 检索路径：query → embed → Qdrant top-K → rerank → top-N → LLM
- ✅ Prompt: `prompts/configqa_answer.txt`（含引用要求 + 拒答规则）
- ✅ Pydantic：`QARequest` / `QAResponse` / `Citation`
- ✅ feedback 表 + endpoint
- ✅ 测试 ≥ 12 项

- ❌ 不做 Router（lean MVP 单 Agent）
- ❌ 不做对话历史（无 conversation 表）
- ❌ 不做 ACL filter（customer 表空）
- ❌ 不做外部用户路径（lean MVP 内部 only，#68 推迟）

---

## §3 任务目标

1. `ConfigQA` Agent 用 LangGraph `StateGraph` 实现 4 节点 pipeline：
   - `retrieve` → Qdrant top-K（K=settings.top_k 默认 30）
   - `rerank` → 百炼 gte-rerank-v2 → top-N（N=settings.rerank_n 默认 5）
   - `decide` → 最高分 < settings.min_score（默认 0.5）→ 走 refuse 分支
   - `answer` → LLM 生成带 `[1] [2]` 引用的答案；refuse 分支返回固定拒答文本
2. `POST /api/v1/internal/qa` SSE 流式返回 `data: {chunk}\n\n`
3. 响应包含：`answer` / `citations[]`（doc_id / title / page / score）/ `latency_ms` / `model`
4. 挂 `internal_router`（原则 P3）
5. `_require_internal(user)` 二次校验（铁律 #10 layer 2，复用 #69 模式）
6. `POST /api/v1/internal/qa/feedback` 接收 👍/👎 + 文字 → 写 `feedback` 表
7. 测试覆盖 ≥ 12 项

---

## §4 文件清单

### 4.1 `backend/prompts/configqa_answer.txt`（jinja2）

```jinja2
你是 IP-Guard 产品支持助手。基于以下检索到的文档片段回答用户问题。

## 回答要求
1. 答案必须基于检索内容，禁止臆测。关键步骤、版本号、路径必须来自原文。
2. 每个结论后必须标 [N] 引用编号，对应"检索文档"列表的序号。
3. 如检索内容不足以回答（无相关或矛盾），直接说"该问题暂未收录到产品资料中，请联系工单系统"。
4. 答案用 markdown 格式，配置类问题尽量用步骤列表。

## 检索文档
{% for c in citations %}
[{{ loop.index }}] 来源：{{ c.title }}（p.{{ c.page }}）
内容：{{ c.text }}
{% endfor %}

## 用户问题
{{ query }}

## 回答
```

### 4.2 `backend/prompts/configqa_refuse.txt`（拒答文本）

```text
该问题暂未在 IP-Guard 产品资料中找到相关内容（检索置信度 {{ max_score }}，低于阈值 {{ threshold }}）。

建议：
- 换个问法（更具体的模块 / 版本 / 平台）
- 检查工单系统是否有历史记录
- 直接提工单给产品 / 售后团队
```

### 4.3 `backend/app/agents/configqa.py`（LangGraph 实现）

```python
from typing import TypedDict
from langgraph.graph import StateGraph, END

class QAState(TypedDict):
    query: str
    user_id: str
    candidates: list[Chunk]      # top-K 检索结果
    citations: list[Citation]    # rerank 后 top-N
    answer: str
    refused: bool
    max_score: float

async def _retrieve(state: QAState) -> QAState:
    embed = await get_embedding().aget_text_embedding(state["query"])
    hits = await qdrant.search(
        collection=settings.qdrant_collection,
        query_vector=embed,
        limit=settings.top_k,
    )
    state["candidates"] = [_to_chunk(h) for h in hits]
    return state

async def _rerank(state: QAState) -> QAState:
    if not state["candidates"]:
        state["citations"] = []
        state["max_score"] = 0.0
        return state
    docs = [c.text for c in state["candidates"]]
    scores = await get_reranker().rerank(state["query"], docs, top_n=settings.rerank_n)
    state["citations"] = [
        _to_citation(state["candidates"][s.index], s.score) for s in scores
    ]
    state["max_score"] = max((s.score for s in scores), default=0.0)
    return state

def _decide(state: QAState) -> str:
    return "refuse" if state["max_score"] < settings.min_score else "answer"

async def _answer(state: QAState) -> QAState:
    prompt = _render_prompt("configqa_answer.txt", query=state["query"], citations=state["citations"])
    state["answer"] = await get_llm().acomplete(prompt)
    return state

async def _refuse(state: QAState) -> QAState:
    state["refused"] = True
    state["answer"] = _render_prompt(
        "configqa_refuse.txt", max_score=state["max_score"], threshold=settings.min_score
    )
    return state


def build_configqa_graph():
    g = StateGraph(QAState)
    g.add_node("retrieve", _retrieve)
    g.add_node("rerank", _rerank)
    g.add_node("answer", _answer)
    g.add_node("refuse", _refuse)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "rerank")
    g.add_conditional_edges("rerank", _decide, {"answer": "answer", "refuse": "refuse"})
    g.add_edge("answer", END)
    g.add_edge("refuse", END)
    return g.compile()
```

### 4.4 `backend/app/models/qa.py`（Pydantic）

```python
from pydantic import BaseModel, Field

class Citation(BaseModel):
    n: int                        # 引用编号 [1] [2]
    doc_id: str
    title: str
    page: int | None = None
    score: float
    excerpt: str = ""             # 前 200 字片段，UI 展示用

class QARequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    stream: bool = True

class QAResponse(BaseModel):
    answer: str
    citations: list[Citation]
    refused: bool = False
    max_score: float
    latency_ms: int
    model: str
    trace_id: str | None = None

class FeedbackRequest(BaseModel):
    query: str
    answer: str
    rating: int = Field(ge=-1, le=1)   # -1 没解决 / 0 中性 / +1 有用
    comment: str | None = None
```

### 4.5 `backend/app/api/qa.py`（endpoint）

```python
internal_router = APIRouter(prefix="/qa", tags=["qa"])

@internal_router.post("")
async def query(
    payload: QARequest,
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    _require_internal(user)
    graph = build_configqa_graph()

    async def _stream():
        # LangGraph astream 增量返回 state 变化；汇总成 SSE
        start = time.monotonic()
        state = {"query": payload.query, "user_id": user.user_id, ...}
        async for chunk in graph.astream(state):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        elapsed = int((time.monotonic() - start) * 1000)
        yield f"data: {json.dumps({'event': 'done', 'latency_ms': elapsed})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@internal_router.post("/feedback", status_code=201)
async def feedback(
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    _require_internal(user)
    await feedback_repo.create(session, user_id=user.user_id, **payload.model_dump())
    return {"status": "recorded"}
```

### 4.6 `backend/app/db/models/feedback.py`（新建）

```python
class Feedback(Base):
    __tablename__ = "feedback"
    id: int (pk)
    user_id: str (索引)
    query: Text
    answer: Text
    rating: int        # -1 / 0 / +1
    comment: Text | None
    created_at: datetime
```

### 4.7 `backend/migrations/versions/0004_feedback.py`

按 #67 模式手写。

### 4.8 `backend/tests/agents/test_configqa.py`（≥ 8 项）

mock get_embedding / qdrant.search / get_reranker / get_llm：

- `test_retrieve_returns_top_k_candidates`
- `test_rerank_sorts_and_truncates_to_top_n`
- `test_decide_routes_to_refuse_when_max_score_below_threshold`
- `test_decide_routes_to_answer_when_max_score_above_threshold`
- `test_answer_includes_citation_markers`
- `test_refuse_returns_canned_text`
- `test_empty_candidates_routes_to_refuse`
- `test_full_pipeline_end_to_end_mock`

### 4.9 `backend/tests/api/test_qa.py`（≥ 4 项）

- `test_qa_endpoint_streams_sse`
- `test_external_user_qa_returns_403`
- `test_feedback_persists_to_db`
- `test_feedback_validates_rating_range`

### 4.10 `backend/app/core/config.py`（确认已有）

`top_k=30` / `rerank_n=5` / `min_score=0.5` 在 #19 时已加，无需新增。

---

## §5 验收

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'
& uv run pytest tests/agents/test_configqa.py tests/api/test_qa.py -v   # ≥ 12 passed
& uv run pytest -m "not integration" --cov=app                          # 回归不降
& uv run alembic upgrade head                                           # 0004 应用
& uv run ruff check . ; & uv run mypy app

# 端到端（需 199 份已入库）
curl -X POST http://localhost:8000/api/v1/internal/qa \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <local_token>" \
  -d '{"query": "自动加解密文件夹支持多目录怎么配置"}'
# 应流式返回答案 + 引用
```

---

## §6 风险

| 风险 | 缓解 |
|------|------|
| LangGraph astream 在百炼 OpenAI 兼容下流式细节 | 实施时如有差异，降级为非流式 + chunk 模拟（UI 体验下降但功能在）|
| min_score=0.5 阈值过严 / 过松 | W3 末用真实 Bad Case 调；初始 0.5 是经验值 |
| rerank 调用增加 200-500ms 延迟 | 端到端 < 3s 是可接受目标 |
| LLM 不按 [N] 格式输出引用 | prompt 加 few-shot 示例；测试时 regex 验 |
| feedback 表无限增长 | Phase 2 加定期归档；MVP 不限 |

### 新增依赖

无（LangGraph / LlamaIndex / SQLAlchemy 都已装）

---

## §7 禁止事项

- ❌ 在 `configqa.py` 直接 `import dashscope` / `from openai`（铁律 #1）
- ❌ 用 LlamaIndex Workflows（铁律 #8，Agent 编排走 LangGraph）
- ❌ 把 `/qa` 挂到 public_router / 顶层 api_router（违反原则 P3）
- ❌ external user 能 reach `/qa`（铁律 #10 layer 2 二次校验）
- ❌ `PermissionDeniedError` 错误信息回显工具名 / query（PR #15 N1）
- ❌ `_require_internal` 不调用就让 user 进 graph（layer 2 必须）
- ❌ feedback 表存明文 query 不脱敏（lean MVP 内部用 OK；外部上线前必须改）
- ❌ Prompt 写在 Python 字符串里超过 3 行（铁律 #5）

---

## §8 参考

- `CLAUDE.md` v1.2 § 铁律 #1 #5 #8 #10
- `docs/tasks/W1-D4-20-min-rag-pipeline.md`（基础 RAG pipeline 参考）
- `docs/tasks/W2-D3-69-crm-abstraction.md`（_check_internal 模式参考）
- `docs/reviews/PR-15.md` § N1（错误信息脱敏）
- LangGraph 文档：https://langchain-ai.github.io/langgraph/

---

_v1.0 | 2026-06-12 | lean MVP W3 核心 Agent_

