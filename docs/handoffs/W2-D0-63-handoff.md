# Handoff: 任务 #63 - 切换对象存储 MinIO 到 RustFS

> 执行者：Codex
> 完成日期：2026-06-05
> 分支：feat/W2-D0-63-rustfs-migration
> PR：#10
> PR URL：https://github.com/Ruidooww/rag-kb/pull/10

---

## 0. TL;DR

总评：NEEDS_REVIEW。

本任务已把底层对象存储从 MinIO 切换到 RustFS，并新增 `backend/app/services/storage.py` 作为唯一 S3 兼容存储抽象入口。Docker 4 个服务已全部 healthy；RustFS integration 测试 `5 passed`；非 integration 回归 `15 passed, 16 deselected`；coverage `67%`，高于当前 CI 60% 门槛。

需要审查者关注的触发项：D4 修改超过 5 个已有文件，D5 新增 `boto3`/`botocore`，D6 修改 `backend/app/core/config.py` 核心配置层。风险评估：中低，改动集中在存储底座和配置字段迁移，没有实现 Agent，也没有让业务代码直接依赖 boto3。

RustFS healthcheck 与 spec 有明确偏离：实测 `/minio/health/live` 返回 `403 AccessDenied`，已按审查者授权改为访问 S3 根路径 `/` 并接受 `200/403`。

---

## 1. 任务概述

任务 #63 的目标是把本地 RAG 基础设施中的对象存储从 MinIO 替换为 RustFS，同时在后端新增对象存储抽象层，为 Phase 2 的双轨入库和后续文件下载/预签名 URL 做准备。

本轮没有实现任何 Agent，也没有把对象存储接入现有 RAG 查询链路；业务侧后续只应通过 `get_storage()` 或后端 REST API 使用文件能力。

---

## 2. 完成清单

- [x] `docker-compose.yml`：删除 `minio` 服务，新增 `rustfs` 服务。
- [x] `.env.example`：`MINIO_*` 字段迁移为 `STORAGE_*`。
- [x] `backend/app/core/config.py`：新增 `storage_*` 配置字段并移除 `minio_*`。
- [x] `backend/app/services/storage.py`：新增 `DocumentStorage`、`S3CompatibleStorage`、`StorageError`、`get_storage()`。
- [x] `backend/tests/services/test_storage.py`：新增 5 个 RustFS integration 测试。
- [x] `data/rustfs/`：本地已创建，目录被 `data/` gitignore 覆盖，不提交。
- [x] `docs/STACK_UPDATE_V2.2.md`：追加 MinIO 到 RustFS 技术栈调整说明。
- [x] `docs/CODEX_QUICK_REF.md`：追加 RustFS 对象存储速查章节。
- [x] `backend/pyproject.toml` / `backend/uv.lock`：新增 `boto3`、`botocore`。
- [x] `docs/tasks/W2-D0-63-rustfs-migration.md`：补入本任务 spec，便于 PR 审查追踪。

额外同步：

- [x] `.github/workflows/self-review.yml`：CI env 从 `MINIO_*` 改为 `STORAGE_*`，否则配置加载会失败。
- [x] `backend/scripts/docx-build/arch_part3.js`：旧架构文档生成脚本中的 `MINIO_ENDPOINT` 示例改为 `STORAGE_ENDPOINT`。
- [x] `backend/tests/services/test_llm.py`：配置加载测试从 `MINIO_*` 改为 `STORAGE_*`。

---

## 3. 与 Spec 的偏差

偏差 1：RustFS healthcheck 从 `GET /minio/health/live` 改为 `GET /` 接受 `200/403`。

- 偏离点：spec §4.1 示例使用 `curl -f http://localhost:9000/minio/health/live`。
- 原因：实测 `/minio/health/live` 返回 `403 AccessDenied`，该端点是 MinIO 私有 health 端点；RustFS 不提供 MinIO 风格的私有 health endpoint。
- 处理：按审查者授权，将 `docker-compose.yml:57-64` 改为 S3 根路径探活：`curl -s -o /dev/null -w '%{http_code}' http://localhost:9000/ | grep -qE '^(200|403)$'`。
- 影响：仅影响 Docker healthcheck；业务代码通过 S3 API 正常访问，不受影响。
- 后续：跟踪 RustFS 官方 release notes，如未来暴露 `/health` 或 `/ready`，再切回 `curl -f` 标准探活。
- Commit：`e435b97`

偏差 2：同步修改 `.github/workflows/self-review.yml`。

