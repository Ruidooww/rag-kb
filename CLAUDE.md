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

## 🔒 十条迁移友好铁律（最高优先级）

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

### 铁律 #9：CRM 调用走统一抽象层（services/crm.py）

- ✅ 允许：`from app.services.crm import get_crm`，业务调 `await crm.get_customer(...)` / `await crm.list_contracts(...)`
- ❌ 禁止：`import xiaoshouyi` / `import fxiaoke` / `from hubspot import HubSpot`
- ❌ 禁止：在 Agent 节点 / API endpoint 直接拼 CRM 厂家 HTTP / SDK
- 分层原则与铁律 #1 同构：CRM 厂家拍板前接口先冻结（`CRMService` ABC + MockCRM 实现），落地厂家时只改 `services/crm.py` 一个文件
- LangGraph Agent 内的 CRM 工具（`get_customer_basic` / `get_contract` / ...）必须经过 `services/crm.py`，节点禁止直连 SDK
- **CRM 工具集物理隔离**：CRM 工具只能进 `INTERNAL_TOOLS`，绝不允许进 `EXTERNAL_TOOLS`（见铁律 #10）

### 铁律 #10：Agent 工具集物理隔离（外部 vs 内部）

权限不在 prompt 里，权限在工具集里。LLM 即使被 prompt injection，调不到不存在的工具。

- ✅ 允许：构建 Agent 前根据 `user.is_external` 选 `EXTERNAL_TOOLS` 或 `INTERNAL_TOOLS`
- ❌ 禁止："一个 Agent 装所有工具靠 prompt 限制"——prompt 不是安全边界
- ❌ 禁止：CRM 工具 / 内部 `search_docs` / `get_contract` 进 `EXTERNAL_TOOLS`
- ❌ 禁止：通过参数把 `internal=True` 传给 EXTERNAL_TOOLS 里的工具"开权限"
- 标准模式：
  ```python
  EXTERNAL_TOOLS = [search_external_docs]                          # 公众号 / 客服渠道 Agent
  INTERNAL_TOOLS = [search_docs, get_customer_basic, get_contract] # 飞书员工 Agent

  def build_agent(user: User):
      tools = EXTERNAL_TOOLS if user.is_external else INTERNAL_TOOLS
      return create_react_agent(llm, tools)
  ```
- 4 层外部访问防御（缺一层即重做该任务）：
  | 层 | 机制 |
  |----|------|
  | 1 | 工具集物理隔离（CRM / 内部 search 不进 EXTERNAL_TOOLS）|
  | 2 | 每个内部工具入口 `if user.is_external: raise PermissionError`（二次校验）|
  | 3 | API endpoint 物理隔离（`/api/v1/internal/*` vs `/api/v1/public/*` 独立 router 树）|
  | 4 | 审计日志（外部 user 触达内部工具 → 立即告警 + 事后追责）|

---

## 🧭 横切原则（不到铁律级别，每个任务都要遵守）

### 原则 P1：API 响应脱敏

- 任何返回客户/员工敏感字段（手机号 / 邮箱 / 身份证 / 合同金额 / 内部部门代码 / 用量与费用）的 endpoint，
  必须经 `app.api.utils.sanitize(payload, user)` 处理后再返回
- `sanitize()` 根据 `user.is_external` / `user.role` 决定字段可见性；外部用户拿到掩码版（如 `138****5678`）
- 不要在 Pydantic response model 里写 raw 字段然后"前端隐藏"——脱敏必须在 API 层完成
- 测试断言：外部用户拉任何 endpoint 都不应在 JSON 里出现 11 位手机号 / 完整邮箱

### 原则 P2：工具集版本化

- `EXTERNAL_TOOLS` / `INTERNAL_TOOLS` 列表必须在单文件集中定义（如 `app/agents/tool_registry.py`）
- 每次变更（加/删/改工具）必须配 1 个断言测试，证明工具集 diff 符合预期
- 反例：CRM 工具误进 `EXTERNAL_TOOLS` → 单测立刻报错，不允许靠 code review 兜底
- 见 Phase 2+ 待办「Agent 工具集断言测试」

### 原则 P3：内外路由树严格分流

- FastAPI 维护两个独立 router：`internal_router`（挂 `/api/v1/internal/`）+ `public_router`（挂 `/api/v1/public/`）
- admin / 用量 / 知识缺口 / CRM / 内部 search endpoint 只挂 `internal_router`
- 公众号 / 外部客服 endpoint 只挂 `public_router`
- 真正中性 endpoint（如 feedback、health）才挂顶层 `api_router`
- 见 #68 spec 落地

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
- ❌ 业务代码直接 import CRM SDK（违反铁律 #9）
- ❌ "一个 Agent 装所有工具靠 prompt 限制权限"（违反铁律 #10）
- ❌ admin / 用量 / CRM endpoint 挂到 `/public/*` 或外部可达 router 树（违反原则 P3）
- ❌ 在 Pydantic response 直接返回手机号 / 邮箱 / 合同金额等明文字段给外部用户（违反原则 P1）

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

_本文件版本：v1.1 | 最后更新：2026-06-05_

变更（v1.1）：
- 八条铁律扩为十条：加 #9（CRM 抽象层）+ #10（Agent 工具集物理隔离 + 4 层外部访问防御）
- 新增「横切原则」段：P1 API 响应脱敏 / P2 工具集版本化 / P3 内外路由树严格分流
- 禁止事项清单同步扩展
