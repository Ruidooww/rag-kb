# Task #18: 搭建 FastAPI 项目骨架

> **Phase**: 1 | **Week**: 1 | **Day**: 3
> **预估工时**: 2-3 小时
> **优先级**: 🟡 重要（后续所有任务的代码基础）
> **前置任务**: #15、#16、#17

---

## 1. 任务背景

本任务搭建 FastAPI 后端的"骨架"——包含配置加载、日志、异常处理、健康检查、测试基础设施。

**不实现任何业务逻辑**（Agent、RAG、模型调用、数据库 ORM 都在后续任务做）。本任务的目标是让骨架"能跑起来"且"符合 CLAUDE.md 全部规范"。

完成后，应该能：
- `uv sync` 一键装好依赖
- `uvicorn app.main:app --reload` 起服务
- `curl http://localhost:8000/health` 返回服务状态
- `uv run pytest` 全绿
- `uv run ruff check` 和 `uv run mypy` 全绿

---

## 2. 前置依赖（执行前必须确认）

| # | 验证方法 | 期望 |
|---|---------|------|
| Python 3.14（或 3.13）已安装 | `python --version` | 返回版本号 |
| uv 已安装 | `uv --version` | 返回版本号 |
| Docker 服务全部 healthy | `docker compose ps` | 4 个服务都 healthy |
| 项目根目录结构存在 | `ls C:\Users\Ruidoww\Desktop\RAG\backend\app` | 看到 api/agents/services 等子目录 |
| CLAUDE.md 已读 | - | 必须先读项目根目录 CLAUDE.md |

**如 uv 未安装**：
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## 3. 任务目标

在 `backend/` 目录下完成：
1. `pyproject.toml` + `uv.lock`（uv 项目）
2. FastAPI 主应用（`app/main.py`）
3. 配置加载层（`app/core/config.py`）
4. 异常类（`app/core/exceptions.py`）
5. 日志配置（`app/core/logging.py`）
6. 健康检查端点（`app/api/health.py`）
7. API 路由聚合（`app/api/router.py`）
8. 测试骨架（`tests/conftest.py` + `tests/api/test_health.py`）
9. 工具链配置（ruff / mypy 集成在 `pyproject.toml`）

---

## 4. 输出文件清单（详细要求）

### 4.1 `backend/pyproject.toml`

用 `uv init` 初始化后修改，包含：

```toml
[project]
name = "rag-kb-backend"
version = "0.1.0"
description = "Private RAG knowledge base backend"
requires-python = ">=3.13,<3.15"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.7",
    "pydantic-settings>=2.4",
    "pyyaml>=6.0",
    "loguru>=0.7",
    "httpx>=0.27",
    "python-multipart>=0.0.9",  # FastAPI 文件上传支持
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5",
    "ruff>=0.6",
    "mypy>=1.11",
    "httpx>=0.27",  # 测试用 TestClient
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "W", "UP", "ASYNC", "SIM"]
ignore = ["E501"]  # line-too-long 交给 formatter

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["B011"]  # 测试里允许 assert False

[tool.mypy]
python_version = "3.13"
strict = true
plugins = ["pydantic.mypy"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```


### 4.2 `backend/app/core/config.py`

**职责**：合并加载 `.env`（项目根目录）+ `config.yaml`（项目根目录），暴露 `settings` 单例。

**要求**：
- `Settings` 类继承 `BaseSettings`（pydantic-settings）
- `.env` 来源的字段（带 SecretStr 加密）：
  ```python
  llm_provider: str
  llm_base_url: str
  llm_model: str
  llm_api_key: SecretStr
  rerank_base_url: str
  rerank_model: str
  embed_base_url: str
  embed_model: str
  postgres_url: str
  qdrant_url: str
  minio_endpoint: str
  minio_access_key: SecretStr
  minio_secret_key: SecretStr
  minio_bucket: str
  app_env: str = "development"
  app_port: int = 8000
  app_log_level: str = "INFO"
  ```