- 偏离点：spec §4 输出文件清单未列 CI workflow。
- 原因：`Settings` 已从 `minio_*` 改为必填 `storage_*`，CI 的 pytest env 如果保留 `MINIO_*` 会导致配置加载失败。
- 影响：只影响 CI 环境变量，不改变业务运行逻辑。
- Commit：`e435b97`

偏差 3：同步修改 `backend/scripts/docx-build/arch_part3.js`。

- 偏离点：spec §4 输出文件清单未列该旧架构文档生成脚本。
- 原因：自检 `MINIO_` 扫描命中该脚本的旧示例，后续如果重新生成架构文档会继续输出旧 MinIO 配置。
- 影响：仅更新文档生成脚本中的 ASCII 示例字符串，不影响 Python 后端或运行时。
- Commit：`e435b97`

---

## 4. 本地验收结果

| 项目 | 结果 | 备注 |
|------|------|------|
| `docker compose pull` | 通过 | `rustfs/rustfs:latest` 拉取成功 |
| `docker compose up -d --remove-orphans` | 通过 | `rag-minio` 已移除，`rag-rustfs` 已创建 |
| `docker compose ps` | 通过 | 4 个服务均 healthy |
| RustFS S3 API | 通过 | `curl http://localhost:9000/` 返回 XML `403 AccessDenied`，说明 S3 API 可达 |
| RustFS Console | 通过 | `curl http://localhost:9001/` 返回 XML `403 AccessDenied`，端口可达 |
| Qdrant health | 通过 | `curl http://localhost:6333/healthz` 返回 `200 OK` |
| Infinity health | 通过 | `curl http://localhost:8080/health` 返回 `200 OK` |
| Postgres readiness | 通过 | `pg_isready -U rag` 返回 `accepting connections` |
| `uv sync` | 通过 | `Resolved 125 packages`, `Checked 123 packages` |
| storage integration | 通过 | `5 passed, 1 warning in 18.79s` |
| 非 integration 回归 | 通过 | `15 passed, 16 deselected, 2 warnings in 19.61s` |
| coverage | 通过 | `TOTAL 412 statements, 67%` |
| `ruff check` | 通过 | `All checks passed!` |
| `ruff format --check` | 通过 | `33 files already formatted` |
| `mypy app` | 通过 | `Success: no issues found in 20 source files` |
| `python -c "from app.services.storage import ..."` | 通过 | `storage import ok` |
| `python -c "import app.main"` | 通过 | `import app.main ok` |
| `uv pip check` | 通过 | `All installed packages are compatible` |
| `boto3`/`botocore` license | 通过 | `Apache-2.0` |

关键命令输出摘录：

```text
docker compose ps
rag-infinity   Up 12 minutes (healthy)
rag-postgres   Up 12 minutes (healthy)
rag-qdrant     Up 12 minutes (healthy)
rag-rustfs     Up 8 minutes (healthy)
```

```text
uv run pytest tests/services/test_storage.py -v
tests/services/test_storage.py::test_save_and_load_roundtrip PASSED
tests/services/test_storage.py::test_exists_for_missing_key_returns_false PASSED
tests/services/test_storage.py::test_delete_removes_file PASSED
tests/services/test_storage.py::test_get_presigned_url_returns_http_url PASSED
tests/services/test_storage.py::test_storage_error_on_invalid_endpoint PASSED
5 passed
```

```text
uv run pytest -v -m "not integration" --cov=app --cov-report=term-missing --cov-report=xml
15 passed, 16 deselected
TOTAL 412 138 67%
```

---

## 5. 已知问题 / 风险

新增依赖：

- `boto3>=1.43.22`：S3-compatible SDK，用于访问 RustFS。
- `botocore>=1.43.22`：`boto3` 底层依赖，也显式引入以使用 `botocore.client.Config` 和异常类型。
- License：二者均为 `Apache-2.0`。
- 风险：`boto3` 是同步 SDK，本实现已用 `anyio.to_thread.run_sync` 包装所有对象操作，避免在 async API 内直接阻塞 event loop。

已知风险：

- `docker-compose.yml:48-49` 使用本地默认凭据 `rustfsadmin` / `rustfsadmin-please-change-me`，只适合本地开发；Phase 2 前应替换为安全凭据。
- `backend/app/main.py:31` 仍有历史硬编码 CORS origin `http://localhost:3000`，不是本轮新增。
- `backend/app/services/storage.py:60-70` 在构造 `S3CompatibleStorage` 时会同步执行 `_ensure_bucket()`；当前用于最小实现和测试可接受，后续高并发场景可考虑延迟初始化或生命周期管理。
- `docs/RAG知识库_任务清单.md` 和旧 task spec 仍包含 `MINIO_` 历史文本，属于 archive/history，不是运行时配置。

