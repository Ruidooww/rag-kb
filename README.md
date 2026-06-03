# 私有化 RAG 知识库系统

> 混合云架构 · 多 Agent 编排 · 销售/售后场景增强

## 概述

为 30 人公司搭建的私有化 RAG 知识库，支持：

- 📚 基础文档问答（700 份 Word/Excel/PPT）
- 🔍 客户档案查询 + 客户级权限
- 📊 客户对比报告（销售现场场景）
- 📈 服务路径图（售后场景）
- 🕸 客户关系图
- 💬 自由问答 + 多 Agent 编排
- 📱 移动端 PWA（可选）

**架构特点**：数据 100% 本地，仅 LLM 推理调用云端 API（混合云）。

## 文档导航

| 文档 | 用途 |
|------|------|
| [完整任务书 V2.0](docs/RAG知识库_完整任务书_V2.0.docx) | 项目目标、技术架构、实施计划 |
| [数据治理 SOP](docs/RAG知识库_数据治理SOP.docx) | 元数据规范、入库审核流程 |
| [系统架构图](docs/RAG知识库_系统架构图.docx) | 整体架构、Pipeline 详图 |
| [任务清单](docs/RAG知识库_任务清单.md) | 56 个待办任务 |
| [CLAUDE.md](CLAUDE.md) | 开发规则（Codex/Claude Code 必读）|
| [任务 spec](docs/tasks/) | 每个代码任务的详细执行规格 |

## 技术栈

| 层级 | 技术 |
|------|------|
| LLM/VLM | qwen3.5-omni-flash（云端百炼）|
| Rerank | gte-rerank-v2（云端百炼）|
| Embedding | bge-m3（本地 infinity 服务）|
| 向量库 | Qdrant（Docker）|
| 元数据库 | PostgreSQL 16 |
| 对象存储 | MinIO |
| 后端 | FastAPI + Python 3.14 + LlamaIndex |
| 前端 | Next.js 15 + Node.js 22 LTS |

## 快速开始

### 1. 前置准备

- [ ] 已有阿里云百炼 API Key（任务 #13）
- [ ] 已安装 Docker、Python 3.14、Node.js 22+（任务 #14）

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY
```

### 3. 启动本地服务

```bash
docker compose up -d
docker compose ps   # 验证所有服务 healthy
```

服务端口：
- Qdrant: http://localhost:6333
- PostgreSQL: localhost:5432
- MinIO Console: http://localhost:9001
- Infinity (bge-m3): http://localhost:8080

### 4. 后端开发（任务 #18 之后）

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### 5. 前端开发（Phase 3 之后）

```bash
cd web
npm install
npm run dev
```

## 项目结构

```
.
├── backend/             # FastAPI 后端
│   ├── app/             # 应用代码
│   │   ├── api/         # 路由
│   │   ├── agents/      # Agent 实现
│   │   ├── services/    # 底层服务
│   │   ├── workflows/   # LlamaIndex Workflows
│   │   ├── models/      # Pydantic Schemas
│   │   ├── db/          # SQLAlchemy + alembic
│   │   ├── core/        # 配置/日志/异常
│   │   └── prompts/     # Prompt 模板
│   ├── tests/
│   └── scripts/         # 批量脚本
├── web/                 # Next.js 前端
├── docker/              # Dockerfile
├── docs/                # 项目文档
│   ├── tasks/           # 任务详细 spec
│   └── archive/         # 历史版本
├── config.yaml          # 业务参数
├── docker-compose.yml   # 本地服务编排
├── .env.example         # 环境变量模板
└── CLAUDE.md            # 开发规则
```

## 开发规则

**所有开发必须先读 [CLAUDE.md](CLAUDE.md)。**

核心铁律：
1. 所有模型调用走 `backend/app/services/llm.py`
2. 配置 100% 走环境变量
3. 使用 OpenAI-Compatible 协议
4. Embedding 用 bge-m3 本地
5. Prompt 放 `prompts/`
6. 参数放 `config.yaml`
7. 每周验证 Ollama 兼容性

## 实施进度

当前阶段：**Week 1 - 环境搭建**

详见 [任务清单](docs/RAG知识库_任务清单.md)。

## License

公司内部项目，未授权请勿外传。
