# Handoff: 任务 #18 - 搭建 FastAPI 项目骨架

> 执行者：Codex
> 完成日期：2026-06-03
> 分支：feat/W1-D3-18-fastapi-skeleton
> PR：#（占位）

## 1. 任务概述

本任务在 `backend/` 下搭建 FastAPI 后端骨架，包括配置加载、日志、异常处理、健康检查路由和测试基础设施。实现保持在骨架范围内，不包含 Agent、RAG、数据库 ORM 或模型调用业务逻辑。配置层按项目根目录 `.env` 与 `config.yaml` 合并加载，并通过 `pydantic-settings` 做必填项校验。

## 2. 完成清单（对应 spec §4）

- [x] backend/pyproject.toml
- [x] backend/app/main.py
- [x] backend/app/core/config.py
- [x] backend/app/core/exceptions.py
- [x] backend/app/core/logging.py
- [x] backend/app/api/health.py
- [x] backend/app/api/router.py
- [x] backend/tests/conftest.py
- [x] backend/tests/api/test_health.py
- [x] backend/.python-version
- [x] backend/README.md
- [x] backend/uv.lock

## 3. 与 Spec 的偏差

- 偏差 1：本地验收在 Windows PowerShell 环境执行，`uvicorn --reload` 后台启动与关闭使用 PowerShell 进程控制替代 `&`、`sleep`、`kill %1`。影响：验收目标等价，`/api/v1/health` 和 `/docs` 均通过真实 HTTP 请求验证。
- 偏差 2：`test_app_exception_handler` 没有按示例保留 `pass`，而是在测试中临时注册一个抛出 `ValidationError` 的端点。影响：覆盖全局异常 handler，生产应用不保留测试端点。

## 4. 本地验收结果（贴 Step 7 的真实输出）

| 项目 | 结果 | 备注 |
|------|------|------|
| uv sync | ✅ | `Resolved 42 packages in 10ms`; `Checked 40 packages in 17ms`; 耗时 `628ms` |
| uvicorn 启动 | ✅ | `Uvicorn running on http://127.0.0.1:8000`; `Starting RAG-KB backend in development mode` |
| GET /api/v1/health | ✅ | 返回 JSON: `{"status":"ok","app_env":"development","version":"0.1.0"}` |
| GET /docs | ✅ | HTTP `200` |
| pytest | ✅ | `2 passed / 0 failed / 0 skip`; 有 1 条 `StarletteDeprecationWarning` |
| ruff check | ✅ | `All checks passed!` |
| ruff format --check | ✅ | `17 files already formatted` |
| mypy | ✅ | `Success: no issues found in 14 source files` |
| grep print( | ✅ 无命中 | `grep` exit code `1`，表示无匹配 |
| grep import logging | ✅ 无命中 | `grep` exit code `1`，表示无匹配 |
| grep openai/dashscope | ✅ 无命中 | `grep` exit code `1`，表示无匹配 |

关键原始输出摘录：

```text
{"status":"ok","app_env":"development","version":"0.1.0"}
DOCS_HTTP_CODE=200
======================== 2 passed, 1 warning in 0.08s =========================
All checks passed!
17 files already formatted
Success: no issues found in 14 source files
GREP_PRINT_EXIT=1
GREP_LOGGING_EXIT=1
GREP_MODEL_EXIT=1
```

日志格式验证摘录：

```text
2026-06-03 21:38:55 | INFO     | app.main:lifespan:18 | Starting RAG-KB backend in development mode
2026-06-03 21:42:31 | INFO     | uvicorn.protocols.http.httptools_impl:send:484 | 127.0.0.1:2255 - "GET /docs HTTP/1.1" 200
```

## 5. 已知问题 / 风险

- 本地 `.env` 由 `.env.example` 复制生成，仅用于验收，未提交；真实环境需要替换 `LLM_API_KEY` 等占位值。
- 当前依赖组合下 `pytest` 会出现 `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`，不影响测试通过，后续可在 FastAPI/Starlette/httpx 版本策略明确后处理。
- Windows `WinNAT` 会动态保留 `8000/8080` 等端口；本次验收前已通过管理员 PowerShell `net stop winnat` 释放端口。

## 6. 给审查者的提示

- 重点 1：检查 `backend/app/core/config.py` 的加载优先级是否符合默认值 -> `config.yaml` -> `.env`，且必填 `.env` 字段没有默认值。
- 重点 2：检查 `backend/app/core/logging.py` 是否满足 loguru 输出到 stderr 与 `logs/app.log`，并拦截 uvicorn/fastapi stdlib 日志。
- 重点 3：检查 `backend/app/main.py` 是否保持骨架职责，没有引入业务逻辑或直连模型客户端。

## 7. 给下一轮（#19 LlamaIndex 抽象层）的提示

- 上下文 1：后续模型调用必须从 `app.services.llm` 统一抽象层进入，不要在业务代码中直接 `import dashscope`、`from openai import OpenAI` 或 `import litellm`。
- 上下文 2：`settings` 已暴露 LLM、Embedding、Rerank、Postgres、Qdrant、MinIO 以及 `config.yaml` 业务参数，可直接复用，避免新增 `os.getenv()`。