---

## 6. 给审查者的提示

- 重点 1：请先看 `docker-compose.yml:42-64`，确认 `rustfs` 服务替换和 healthcheck 偏离是否符合审查者授权。
- 重点 2：请看 `backend/app/services/storage.py:29-54` 的 `DocumentStorage` async 抽象，以及 `storage.py:57-168` 的 S3-compatible 实现；业务代码只有这里允许 `import boto3`。
- 重点 3：请看 `backend/tests/services/test_storage.py:14-61`，5 个 integration 测试覆盖 save/load、missing exists、delete、presigned URL、invalid endpoint。
- 重点 4：请确认 `.github/workflows/self-review.yml:67-72` 已从 `MINIO_*` 切到 `STORAGE_*`，否则 PR CI 的配置加载会失败。
- 重点 5：`backend/scripts/docx-build/arch_part3.js` 只是架构文档生成脚本；本轮只改 ASCII 存储示例，未处理该文件已有中文乱码。

---

## 7. 给下一轮的提示

- RustFS 已部署，本地 Web Console/API 端口为 `http://localhost:9001` / `http://localhost:9000`；当前匿名访问返回 `403 AccessDenied` 是正常 S3 行为。
- 存储抽象入口是 `backend/app/services/storage.py:166` 的 `get_storage()`；业务层不要直接 new boto3 client。
- bucket 名从 `settings.storage_bucket` 读取，默认 `rag-documents`，字段定义在 `backend/app/core/config.py:29-34`。
- 预签名 URL 已可通过 `await get_storage().get_presigned_download_url(doc_id)` 生成，测试见 `backend/tests/services/test_storage.py:44-54`。
- Phase 2 的 #28 双轨入库可以把原文档 bytes 写入 `get_storage().save(doc_id, content, content_type=...)`，返回 `s3://rag-documents/documents/{doc_id}`。
- 默认凭据 `rustfsadmin-please-change-me` 只用于本地开发；进入 Phase 2 前应按 #61 backlog 换成非默认 secret。
- 后续如果 RustFS 官方提供 `/health` 或 `/ready`，把 `docker-compose.yml:57-64` 改回 `curl -f` 风格的标准 healthcheck。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|----|------|------|
| A1 pytest | 通过 | `15 passed, 16 deselected`; storage integration `5 passed` |
| A1 coverage | 通过 | `TOTAL 412 statements, 67%`, 高于 CI 60% |
| A2 ruff/mypy | 通过 | `ruff check`: All checks passed; `ruff format --check`: 33 files already formatted; `mypy`: no issues |
| A3 七条铁律 + 敏感词 grep | 通过 | `print(`、`import logging`、`from openai/import dashscope` 无输出；`import boto3` 仅 `backend/app/services/storage.py:8` |
| A4 spec §4 文件 | NEEDS_REVIEW | spec 要求文件已完成；额外同步 CI workflow、docx-build 脚本和 task spec，见 §3 |
| A5 依赖安全 | 通过 | `uv pip check` 通过；`boto3`/`botocore` license `Apache-2.0` |
| A6 commit message | 通过 | `feat: switch object storage to RustFS` + `Refs: #63` |
| A7 Handoff 完整性 | 通过 | 本文件包含 §0-§8 和 `last_verified_commit` |
| A8 CI 复现 | 通过 | `self-review pass`, https://github.com/Ruidooww/rag-kb/actions/runs/26989916306/job/79647672394 |

### Part B 软指标

**B1 错误处理**：

外部 S3/RustFS 调用失败时不会吞错，会统一转换为 `StorageError` 并保留异常链。不存在 `except: pass` 或 `except Exception: pass`，扫描无输出。所有新增 except 块如下：

```text
backend/app/services/storage.py:75  except ClientError as exc -> no such bucket 创建，否则 raise StorageError from exc
backend/app/services/storage.py:80  except BotoCoreError as exc -> raise StorageError from exc
backend/app/services/storage.py:106 except (BotoCoreError, ClientError) as exc -> save 失败 raise StorageError from exc
backend/app/services/storage.py:121 except ClientError as exc -> missing key raise StorageError / other raise StorageError
backend/app/services/storage.py:125 except BotoCoreError as exc -> load 失败 raise StorageError from exc
backend/app/services/storage.py:134 except (BotoCoreError, ClientError) as exc -> delete 失败 raise StorageError from exc
backend/app/services/storage.py:142 except ClientError as exc -> missing key 返回 False，否则 raise StorageError from exc
backend/app/services/storage.py:146 except BotoCoreError as exc -> exists 失败 raise StorageError from exc
backend/app/services/storage.py:162 except (BotoCoreError, ClientError) as exc -> presign 失败 raise StorageError from exc
```

