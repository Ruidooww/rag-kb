# Task #20: 最小 RAG Pipeline 跑通

> **Phase**: 1 | **Week**: 1 | **Day**: 4
> **预估工时**: 5-7 小时
> **优先级**: 🟡 重要（第一个端到端跑通 RAG 的任务，里程碑）
> **前置任务**: #15、#16、#17、#18、#19（特别依赖 #19 的 LLM 抽象层）
> **本任务首次按 v2.1 自审查机制执行**——必须按 TASK_PROMPT_TEMPLATE.md 走 10 步

---

## 1. 任务背景

完成 #18 (FastAPI 骨架) + #19 (LlamaIndex 抽象) 后，本任务把它们串起来跑通**端到端最小 RAG**：

```
5 份测试文档 → ingest 脚本 → 切片 → bge-m3 向量化 → Qdrant 存储
                                                        ↓
用户 POST /api/v1/query → 召回 Top-30 → Rerank → LLM 生成答案（带引用）
```

**关键设计原则**：
- **真正"最小"**：不做文件上传 API、不做 Agent 框架、不做 PDF/图片解析（这些在 Phase 2+ 做）
- **5 份测试文档全部是 markdown/txt**（PDF/PPT 留到 #28 双轨入库）
- **API Key 占位时 integration 测试 skip**（与 #19 一致）
- **Pipeline 是"代码骨架"，不是 production-ready**（Phase 2 会重构）

---

## 2. 前置依赖（执行前必须确认）

| # | 验证方法 | 期望 |
|---|---------|------|
| Python 3.13/3.14 + uv 已安装 | `uv --version` | 返回版本号 |
| FastAPI 骨架在 main | `ls backend/app/main.py` | 存在 |
| LlamaIndex 抽象在 main | `ls backend/app/services/llm.py` | 存在 |
| Docker 4 个服务 healthy | `docker compose ps` | 全部 healthy |
| infinity Embedding 服务可达 | `curl http://localhost:8080/health` | 返回 200 |
| Qdrant 可达 | `curl http://localhost:6333/healthz` | 返回 OK |
| v2.1 自审查机制已激活 | `ls docs/SELF_REVIEW.md` | 存在 |

---

## 3. 任务目标

实现端到端 RAG 流程，证明：
1. 文档能被 chunk + 向量化 + 存进 Qdrant
2. 用户 query 能召回相关 chunk
3. Rerank 能重排提升精度
4. LLM 能基于召回内容生成答案 + 引用来源

完成后，业务方可以：
```bash
# 入库 5 份测试文档
uv run python scripts/ingest_test_docs.py

# 起服务
uv run uvicorn app.main:app --reload

# 提问
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "产品 X 怎么安装？"}'

# 期望响应：
# {
#   "answer": "根据产品 X 手册...",
#   "sources": [
#     {"doc_id": "...", "text": "...", "score": 0.92}
#   ],
#   "latency_ms": 3500
# }
```

---

## 4. 输出文件清单（详细要求）

### 4.1 `backend/tests/fixtures/sample_docs/`（5 份测试文档）

新建目录，提交以下 5 份 markdown 文件（提交到 git 用于复现）：

#### `product_x_manual.md`
产品 X 用户手册片段：包含产品介绍、安装步骤（3 步）、常见故障排查（3 个）。
长度：~500 字。

#### `faq_general.md`
通用 FAQ：包含至少 5 个问答对，覆盖账号、付款、退款、技术支持、隐私。
长度：~600 字。

#### `customer_case_acme.md`
客户案例：ACME 公司使用本产品的背景、实施过程、成果数据。
长度：~400 字。

#### `team_handbook.md`
团队手册节选：包含远程工作规范、代码 review 流程、迭代周期。
长度：~500 字。

#### `release_notes_v2.md`
v2.0 发布说明：新特性 5 个、修复 3 个、已知问题 2 个。
长度：~400 字。

**内容要求**：必须是真实可信的中文文档（不要纯占位 lorem ipsum），便于评估问答质量。
**禁止**：不要包含真实公司名、真实客户名、真实金额（避免被敏感词扫描误报）。

