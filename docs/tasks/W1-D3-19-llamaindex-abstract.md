# Task #19: LlamaIndex 抽象层封装

> **Phase**: 1 | **Week**: 1 | **Day**: 3
> **预估工时**: 4-6 小时
> **优先级**: 🔒 关键（七条铁律的根基）
> **前置任务**: #13、#14、#15、#16、#17、#18

---

## 1. 任务背景

七条铁律的第 1 条规定：**所有 LLM / Embedding / Rerank 调用必须走统一抽象层**。

本任务实现这个抽象层（`backend/app/services/llm.py`），是后续所有 Agent、RAG Pipeline、入库流程的基础。做错这一步，未来切换到本地 Ollama 就要改一堆业务代码——违反整个项目的核心架构原则。

**关键决策**：
- LLM 用 LlamaIndex 的 `OpenAILike`，连百炼的 `compatible-mode/v1` 端点
- Embedding 用 `OpenAIEmbedding`，连本地 `infinity` 服务（OpenAI 兼容）
- Rerank 不在 OpenAI 标准协议内，需要自定义 `BaseNodePostprocessor` 子类

---

## 2. 前置依赖（必须先确认就绪）

| # | 来源 | 验证方法 |
|---|------|---------|
| ✅ Python 3.14 + uv 已安装 | #14 | `uv --version` 返回非空 |
| ✅ FastAPI 项目骨架存在 | #18 | `backend/app/main.py` 存在 |
| ✅ `.env` 文件已填值 | #17 | `cat backend/.env` 含 `LLM_API_KEY=sk-...` |
| ✅ `config.yaml` 已存在 | #17 | `cat backend/config.yaml` 含 `chunk_size` 等 |
| ✅ docker-compose 已起 infinity 服务 | #16 | `curl http://localhost:8080/health` 返回 200 |
| ✅ 百炼 API Key 可用 | #13 | 控制台「API 调用」页面有调用记录 |

如有任一未就绪，先完成对应任务再回来。

---

## 3. 任务目标

实现 3 个工厂函数 + 1 个自定义 Rerank 类 + 1 个 Settings 类，并完成 3 个单元测试。

完成后，业务代码使用方式应该是：

```python
from app.services.llm import get_llm, get_embedding, get_reranker

llm = get_llm()
response = llm.complete("你好")

embedder = get_embedding()
vector = embedder.get_text_embedding("中文文本")

reranker = get_reranker()
ranked_nodes = reranker.postprocess_nodes(nodes, query_str="问题")
```

业务代码**永远不应该直接** import dashscope / openai / httpx 去调模型。

---

## 4. 输出文件清单

### 4.1 `backend/app/core/config.py`

**职责**：统一加载 `.env` + `config.yaml`，暴露 `settings` 单例。

**要求**：
- 用 `pydantic-settings` 的 `BaseSettings`
- `.env` 字段（必填，无默认值，缺失即报错）：
  - `LLM_BASE_URL: str`
  - `LLM_MODEL: str`
  - `LLM_API_KEY: SecretStr`
  - `RERANK_BASE_URL: str`
  - `RERANK_MODEL: str`
  - `EMBED_BASE_URL: str`
  - `EMBED_MODEL: str`
- `config.yaml` 字段（有默认值）：
  - `chunk_size: int = 800`
  - `chunk_overlap: int = 100`
  - `top_k: int = 30`
  - `rerank_n: int = 5`
  - `temperature: float = 0.3`
  - `max_tokens: int = 2000`
  - `llm_timeout: int = 60`
  - `llm_max_retries: int = 2`
- 用 `lru_cache` 装饰的 `get_settings()` 函数返回单例
- 模块级 `settings = get_settings()` 提供便捷访问

**关键约束**：
- 任何字段缺失必须抛 `pydantic.ValidationError`（fail-fast）
- 不允许任何字段有"看起来合理的默认值但实际依赖部署环境"（如 base_url）

### 4.2 `backend/app/services/llm.py`

**职责**：封装 LLM / Embedding / Rerank，对外只暴露 3 个工厂函数。

**导出符号**（`__all__`）：
```python
__all__ = ["get_llm", "get_embedding", "get_reranker", "BailianRerank"]
```

