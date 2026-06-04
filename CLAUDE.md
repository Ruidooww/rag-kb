# RAG 知识库项目 - 开发规则（Codex/Claude Code 必读）

> 本文件放在项目根目录，Claude Code/Codex 会自动读取。
> 任何任务执行前请先理解本文件的全部规则。

---

## 项目概述

私有化 RAG 知识库系统，混合云架构：
- **本地**：文档、向量库（Qdrant）、客户主数据（PostgreSQL）、Embedding（bge-m3）
- **云端**：LLM/VLM（qwen3.5-omni-flash）、Rerank（gte-rerank-v2）

目标：30 人公司，700 份文档，支持基础问答 + 客户对比报告 + 服务路径图 + 关系图。

详细背景见 `docs/RAG知识库_完整任务书_V2.0.docx`。

---

## 🔒 自审查机制 v2.1（每个代码任务强制读）

⚡ **平时只读浓缩卡，按需回查源文档**：

1. **`docs/CODEX_QUICK_REF.md`** ← 速查卡（七条铁律 / 10 步流程 / Part A-E / 反模式 / 命令）
2. **对应任务 spec**：`docs/tasks/W?-D?-N-xxx.md`
3. **上一轮 Handoff**：`docs/handoffs/W?-D?-M-handoff.md`

QUICK_REF 解决不了的细节再打开 `SELF_REVIEW.md` / `ANTIPATTERNS.md` / `TASK_PROMPT_TEMPLATE.md` / `HANDOFF_TEMPLATE.md` / `REVIEW_FEEDBACK_TEMPLATE.md`。

**任何代码任务不完整走自审查 = 任务未完成**。

---

## 🔍 CodeGraph 集成（优先于 grep）