### 4.2 `backend/app/models/query.py`

定义 query 相关 Pydantic schemas：

```python
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=50)
    rerank_n: int | None = Field(default=None, ge=1, le=20)


class SourceChunk(BaseModel):
    doc_id: str
    chunk_id: str
    text: str
    score: float
    metadata: dict[str, str | int | float] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    latency_ms: int
    model_used: str
```

### 4.3 `backend/app/services/qdrant_store.py`

Qdrant 封装：

**导出**：
- `get_qdrant_client() -> QdrantClient` — 工厂函数
- `ensure_collection(collection: str, vector_size: int = 1024)` — 幂等创建 collection
- `upsert_chunks(collection, chunks: list[ChunkPayload])` — 批量入库
- `search_chunks(collection, query_vector, top_k, filter)` — 向量检索

**要求**：
- 用 `qdrant-client` Python SDK
- collection 名走 settings（新增 `qdrant_collection: str = "rag_chunks"`）
- HNSW 默认参数即可（不用调优）
- 错误抛 `AppException` 子类 `VectorStoreError`（在 exceptions.py 新增）

### 4.4 `backend/app/services/rag_pipeline.py`

端到端 RAG 函数（**这是本任务的核心**）：

**导出 3 个函数**：

```python
async def ingest_file(file_path: Path, collection: str = "rag_chunks") -> int:
    """读文件 → 切片 → 向量化 → 入库。返回入库的 chunk 数。

    支持的格式：.md, .txt（PDF 在 Phase 2 处理）
    """

async def retrieve(query: str, top_k: int, rerank_n: int) -> list[SourceChunk]:
    """Embedding → Qdrant 检索 → Rerank → 返回 Top-rerank_n。"""

async def generate_answer(query: str, sources: list[SourceChunk]) -> str:
    """根据召回的 sources + query，让 Omni 生成答案。

    必须用 prompts/base_qa.txt 模板，禁止 inline prompt > 3 行。
    """
```

**实现要点**：
- 切片用 LlamaIndex 的 `SentenceSplitter`，`chunk_size=settings.chunk_size`、`chunk_overlap=settings.chunk_overlap`
- chunk metadata 至少含：`doc_id`（文件名 stem）、`file_path`、`chunk_index`
- 调用模型走 `get_llm/get_embedding/get_reranker`（铁律 #1）
- generate_answer 实现引用要求：让 LLM 输出含 `[来源: doc_id]` 标记的答案

### 4.5 `backend/app/prompts/base_qa.txt`

基础问答 prompt 模板，用 `str.format()` 注入变量：

```
你是一个基于公司内部知识库回答问题的助手。

请根据下面提供的"参考资料"回答用户问题。

要求：
1. 答案必须严格基于参考资料，禁止编造
2. 如果参考资料不足以回答，明确回复"暂未收录此问题"
3. 答案中引用具体来源时，标记为 [来源: 文档名]
4. 答案语言简洁，2-5 句话为宜

参考资料：
{sources}

用户问题：
{query}

请给出答案：
```

**变量替换约定**：
- `{sources}` = 多个 chunk 拼接，每个含 `--- 文档: {doc_id} ---\n{text}\n`
- `{query}` = 用户原始 query

### 4.6 `backend/app/api/query.py`

POST /query 端点：

```python
from fastapi import APIRouter
from app.models.query import QueryRequest, QueryResponse

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """基础 RAG 问答。"""
    # 1. 调 retrieve()
    # 2. 调 generate_answer()
    # 3. 记录 latency
    # 4. 返回带引用的答案
    ...
```

并在 `backend/app/api/router.py` 注册：
```python
from app.api import health, query
api_router.include_router(health.router)
api_router.include_router(query.router)
```

### 4.7 `backend/app/core/exceptions.py`（追加）

新增异常类：
```python
class VectorStoreError(AppException):
    error_code = "VECTOR_STORE_ERROR"
    status_code = 502
```