#### 4.2.1 `get_llm() -> BaseLLM`

```python
from llama_index.llms.openai_like import OpenAILike

def get_llm() -> OpenAILike:
    """返回配置好的 LlamaIndex LLM 客户端。

    使用百炼 OpenAI 兼容模式。所有参数从 settings 读取。
    禁止在调用方传参覆盖，否则破坏「配置统一」原则。
    """
    return OpenAILike(
        model=settings.llm_model,
        api_base=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
        is_chat_model=True,
        context_window=128000,  # qwen3.5-omni-flash 上下文
    )
```

#### 4.2.2 `get_embedding() -> BaseEmbedding`

```python
from llama_index.embeddings.openai_like import OpenAILikeEmbedding

def get_embedding() -> OpenAILikeEmbedding:
    """返回 bge-m3 Embedding 客户端（本地 infinity 服务）。

    维度固定 1024，不允许通过参数修改。
    """
    return OpenAILikeEmbedding(
        model_name=settings.embed_model,
        api_base=settings.embed_base_url,
        api_key="not-needed",  # infinity 本地服务不验证 key
        embed_batch_size=32,
    )
```

#### 4.2.3 `BailianRerank(BaseNodePostprocessor)`

百炼 Rerank API 不是 OpenAI 标准，需要自定义。

**接口**：
```python
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

class BailianRerank(BaseNodePostprocessor):
    """百炼 gte-rerank-v2 包装类。

    实现 LlamaIndex BaseNodePostprocessor 接口，可直接放入
    RetrieverQueryEngine 的 node_postprocessors 列表。
    """

    model: str
    top_n: int
    base_url: str
    api_key: SecretStr

    def _postprocess_nodes(
        self,
        nodes: list[NodeWithScore],
        query_bundle: QueryBundle | None = None,
    ) -> list[NodeWithScore]:
        if not query_bundle or not nodes:
            return nodes
        # 调百炼 rerank API：
        # POST {base_url}/services/rerank/text-rerank/text-rerank
        # body: {"model": ..., "input": {"query": ..., "documents": [...]}, "parameters": {"top_n": ...}}
        # 用 httpx.Client (sync) 调用
        # 返回 top_n 个 NodeWithScore，score 用 rerank 返回的 relevance_score
        ...
```

**实现要点**：
- 用 `httpx.Client`（sync 同步，配合 LlamaIndex 同步接口）
- timeout=30s，retry 2 次
- 返回的 nodes 顺序按 rerank score 降序
- node 的 `.score` 字段更新为 rerank 的 `relevance_score`
- 错误处理：API 失败时**抛异常**（不要静默返回原 nodes，会掩盖问题）

#### 4.2.4 `get_reranker() -> BailianRerank`

```python
def get_reranker() -> BailianRerank:
    return BailianRerank(
        model=settings.rerank_model,
        top_n=settings.rerank_n,
        base_url=settings.rerank_base_url,
        api_key=settings.llm_api_key,  # 百炼 rerank 复用同一个 key
    )
```

### 4.3 `backend/app/core/exceptions.py`

如不存在则创建。本任务需要：

```python
class AppException(Exception):
    """所有自定义异常的基类。"""

class LLMServiceError(AppException):
    """LLM/Embedding/Rerank 调用失败。"""
```

### 4.4 `backend/tests/services/test_llm.py`

参见 §6 测试规范。

### 4.5 `backend/pyproject.toml` 依赖追加

```toml
[project]
dependencies = [
    # ... 已有依赖
    "llama-index-core>=0.10",
    "llama-index-llms-openai-like>=0.2",
    "llama-index-embeddings-openai-like>=0.2",
    "pydantic-settings>=2.0",
    "httpx>=0.27",
    "loguru>=0.7",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "ruff>=0.5",
    "mypy>=1.10",
]
```

用 `uv add ...` 而不是手动改 `pyproject.toml`（uv 会同步 lockfile）。

---

## 5. 配置参考

### 5.1 `.env` 应包含的值（来自任务 #17）