本项目已集成 [CodeGraph](https://github.com/) 作为代码索引工具，通过 MCP 服务对 Codex / Claude Code 透明。

### 优先级
- 查找符号：用 `codegraph_search` / `codegraph_explore` > `grep`
- 查调用关系：用 `codegraph_callers` / `codegraph_callees` > 人工追踪
- 评估改动影响：用 `codegraph_impact`
- 测试范围：用 `codegraph_affected`

### 何时仍用 grep
- CodeGraph 索引未覆盖的文件（如 `.env`、`docs/`、`docker-compose.yml`）
- 自审查 Part A3 的铁律 grep（必须用文本扫描的场景）

### 索引同步
代码改动后，本地建议跑：
```bash
codegraph sync   # 增量同步
codegraph status # 看索引状态
```

---

## 🔒 八条迁移友好铁律（最高优先级）

**违反任何一条 = 重做该任务。**

### 铁律 #1：所有模型调用走统一抽象层
- ✅ 允许：`from app.services.llm import get_llm, get_embedding, get_reranker`
- ❌ 禁止：`import dashscope`
- ❌ 禁止：`from openai import OpenAI`（业务代码里不能直接用）
- ❌ 禁止：`import litellm` 等其他直连客户端

### 铁律 #2：配置 100% 走环境变量
- ❌ 禁止：`MODEL_NAME = "qwen3.5-omni-flash"`
- ❌ 禁止：`BASE_URL = "https://dashscope.aliyuncs.com/..."`
- ✅ 允许：`model_name = settings.llm_model`
- ✅ 允许：`base_url = settings.llm_base_url`

### 铁律 #3：使用 OpenAI-Compatible 协议
- LLM：百炼 `compatible-mode/v1` 端点 + LlamaIndex `OpenAILike`
- Embedding：本地 `infinity` 服务（OpenAI 兼容）+ `OpenAIEmbedding`
- Rerank：百炼 rerank API（非 OpenAI 标准，自定义 wrapper）

### 铁律 #4：Embedding 用 bge-m3（本地）
- 不要换成 text-embedding-v4 / text-embedding-3 等云端 Embedding
- 维度：1024
- 部署：infinity 容器，连接地址走 `EMBED_BASE_URL`

### 铁律 #5：Prompt 写到 prompts/ 目录
- 一个任务一个文件，如 `prompts/extract_metadata.txt`、`prompts/base_qa.txt`
- 不要在 Python 字符串里写超过 3 行的 Prompt
- 用 jinja2 或 `str.format()` 注入变量

### 铁律 #6：关键参数走 config.yaml
- `chunk_size`、`top_k`、`rerank_n`、`temperature`、`max_tokens`
- 不要硬编码这些数值

### 铁律 #7：保留 Ollama 兼容性
- 切换到本地 Ollama 只改 `.env`，业务代码必须零改动
- 每周五运行迁移验证（任务 #52）

### 铁律 #8：Agent 编排走 LangGraph，RAG 工具走 LlamaIndex

- ✅ 允许：`from langgraph.graph import StateGraph`
- ✅ 允许：LangGraph 节点调 `from app.services.llm import get_llm`
- ❌ 禁止：业务代码用 LlamaIndex Workflows（除非有强理由且 spec 明示）
- ❌ 禁止：在 LangGraph 节点里直接 import `openai` / `dashscope`
- 分层原则：
  - **RAG 工具层**：LlamaIndex（embedding / LLM / rerank / chunking）
  - **Agent 编排层**：LangGraph（状态图 / 节点 / 条件边 / 工具调用）
  - **桥接**：LangGraph 节点是 Python 函数，可调任何 LlamaIndex 工具

---

## 技术栈版本（强制）

| 组件 | 版本 |
|------|------|
| Python | 3.14 |
| 包管理 | uv（禁止 pip + requirements.txt）|
| FastAPI | ≥ 0.110 |
| LlamaIndex | ≥ 0.10 |
| Pydantic | v2 |
| Node.js | 22 LTS |
| Next.js | 15 |
| Qdrant | ≥ 1.10 |
| PostgreSQL | 16 |

---

## 目录结构（严格遵守）

```
rag-kb/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 路由（一个资源一个文件）
│   │   ├── agents/       # Agent 实现（router / base_qa / comparison / ...）
│   │   ├── services/     # 底层服务（llm / qdrant / postgres / minio）
│   │   ├── workflows/    # LlamaIndex Workflows 实现
│   │   ├── models/       # Pydantic Schemas（不是 ORM）
│   │   ├── db/           # SQLAlchemy ORM + alembic migrations
│   │   └── core/         # config / logging / exceptions / deps
│   ├── tests/            # pytest 测试
│   ├── scripts/          # 批量脚本（batch_ingest / batch_extract / evaluate）
│   ├── prompts/          # Prompt 模板（.txt 或 .j2）
│   ├── config.yaml       # 业务参数
│   ├── .env.example
│   └── pyproject.toml
├── web/                  # Next.js 15 前端
├── docker/               # Dockerfile（每个服务一个）
├── docker-compose.yml
├── docs/
│   ├── CLAUDE.md         # ← 本文件
│   ├── architecture.md
│   ├── naming-convention.md
│   └── tasks/            # 任务详细 spec
│       └── W1-D3-19-llamaindex-abstract.md
├── data/                 # Docker 卷挂载（gitignore）
└── README.md
```

---

## 编码规范

### Python
- **命名**：函数 `snake_case`、类 `PascalCase`、常量 `UPPER_SNAKE`、私有 `_leading_underscore`
- **类型**：所有公共函数必须有 type hints，启用 `mypy --strict`
- **字符串**：双引号优先
- **异步**：API endpoint 全部 `async def`，service 层能 async 就 async
- **导入顺序**：标准库 → 第三方 → 本地，每组按字母序

### 异常处理
- 自定义异常继承 `app.core.exceptions.AppException`
- API 层用全局 exception handler 统一转 HTTP 响应
- 禁止 `except:` 或 `except Exception: pass`（必须 log + 处理或重抛）

### 日志
- 用 `loguru` 或标准 `logging`
- 禁止 `print()`
- 关键操作记录：模型调用、入库、检索、Agent 步骤

### 测试
- 框架：`pytest` + `pytest-asyncio`
- 每个 `app/services/*.py` 必须有对应 `tests/services/test_*.py`
- 每个 Agent 必须有端到端集成测试
- 覆盖率目标：核心模块 ≥ 85%，整体 ≥ 70%

### 数据库
- ORM：SQLAlchemy 2.0（async style）
- Migration：alembic
- 不要写裸 SQL（除非性能场景 + 注释说明）

---

## 提交前检查（CI 也会跑）

```bash
uv run ruff format .
uv run ruff check . --fix
uv run mypy backend/app
uv run pytest backend/tests
```

任何一项不过不能合并。

---

## 禁止事项清单

- ❌ `print()` 调试代码（用 logger）
- ❌ `requirements.txt`（用 pyproject.toml + uv）
- ❌ commit `.env`、API Key、任何 secrets
- ❌ 硬编码 URL / 端口 / 模型名 / 路径
- ❌ 在 main 分支直接提交（必须 PR）
- ❌ 忽略类型错误（`# type: ignore` 必须附注释说明）
- ❌ 删除/重命名公共 API 不更新调用方
- ❌ 跳过测试（`@pytest.mark.skip` 必须附 issue 链接）

---

## Git 规范

### 分支
- `main`：可发布的稳定版本
- `dev`：开发主分支
- `feat/W1-D3-19-llamaindex`：任务分支（命名 = task spec 文件名）

### Commit Message
```
<type>: <subject>

<body>

Refs: #<task-id>
```

type：`feat` / `fix` / `refactor` / `test` / `docs` / `chore`

---

## 任务 spec 使用方式

1. 项目 `docs/tasks/` 目录有详细任务 spec
2. 文件命名：`W{周}-D{日}-{任务ID}-{kebab-case-描述}.md`
3. 执行任务前先读对应 spec
4. spec 的「验收标准」是 Definition of Done
5. 完成后用 `git commit -m "feat: complete #<task-id>"` 提交

---

## 关键参考

- 完整任务书：`docs/RAG知识库_完整任务书_V2.0.docx`
- 数据治理 SOP：`docs/RAG知识库_数据治理SOP.docx`
- 系统架构图：`docs/RAG知识库_系统架构图.docx`
- 任务清单：`docs/RAG知识库_任务清单.md`
- 百炼 OpenAI 兼容文档：https://help.aliyun.com/zh/model-studio/getting-started/compatibility-with-openai
- LlamaIndex 文档：https://docs.llamaindex.ai/

---

_本文件版本：v1.0 | 最后更新：2026-06-03_