### 4.8 `backend/app/core/config.py`（追加）

新增字段：
```python
qdrant_collection: str = "rag_chunks"
```

### 4.9 `backend/scripts/ingest_test_docs.py`

CLI 脚本：扫 `backend/tests/fixtures/sample_docs/` 下所有文件，调 `ingest_file()` 入库。

```python
"""入库 5 份测试文档。

用法：
    cd backend
    uv run python scripts/ingest_test_docs.py
"""
import asyncio
from pathlib import Path

from app.services.rag_pipeline import ingest_file


async def main() -> None:
    fixtures_dir = Path(__file__).parents[1] / "tests" / "fixtures" / "sample_docs"
    total_chunks = 0
    for file in sorted(fixtures_dir.glob("*.md")):
        chunks = await ingest_file(file)
        print(f"  入库 {file.name}: {chunks} chunks")  # noqa: T201（脚本允许 print）
        total_chunks += chunks
    print(f"\n总计：{total_chunks} chunks")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
```

**注意**：script 允许 `print`，但要加 `# noqa: T201` 标记。

### 4.10 测试文件（4 个）

- `backend/tests/services/test_qdrant_store.py` — Qdrant 操作（需 Qdrant 服务，标 integration）
- `backend/tests/services/test_rag_pipeline.py` — Pipeline 三个函数单测（mock + integration 两类）
- `backend/tests/api/test_query.py` — /query 端点（integration）
- `backend/tests/agents/__init__.py` — 创建空文件（虽然本任务无 agent，但 v2.1 SELF_REVIEW 要求结构完整）

### 4.11 `backend/pyproject.toml` 追加依赖

```bash
uv add qdrant-client llama-index-core llama-index-vector-stores-qdrant
```

---

## 5. 配置参考

### 5.1 Qdrant collection 创建

Codex 初次跑 ingest_test_docs.py 时，`ensure_collection` 会幂等创建 `rag_chunks` collection：
- vector_size: 1024（bge-m3）
- distance: COSINE
- 如已存在则不重建

### 5.2 chunk_size / chunk_overlap

来自 settings（config.yaml 默认）：
- chunk_size: 800
- chunk_overlap: 100