- `config.yaml` 来源的字段（带默认值）：
  ```python
  chunk_size: int = 800
  chunk_overlap: int = 100
  top_k: int = 30
  rerank_n: int = 5
  min_score: float = 0.5
  temperature: float = 0.3
  max_tokens: int = 2000
  llm_timeout: int = 60
  llm_max_retries: int = 2
  router_confidence_threshold: float = 0.7
  ingest_concurrency: int = 5
  ```
- 配置加载顺序：默认值 → config.yaml → .env（env 优先级最高）
- 用 `@lru_cache` 装饰 `get_settings()`，模块底部 `settings = get_settings()`
- **路径处理**：.env 在项目根（`backend/` 的父目录），用 `Path(__file__).parents[3] / ".env"` 定位
- 缺失任何 `.env` 必填字段时抛 ValidationError（不要默认值）

### 4.3 `backend/app/core/logging.py`

**职责**：用 loguru 统一日志，禁止使用 stdlib `print`/`logging`。

**要求**：
- 暴露 `setup_logging(level: str)` 函数，在 `main.py` lifespan 中调用
- 日志格式：`{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}`
- 输出到 stderr（开发）+ 文件 `logs/app.log`（保留 7 天，轮转 10MB）
- 拦截 uvicorn/fastapi 的 stdlib 日志，转 loguru
- 给业务代码暴露：`from loguru import logger`

### 4.4 `backend/app/core/exceptions.py`

```python
class AppException(Exception):
    """所有自定义异常的基类。"""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ConfigError(AppException):
    error_code = "CONFIG_ERROR"
    status_code = 500


class LLMServiceError(AppException):
    error_code = "LLM_SERVICE_ERROR"
    status_code = 502


class NotFoundError(AppException):
    error_code = "NOT_FOUND"
    status_code = 404


class PermissionDeniedError(AppException):
    error_code = "PERMISSION_DENIED"
    status_code = 403


class ValidationError(AppException):
    error_code = "VALIDATION_ERROR"
    status_code = 400
```

并在 `main.py` 注册全局 exception handler：将 `AppException` 转 JSON 响应：
```json
{"error_code": "...", "message": "...", "status_code": 4xx}
```

### 4.5 `backend/app/api/health.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    app_env: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """服务健康检查。后续可扩展为检查依赖服务（PG/Qdrant/Infinity）状态。"""
    from app.core.config import settings
    return HealthResponse(
        status="ok",
        app_env=settings.app_env,
        version="0.1.0",
    )
```

### 4.6 `backend/app/api/router.py`

聚合所有子路由：
```python
from fastapi import APIRouter
from app.api import health

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
# 后续任务会追加 documents / query / customers / agents 等路由
```


### 4.7 `backend/app/main.py`

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.app_log_level)
    from loguru import logger
    logger.info(f"Starting RAG-KB backend in {settings.app_env} mode")
    yield
    logger.info("Shutting down RAG-KB backend")


app = FastAPI(
    title="RAG-KB API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS：开发期允许前端本地访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
        },
    )


app.include_router(api_router)
```

### 4.8 `backend/tests/conftest.py`

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
```

### 4.9 `backend/tests/api/test_health.py`

```python
from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "app_env" in data
    assert "version" in data


def test_app_exception_handler(client: TestClient) -> None:
    """验证全局异常 handler 工作。可以临时加一个会抛 AppException 的端点测试，
    完成后删除该测试端点。"""
    # 此测试可选：如不易实现，跳过即可
    pass
```

### 4.10 `backend/.python-version`

```
3.13
```
（或 `3.14`，与本机版本一致）

### 4.11 `backend/README.md`

简短的本模块说明：
- 启动命令
- 测试命令
- 目录说明

---

## 5. 验收标准（Definition of Done）

执行 Codex 时按顺序检查以下项，全部通过才算完成：

### 5.1 安装与启动
- [ ] `cd backend && uv sync` 成功，无错误
- [ ] `cd backend && uv run uvicorn app.main:app --reload --port 8000` 能起来
- [ ] 控制台日志格式正确（loguru 格式，非 Python 默认格式）
- [ ] 看到日志："Starting RAG-KB backend in development mode"

### 5.2 接口验证
- [ ] `curl http://localhost:8000/api/v1/health` 返回 200
- [ ] 响应 JSON 包含 `status`、`app_env`、`version` 三个字段
- [ ] `curl http://localhost:8000/docs` 能打开 OpenAPI Swagger UI

