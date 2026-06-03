# Handoff: 任务 #19 - LlamaIndex 抽象层封装

> 执行者：Codex
> 完成日期：2026-06-03
> 分支：feat/W1-D3-19-llamaindex-abstract
> PR：#（PR 创建后回填）

## 1. 任务概述

本任务实现了统一的 LlamaIndex 模型调用抽象层，业务侧后续通过 `get_llm()`、`get_embedding()`、`get_reranker()` 获取模型能力，不直接依赖具体 SDK 或供应商私有调用。Embedding 走本地 infinity 服务，LLM 和 Rerank 从 `settings` 读取云端百炼配置；Rerank 通过自定义 `BailianRerank` 适配 LlamaIndex `BaseNodePostprocessor` 接口。

## 2. 完成清单（对应 spec §4）

- [x] backend/app/core/config.py（已有，复用 `settings`）
- [x] backend/app/core/exceptions.py（已有，复用 `LLMServiceError`）
- [x] backend/app/services/llm.py（含 `get_llm` / `get_embedding` / `get_reranker` / `BailianRerank`）
- [x] backend/tests/services/__init__.py
- [x] backend/tests/services/test_llm.py（9 个测试用例；2 个真实云端 integration 在占位 Key 下 skip）
- [x] backend/pyproject.toml 追加 llama-index 依赖和 `integration` pytest marker
- [x] backend/uv.lock 由 `uv add` 更新
- [x] .env.example 修正本地 infinity embedding base URL

## 3. 与 Spec 的偏差

- 偏差 1：`.env.example` 中 `EMBED_BASE_URL` 从 `http://localhost:8080/v1` 调整为 `http://localhost:8080`。原因是当前 `docker-compose.yml` 启动的 `michaelf34/infinity v2` 实际可用接口为 `/embeddings`，`/v1/embeddings` 返回 404；不调整会导致 LlamaIndex `OpenAILikeEmbedding` 访问失败。
- 偏差 2：除 spec 要求用例外，额外增加了 `test_get_llm_returns_configured_client` 和本地 HTTP rerank 成功路径测试。原因是当前 `LLM_API_KEY` 为占位值，云端 LLM/Rerank integration 按要求 skip；额外测试用于覆盖工厂实例化、Rerank HTTP 请求、响应解析、排序和 score 回填逻辑。

## 4. 本地验收结果

| 项目 | 结果 | 备注 |
|------|------|------|
| uv sync | ✅ | `Resolved 94 packages` / `Checked 92 packages`，耗时 0.06 秒 |
| pytest（services）| ✅ | `7 passed / 2 skipped / 1 warning`，耗时 11.66 秒 |
| coverage | ✅ | `app.services.llm` 覆盖率 91% |
| Embedding 集成测试 | ✅ | 本地 infinity，单条和 batch 均返回 1024 维向量 |
| LLM 集成测试 | ⏭️ skip | `LLM_API_KEY` 为占位值，skip reason: `需要真实 LLM_API_KEY` |
| Rerank 集成测试 | ⏭️ skip | `LLM_API_KEY` 为占位值，skip reason: `需要真实 LLM_API_KEY` |
| ruff check | ✅ | `All checks passed!` |
| ruff format --check | ✅ | `4 files already formatted` |
| mypy | ✅ | `Success: no issues found in 2 source files` |
| grep import dashscope | ✅ 无命中 | 使用 Git for Windows `grep.exe`；无输出，exit code 1 |
| grep openai | ✅ 无命中 | `backend/app/services/` 无直接 `openai` SDK import |
| grep 硬编码 URL / 模型名 | ✅ 无命中 | `backend/app/` 无 `https://dashscope` / `qwen3.5` / `gte-rerank` |

## 5. 已知问题 / 风险

- LLM 和真实百炼 Rerank 集成测试因 `LLM_API_KEY` 仍为占位值被 skip，需要配置真实 API Key 后回归。
- `pytest` 输出中有 1 个既有 `StarletteDeprecationWarning`，来源为现有 `tests/conftest.py` 导入 FastAPI `TestClient`，不影响本任务服务层测试结果。
- 本地 `.env` 已同步调整 `EMBED_BASE_URL=http://localhost:8080` 用于验收；`.env` 在 `.gitignore` 中，不会提交。

## 6. 给审查者的提示（至少 3 条）

- 重点 1：检查 `BailianRerank._postprocess_nodes` 的错误处理，API 请求失败、坏响应和非法 node index 都应抛 `LLMServiceError`，不能静默返回原 nodes。
- 重点 2：确认 `get_llm()`、`get_embedding()`、`get_reranker()` 均不接收调用方覆盖参数，所有模型名、URL、Key 和业务参数来自 `settings`。
- 重点 3：确认服务层没有直接 `dashscope` 或 OpenAI SDK import；OpenAI-compatible 调用只通过 LlamaIndex `OpenAILike` / `OpenAILikeEmbedding`。
- 重点 4：关注 `EMBED_BASE_URL` 修正是否与当前 infinity v2 Docker 服务保持一致。

## 7. 给下一轮（#20 最小 RAG Pipeline）的提示（至少 2 条）

- 上下文 1：#20 应直接 `from app.services.llm import get_llm, get_embedding, get_reranker`，不要在 pipeline 里重新创建模型客户端。
- 上下文 2：`BailianRerank` 已实现 LlamaIndex `BaseNodePostprocessor` 接口，可直接放入 `RetrieverQueryEngine` 的 `node_postprocessors` 列表。
- 上下文 3：当前本地 embedding base URL 应使用 `http://localhost:8080`；LlamaIndex 会拼接 `/embeddings`。