```env
# === LLM (云端百炼) ===
LLM_PROVIDER=bailian
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-omni-flash
LLM_API_KEY=sk-xxxxxxxxxxxxxxxxxx

# === Rerank (云端百炼) ===
RERANK_BASE_URL=https://dashscope.aliyuncs.com/api/v1
RERANK_MODEL=gte-rerank-v2

# === Embedding (本地 infinity) ===
EMBED_BASE_URL=http://localhost:8080/v1
EMBED_MODEL=BAAI/bge-m3
```

### 5.2 `config.yaml` 应包含的值

```yaml
chunk_size: 800
chunk_overlap: 100
top_k: 30
rerank_n: 5
temperature: 0.3
max_tokens: 2000
llm_timeout: 60
llm_max_retries: 2
```

### 5.3 百炼 Rerank API 调用格式

```http
POST https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank
Authorization: Bearer {LLM_API_KEY}
Content-Type: application/json

{
  "model": "gte-rerank-v2",
  "input": {
    "query": "用户问题",
    "documents": ["文档1内容", "文档2内容", "..."]
  },
  "parameters": {
    "return_documents": false,
    "top_n": 5
  }
}
```

响应：
```json
{
  "output": {
    "results": [
      {"index": 2, "relevance_score": 0.95},
      {"index": 0, "relevance_score": 0.82},
      ...
    ]
  },
  "usage": {"total_tokens": 1234}
}
```

---

## 6. 测试规范

### 6.1 文件位置

`backend/tests/services/test_llm.py`

### 6.2 必需的测试用例

#### test_settings_loads_from_env
- 验证 `settings.llm_model` 等字段非空
- 验证缺失字段时抛 ValidationError（用 monkeypatch 删 env var）

#### test_get_llm_completion
- 调 `get_llm().complete("用一句话介绍 RAG")`
- 断言返回 `CompletionResponse`，`response.text` 非空且长度 > 10
- 用真实百炼 API（标记为 `@pytest.mark.integration`，CI 可跳）

#### test_get_embedding_dimension
- 调 `get_embedding().get_text_embedding("测试文本")`
- 断言返回 `list[float]`，长度 == 1024

#### test_get_embedding_batch
- 调 `get_embedding().get_text_embedding_batch(["a", "b", "c"])`
- 断言返回 3 个 1024 维向量

#### test_reranker_reorders_nodes
- 构造 3 个 NodeWithScore（content 分别为"苹果"/"汽车"/"水果香蕉"）
- 用 query "热带水果" 调用 reranker
- 断言返回 nodes 数量 ≤ top_n
- 断言第一个 node 的 content 与 "水果" 相关（"水果香蕉" 或 "苹果"）

#### test_reranker_empty_input
- 传空 nodes 列表
- 断言返回空列表，不抛异常

#### test_reranker_api_failure
- 用 monkeypatch 把 base_url 改成无效地址
- 断言抛 `LLMServiceError`（不是 httpx 原生异常）

### 6.3 测试运行命令

```bash
# 只跑单元测试（mock，快）
uv run pytest backend/tests/services/test_llm.py -m "not integration"

# 跑全部（含真实 API 调用）
uv run pytest backend/tests/services/test_llm.py
```

---

## 7. 验收标准（Definition of Done）

完成本任务必须满足全部以下条件，否则视为未完成：

### 7.1 功能正确性
- [ ] `from app.services.llm import get_llm, get_embedding, get_reranker` 可以导入
- [ ] 三个工厂函数能返回非 None 实例
- [ ] LLM 能完成一次简单 completion
- [ ] Embedding 返回 1024 维向量
- [ ] Reranker 能对至少 3 个 nodes 进行重排

### 7.2 测试通过
- [ ] `uv run pytest backend/tests/services/test_llm.py` 全部绿色
- [ ] 集成测试至少 5 个，覆盖率 ≥ 85%（用 `pytest --cov=app.services.llm`）

### 7.3 静态检查
- [ ] `uv run ruff check backend/app/services/llm.py` 无错误
- [ ] `uv run mypy backend/app/services/llm.py` 无错误
- [ ] `uv run ruff format --check backend/` 已格式化