### 5.3 配置加载
- [ ] 删除 `.env` 中 `LLM_API_KEY` 后启动，应抛 ValidationError 拒绝启动
- [ ] `.env` 中 `APP_LOG_LEVEL=DEBUG` 时日志级别真的变 DEBUG
- [ ] `config.yaml` 修改 `chunk_size: 1000` 后，settings.chunk_size 真的等于 1000

### 5.4 工具链
- [ ] `cd backend && uv run pytest -v` 全绿，至少 1 个测试通过
- [ ] `cd backend && uv run ruff check .` 无错误
- [ ] `cd backend && uv run ruff format --check .` 已格式化
- [ ] `cd backend && uv run mypy app` 无错误

### 5.5 CLAUDE.md 铁律合规
- [ ] `grep -r "print(" backend/app/` 无任何 print 调试
- [ ] `grep -rE "import logging$" backend/app/` 无 stdlib logging（应该全用 loguru）
- [ ] `grep -rE "from openai|import dashscope" backend/app/` 无任何（本任务不该涉及模型）
- [ ] 所有 endpoint 都是 `async def`
- [ ] 没有硬编码 URL / 端口 / 模型名

### 5.6 Git
- [ ] 在分支 `feat/W1-D3-18-fastapi-skeleton`
- [ ] commit message：`feat: add FastAPI skeleton with config/logging/exceptions\n\nRefs: #18`
- [ ] 推送到远端 + 创建 PR 到 main

---

## 6. 禁止事项

- ❌ 不要装与本任务无关的依赖（如 sqlalchemy / qdrant-client / llama-index）——那些是后续任务
- ❌ 不要写任何业务逻辑（Agent / 检索 / 模型调用）
- ❌ 不要在 `app/main.py` 里写超过 50 行业务代码（保持骨架精简）
- ❌ 不要用 `print()` 调试
- ❌ 不要硬编码 `host="0.0.0.0"` / `port=8000` 等（用 settings）
- ❌ 不要为了"看起来更完整"添加未被要求的功能（YAGNI）

---

## 7. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| 用 `os.getenv()` 读配置 | 绕过 pydantic 校验 | 必须走 `settings.xxx` |
| `print()` 调试 | 违反 CLAUDE.md | 用 `loguru.logger.debug(...)` |
| 同步定义 endpoint（`def`） | 异步框架性能损失 | 全部 `async def` |
| 异常 handler 漏注册 | 自定义异常返回 500 | `@app.exception_handler(AppException)` |
| `.env` 路径找不到 | 启动报 missing field | 用绝对路径或 `parents[N]` 精确定位 |
| ruff format 没跑 | CI 失败 | 提交前 `uv run ruff format .` |
| pydantic v1 写法（`Config` class）| 报警告 | 用 v2 的 `model_config = SettingsConfigDict(...)` |

---

## 8. 完成后请汇报

按以下格式回报，便于下一轮任务衔接：

```
## 任务 #18 完成报告

### 跑通情况
- uv sync: ✅ / ❌（耗时多少秒）
- uvicorn 启动: ✅ / ❌
- /health 响应: ✅ / ❌（贴一下 JSON 输出）
- pytest: ✅ / ❌（多少个测试，多少通过）
- ruff check: ✅ / ❌
- mypy: ✅ / ❌

### 实际生成的文件
（列出全部新建/修改的文件路径）

### 与 spec 的偏差
（如有任何偏离 spec 的地方，说明原因；没有就写"无"）

### Git 状态
- 分支：feat/W1-D3-18-fastapi-skeleton
- commit hash：xxx
- PR 链接：xxx（如已创建）

### 遇到的问题
（如有解决方案，一并说明）
```

---

## 9. 参考资料

- 项目内：`CLAUDE.md`（开发规范）、`.env.example`、`config.yaml`
- FastAPI 官方：https://fastapi.tiangolo.com/
- pydantic-settings：https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- loguru：https://loguru.readthedocs.io/
- uv：https://docs.astral.sh/uv/

---

_本 spec 版本：v1.0 | 任务 ID：#18 | 最后更新：2026-06-03_