**B2 偏差**：

详见 §3，共 3 条偏差：RustFS healthcheck endpoint 调整、CI env 同步、旧 docx-build 生成脚本存储示例同步。

**B3 安全**：

`STORAGE_SECRET_KEY` 在 `.env.example` 中仍是本地占位开发值，不是真实生产 secret。`storage.py` 不记录 access key 或 secret key，异常消息只包含 bucket/doc id。扫描 `logger..*api_key|print.*api_key` 无输出；API key/手机号/身份证/大金额敏感扫描无输出。

**B4 性能与副作用**：

外部 IO 位置：

```text
backend/app/services/storage.py:74  head_bucket
backend/app/services/storage.py:78  create_bucket
backend/app/services/storage.py:99  put_object
backend/app/services/storage.py:116 get_object
backend/app/services/storage.py:120 body.read
backend/app/services/storage.py:132 delete_object
backend/app/services/storage.py:140 head_object
backend/app/services/storage.py:155 generate_presigned_url
```

`boto3` 同步调用均通过 `anyio.to_thread.run_sync` 包装；没有新增 `@lru_cache` 缓存有副作用的 client。当前 `S3CompatibleStorage.__init__` 会做 bucket 检查/创建，后续可改成应用生命周期初始化。

**B5 可测性**：

公共函数/方法到测试映射：

```text
S3CompatibleStorage.save -> tests/services/test_storage.py:test_save_and_load_roundtrip
S3CompatibleStorage.load -> tests/services/test_storage.py:test_save_and_load_roundtrip
S3CompatibleStorage.exists -> tests/services/test_storage.py:test_exists_for_missing_key_returns_false, test_delete_removes_file
S3CompatibleStorage.delete -> tests/services/test_storage.py:test_delete_removes_file
S3CompatibleStorage.get_presigned_download_url -> tests/services/test_storage.py:test_get_presigned_url_returns_http_url
S3CompatibleStorage invalid endpoint -> tests/services/test_storage.py:test_storage_error_on_invalid_endpoint
get_storage -> tests/services/test_storage.py uses it in 4 integration tests
```

这些测试被标为 `pytestmark = pytest.mark.integration`，不会在无 RustFS 的 CI 非 integration 步骤误跑。

**B6 配置合规**：

`os.getenv` / `os.environ` 在 `backend/app` 扫描无输出。新增存储配置全部在 `backend/app/core/config.py:29-34`，`.env.example:31-36` 同步了 `STORAGE_*`，CI env 也在 `.github/workflows/self-review.yml:67-72` 同步。

已知历史项：`backend/app/main.py:31` 仍有 `http://localhost:3000` CORS hardcode，不是本轮新增。

**B7 并发与线程安全**：

新增 `DocumentStorage` 和 `S3CompatibleStorage` 暴露 async 方法：`storage.py:31-54`、`storage.py:89-163`。阻塞调用扫描 `time.sleep|requests.get|requests.post` 在源码范围无输出。新增共享状态仅 `_client` 和 `_bucket` 实例字段，没有 module global mutable cache。

**B8 下一轮暗坑**：

- `docker-compose.yml:57-64` 的 healthcheck 接受 `403` 是刻意设计；不要误改回 `/minio/health/live`。
- `backend/app/services/storage.py:60-70` 初始化时会访问 RustFS 并确保 bucket；如果下一轮在 request hot path 高频创建 storage，应考虑生命周期持有或轻量工厂。
- `backend/app/services/storage.py:83-87` 会把所有 doc id 放到 `documents/` 前缀下；#28 双轨入库如果已有路径前缀，需避免重复拼接。

### Part C 陷阱核查（18 项）

- C1 通过：`print(` 扫描无输出。
- C2 通过：`import logging` 扫描无输出。
- C3 NEEDS_REVIEW：本轮新增配置无硬编码 secret；但历史 `backend/app/main.py:31` 仍硬编码 CORS origin。
- C4 通过：`# type: ignore` 扫描无输出。
- C5 通过：`except: pass` / `except Exception: pass` 扫描无输出。
- C6 通过：新增异常均使用 `raise StorageError(...) from exc`。
- C7 通过：S3 IO 使用 `to_thread.run_sync` 包装；没有新增文件句柄泄漏。
- C8 通过：没有给 `get_storage()` 或 S3 client 加 `@lru_cache`。
- C9 通过：新增公共存储接口全部为 `async def`。
- C10 通过：源码范围 `time.sleep|requests.get|requests.post` 扫描无输出。
- C11 通过：配置走 `settings`，无散落 `os.getenv()`。
- C12 通过：新增环境变量已加入 `.env.example`。
- C13 通过：本轮新增的是环境型存储连接参数，无新增 `config.yaml` 业务参数。
- C14 通过：新增依赖已在 §5 说明。
- C15 通过：storage integration 测试真实调用本地 RustFS；非 integration CI 不伪造真实服务。
- C16 通过：新增公共存储方法均有对应测试。
- C17 通过：`uv run python -c "import app.main"` 通过。
- C18 通过：无删除/重命名现有公共 API；配置字段迁移已同步测试和 CI env。