### 7.4 七条铁律验证 🔒
- [ ] `grep -r "import dashscope" backend/app/` **无任何结果**
- [ ] `grep -rE "from openai import|import openai" backend/app/services/` **仅在 llm.py 内部允许，业务层禁止**
- [ ] `grep -rE "https://dashscope|qwen3\.5|gte-rerank" backend/app/` **仅在 .env 和 config 相关位置出现**
- [ ] 在 llm.py 之外的任何文件 `grep` 上述字符串都应无结果

### 7.5 文档
- [ ] `backend/app/services/llm.py` 模块顶部有 docstring 说明用途
- [ ] 每个公共函数/类有 docstring
- [ ] 如有特殊设计决策，在 docstring 里说明 why

### 7.6 提交
- [ ] 在 `feat/W1-D3-19-llamaindex` 分支
- [ ] commit message：`feat: add LlamaIndex abstraction layer for LLM/Embedding/Rerank\n\nRefs: #19`
- [ ] 推送 + 创建 PR 到 `dev` 分支

---

## 8. 禁止事项

- ❌ 不要在 `llm.py` 之外直接 import openai / dashscope
- ❌ 不要把 API Key 写进任何代码（必须从 settings 读）
- ❌ 不要给工厂函数加任何"覆盖配置"的参数（如 `get_llm(temperature=0.7)`），调用方必须通过 settings 修改
- ❌ 不要在 BailianRerank 里静默吞错（API 失败要抛异常）
- ❌ 不要在测试里写死 API Key 或 URL（用 fixture / monkeypatch）
- ❌ 不要为了"看起来更通用"添加未在本 spec 中要求的功能（YAGNI）

---

## 9. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| 用 `os.getenv()` 直接读 env | 绕过 pydantic 校验，运行时才报错 | 用 settings 单例 |
| Embedding 维度写死 1024 | 切换模型时不一致 | 由模型自身返回决定，但要在测试断言 |
| Rerank 用 async httpx | LlamaIndex `_postprocess_nodes` 是 sync 接口 | 用同步 `httpx.Client` |
| Rerank 失败时返回原 nodes | 静默降级会掩盖问题，影响评估准确性 | 必须抛 LLMServiceError |
| 把 `get_llm()` 做成单例 cache | LLM 实例可能持有过时配置 | 每次调用返回新实例（OpenAILike 本身轻量）|
| 忘记 `is_chat_model=True` | OpenAILike 默认走 completion 端点，百炼 omni 不支持 | 显式设置 True |

---

## 10. 参考资料

### 官方文档
- [百炼 OpenAI 兼容模式](https://help.aliyun.com/zh/model-studio/getting-started/compatibility-with-openai)
- [百炼 Rerank API](https://help.aliyun.com/zh/model-studio/developer-reference/text-rerank-api)
- [LlamaIndex OpenAILike LLM](https://docs.llamaindex.ai/en/stable/api_reference/llms/openai_like/)
- [LlamaIndex Custom NodePostprocessor](https://docs.llamaindex.ai/en/stable/module_guides/querying/node_postprocessors/custom_node_postprocessor/)
- [pydantic-settings 文档](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [infinity-embedding 服务](https://github.com/michaelfeil/infinity)

### 项目内文档
- `docs/CLAUDE.md`：项目级开发规则（七条铁律）
- `docs/RAG知识库_系统架构图.docx` §6.2：环境变量完整列表
- `docs/RAG知识库_完整任务书_V2.0.docx` §3.4：七条铁律详解

---

## 11. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 CLAUDE.md + 百炼文档 | 30 分钟 |
| 实现 config.py | 30 分钟 |
| 实现 llm.py 三个工厂函数 | 60 分钟 |
| 实现 BailianRerank 类 | 90 分钟 |
| 写 7 个测试用例 | 90 分钟 |
| 跑测试 + 调试 | 60 分钟 |
| 静态检查 + 格式化 + 提交 | 30 分钟 |
| **合计** | **~6.5 小时** |

如果 4 小时内做不完，先暂停跟项目负责人沟通是不是 spec 有漏洞或环境有问题。

---

_本 spec 版本：v1.0 | 任务 ID：#19 | 最后更新：2026-06-03_