本任务不做调优，沿用默认即可。Phase 1 Week 3 (#34) 会做网格搜索调优。

### 5.3 top_k / rerank_n

来自 settings（config.yaml 默认）：
- top_k: 30
- rerank_n: 5

QueryRequest 允许调用方覆盖，但 query.py endpoint 默认从 settings 读。

### 5.4 Prompt 文件加载

`generate_answer` 实现要点：

```python
from pathlib import Path
PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "base_qa.txt"

async def generate_answer(query, sources):
    template = PROMPT_PATH.read_text(encoding="utf-8")
    sources_block = "\n".join(
        f"--- 文档: {s.doc_id} ---\n{s.text}\n" for s in sources
    )
    prompt = template.format(sources=sources_block, query=query)
    llm = get_llm()
    response = llm.complete(prompt)
    return response.text
```

不要把 prompt 缓存到内存（每次读文件，方便热更新）。

---

## 6. 测试规范

### 6.1 test_qdrant_store.py（约 4 个 case）

- `test_ensure_collection_idempotent` — 调两次不报错 (integration)
- `test_upsert_and_search` — 写入 3 个 chunk，搜索能召回相关的 (integration)
- `test_search_with_filter` — metadata filter 生效 (integration)
- `test_vector_store_error_on_invalid_url` — 错误处理（无 integration，用错误 URL）

全部标 `@pytest.mark.integration` 除最后一个。

### 6.2 test_rag_pipeline.py（约 5 个 case）

- `test_ingest_file_creates_chunks` — 入库单文件，断言 chunk 数 > 0 (integration)
- `test_retrieve_returns_top_n` — 入库后 retrieve，断言数量 ≤ rerank_n (integration)
- `test_generate_answer_uses_prompt_template` — verify prompt 文件被读取
- `test_generate_answer_skipped_without_real_key` — `@requires_real_llm_key`
- `test_ingest_unsupported_format_raises` — `.pdf` 文件应抛 ValidationError（本任务不支持）

### 6.3 test_query.py（约 3 个 case）

- `test_query_endpoint_basic` — POST /api/v1/query，断言返回结构（integration）
- `test_query_endpoint_validation` — 空 query 应返回 422
- `test_query_endpoint_includes_latency` — 响应含 latency_ms

### 6.4 测试运行命令

```bash
# CI 跑（仅 unit）
uv run pytest -v -m "not integration"

# 本地全跑
uv run pytest -v

# 单文件
uv run pytest tests/services/test_rag_pipeline.py -v
```

---

## 7. 验收标准（Definition of Done）

### 7.1 功能正确性
- [ ] `uv run python scripts/ingest_test_docs.py` 成功跑完
- [ ] 5 份测试文档全部入库，总 chunk 数 > 5（每份至少切出 1 个 chunk）
- [ ] `curl -X POST http://localhost:8000/api/v1/query -d '{"query": "产品X怎么安装"}'` 返回有效 JSON
- [ ] 响应含 `answer`（非空）、`sources`（数组非空）、`latency_ms`（整数）

### 7.2 测试通过
- [ ] `uv run pytest -v -m "not integration"` 全绿
- [ ] integration 测试本地能跑通（Qdrant + infinity 都起来时）
- [ ] 覆盖率 ≥ 70%

### 7.3 静态检查
- [ ] ruff check 0 errors
- [ ] ruff format --check 无变更
- [ ] mypy strict 0 errors

### 7.4 七条铁律（grep 自检全空）
- [ ] `grep -r "import dashscope" backend/app/`
- [ ] `grep -r "print(" backend/app/`（scripts/ 除外，但要加 noqa）
- [ ] `grep -rE "import logging$" backend/app/`
- [ ] `grep -rE "from openai|import openai" backend/app/ | grep -v "services/llm.py"`
- [ ] `grep -rE "https://dashscope|qwen[0-9]|gte-rerank" backend/app/`

### 7.5 端到端验证（手动跑一次）
- [ ] Qdrant 控制台 http://localhost:6333/dashboard 能看到 `rag_chunks` collection
- [ ] 入库后 collection 有 > 5 个 vectors
- [ ] /api/v1/query 返回的 sources 中至少 1 个 score > 0.5

### 7.6 v2.1 自审查（CI + Handoff）
- [ ] CI workflow 通过（self-review check = pass）
- [ ] Handoff §0-§8 完整
- [ ] Handoff §8 自审报告含 last_verified_commit
- [ ] ANTIPATTERNS.md 对照检查（如发现新反模式追加）

### 7.7 Git
- [ ] 在分支 `feat/W1-D4-20-min-rag-pipeline`
- [ ] commit 含 `Refs: #20`
- [ ] PR 标题含 `#20` 便于 CI Handoff 检查通过

---

## 8. 禁止事项

- ❌ 不要实现文件上传 API（POST /documents/upload 留到 #29）
- ❌ 不要实现 Agent 框架 / Router / Workflow（Phase 4 做）
- ❌ 不要解析 PDF / 图片 / PPT（#28 双轨入库做）
- ❌ 不要做权限校验（#42 客户级 ACL 做）
- ❌ 不要做用户认证（后续任务）
- ❌ 不要做 streaming 响应（性能优化任务做）
- ❌ 不要给 retrieve 加 cache（YAGNI，未来优化）
- ❌ 不要 inline 长 prompt（必须走 prompts/ 目录）
- ❌ 不要硬编码 collection 名（走 settings.qdrant_collection）
- ❌ scripts/ 之外不能有 print()
- ❌ 不要为了通过测试用 mock LLM 假装 generate 成功（缺 key 就 skip 整测）

---

## 9. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| `ingest_file` 用 sync IO 读大文件 | 阻塞事件循环 | 用 `aiofiles` 或在 `to_thread.run_sync` 中读 |
| Qdrant collection 不存在直接 upsert | 报错 | 先 `ensure_collection` 幂等创建 |
| chunk_id 用 UUID 但忘了存 doc_id | 召回后无法标引用 | metadata 必须含 doc_id |
| Prompt 模板硬编码在 .py | 违反铁律 #5 | 放 prompts/ 目录 |
| `generate_answer` 不检查 sources 为空 | LLM 编造答案 | 空 sources 直接返回"暂未收录" |
| Qdrant 客户端做 lru_cache | 测试间不隔离 | 工厂函数每次新建 |
| `await` 漏写导致返回 coroutine | API 响应是奇怪对象 | mypy strict 会捕获，跑！ |
| Rerank 失败时 retrieve 直接挂 | 用户体验差 | 已在 BailianRerank 内重试 3 次后抛，调用方再处理 |
| 测试入库不清理 collection | 测试间污染 | conftest 加 fixture 在 setup/teardown 清理 |
| Qdrant collection 名硬编码 | 改名要全局搜 | 走 settings.qdrant_collection |

---

## 10. 参考资料

### 官方文档
- [LlamaIndex SentenceSplitter](https://docs.llamaindex.ai/en/stable/api_reference/node_parsers/sentence_splitter/)
- [LlamaIndex QdrantVectorStore](https://docs.llamaindex.ai/en/stable/api_reference/storage/vector_store/qdrant/)
- [qdrant-client Python](https://github.com/qdrant/qdrant-client)
- [Qdrant REST API](https://qdrant.tech/documentation/concepts/collections/)

### 项目内文档
- `CLAUDE.md` — 七条铁律 + v2.1 + CodeGraph
- `docs/SELF_REVIEW.md` — Part A-E 自审查规程
- `docs/TASK_PROMPT_TEMPLATE.md` — 10 步标准流程
- `docs/ANTIPATTERNS.md` — 必查（A1 httpx 复用、C1 os.getenv 等）
- `docs/HANDOFF_TEMPLATE.md` — §0-§8 模板
- `docs/handoffs/W1-D3-19-handoff.md` — #19 给本任务的 §7 提示
- `docs/tasks/W1-D3-19-llamaindex-abstract.md` — LLM 抽象层 spec

### CodeGraph 用法（首次执行任务时建议用）
- `codegraph_search "ingest"` — 看是否已有 ingest 相关代码
- `codegraph_explore "rag_pipeline"` — 看现有架构
- `codegraph_callers "get_llm"` — 确认 LLM 调用都走抽象层

---

## 11. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 CLAUDE.md + SELF_REVIEW + 本 spec | 30 分钟 |
| 创建 5 份测试 markdown 文档 | 45 分钟 |
| 实现 query.py models | 15 分钟 |
| 实现 qdrant_store.py + tests | 60 分钟 |
| 实现 rag_pipeline.py 三函数 + tests | 90 分钟 |
| 实现 base_qa.txt prompt | 15 分钟 |
| 实现 query.py endpoint + tests | 45 分钟 |
| scripts/ingest_test_docs.py | 15 分钟 |
| 本地端到端验证（手动跑 ingest + query） | 30 分钟 |
| Self-Review Part A-E + Handoff | 60 分钟 |
| 修复反馈 / commit / push / PR | 30 分钟 |
| **合计** | **~7 小时** |

超 8 小时未完成需停下沟通，可能 spec 有问题或环境有故障。

---

## 12. 与下一轮的衔接

#20 完成后，#21 (W1-D5 环境变量切换演示) 会：
- 把 .env 的 LLM_BASE_URL 切到本地 Ollama
- 跑同样的 ingest + query，验证业务代码零改动
- 写 docs/migration-test.md 记录切换步骤

所以 #20 的 Handoff §7（给下一轮提示）应该说清楚：
- ingest/query 入口在哪
- 验证切换的最小步骤
- 哪些环境变量需要在 Ollama 下重置

---

_v1.0 | 任务 ID：#20 | 最后更新：2026-06-04_