ANTIPATTERNS 对照结果：

- 已检查反模式：A1、B1、C1、D1、E1、F1。
- 命中并规避：B1，新增异常链均 `raise ... from exc`；C1，无散落 `os.getenv`；E1，未缓存 S3 client 工厂；F1，本任务依赖清单和实现一致，仅引入 `boto3`/`botocore`。
- 未处理历史项：D1 仍是 #18 历史测试隔离问题，不属于本轮新增。

### Part D 人工触发

- D1-D3 代码量：新增非文档/非 lock 行约 319 行，其中核心新增代码约 245 行；小于 600，代码量通过。
- D4 修改已有文件数：10 个 main 上已有文件，触发 NEEDS_REVIEW。
- D5 新增依赖：`boto3`、`botocore`，Apache-2.0，触发 NEEDS_REVIEW。
- D6 核心抽象改动：是，修改 `backend/app/core/config.py`，触发 NEEDS_REVIEW。
- D7 公共 API 删改：否。
- D8 Part A 失败：否；A8 待最终 CI 确认。
- D9 Part C 失败：无新增失败；历史 C3 已标注 NEEDS_REVIEW。
- D10 覆盖率下降：当前 67%，高于 60% CI 门槛；未做 main baseline 对比。
- D11 偏差数：3 条，达到但未超过 3。

### Part E 自我反思

**E1 三个改进点**：

1. 当前 `S3CompatibleStorage.__init__` 在 `backend/app/services/storage.py:60-70` 里创建 client 并立即 `_ensure_bucket()`。如果重做，会考虑把 bucket 初始化放到应用启动或显式 `ensure_ready()`，减少 request hot path 构造副作用。本轮没改是因为 spec 明确要求 `_ensure_bucket` 幂等创建，且当前还没有业务 API 高频调用 storage。
2. 当前 healthcheck 在 `docker-compose.yml:57-64` 用 `403` 判活。更理想方式是 RustFS 官方提供标准 `/health` 或 `/ready` 后改回 `curl -f`。本轮没改是因为实测 RustFS 当前镜像对 MinIO 私有 endpoint 返回 `403`，审查者已授权 S3 根路径探活。
3. 当前 integration tests 在 `backend/tests/services/test_storage.py:14-61` 每个测试都重新 `get_storage()` 并触发 bucket 检查。重做时可以加 fixture 复用 storage 实例并统一清理测试对象。本轮保持简单，是为了减少测试共享状态和隐藏顺序依赖。

**E2 忠告**：

- S3-compatible 不等于兼容 MinIO 的所有私有 endpoint。切 RustFS 时要把健康检查、控制台入口、S3 API 兼容性分开验证，不能只沿用 `/minio/health/live`。

**E3 新发现反模式**：

- 候选反模式：把 S3 API 兼容误认为 MinIO 私有管理/健康端点兼容。
- 错误范例：`curl -f http://localhost:9000/minio/health/live` 用于非 MinIO S3-compatible 服务。
- 正确范例：优先使用该服务官方 health endpoint；没有官方 endpoint 时，用明确授权的 API 可达性探活并在 Handoff 说明。
- 本轮未追加 `docs/ANTIPATTERNS.md`，因为该规则目前只在 RustFS healthcheck 场景出现，建议审查者确认后作为 `A2` 或 `F2` 追加。

### 修复轨迹

- fix_attempt:1 (working tree before commit) - RustFS `/minio/health/live` 返回 `403 AccessDenied`，按审查者授权改为 S3 根路径 `200/403` 探活，重跑 Docker 后 4 services healthy。
- fix_attempt:2 (working tree before commit) - 本地 `.env` 曾被 PowerShell 反引号污染，修复本地 `.env` 换行后 storage integration 从 4 failed 变为 5 passed；`.env` 未提交。

### 总评

NEEDS_REVIEW

原因：本地功能和质量门禁通过，但 Part D 触发 D4/D5/D6，且 healthcheck 有审查者授权的 spec 偏离。建议审查者重点看 §3、§5、§6。

last_verified_commit: e435b97
