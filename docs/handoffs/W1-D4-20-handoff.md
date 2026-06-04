# Handoff: 任务 #20 - 最小 RAG Pipeline 跑通

> **执行者**：Codex
> **完成日期**：2026-06-04
> **分支**：feat/W1-D4-20-min-rag-pipeline
> **PR**：#5
> **基于**：W1-D3-19-handoff.md

---

## 0. TL;DR（审查者 30 秒速读）

⚠️ **总评**：NEEDS_REVIEW（需关注但可合并）

### 关键数据

- 新增代码：790 行（排除 `uv.lock`；实现约 350 行 / 测试与 fixtures 约 440 行）
- 覆盖率：74%（`uv run pytest -v -m "not integration" --cov=app ...`）
- 偏差：2 条
- Self-review：A=✅ B=✅ C=18/18 ✅（含 2 个 #18 遗留提示）D=⚠️ E=✅
- fix_attempt 次数：0
- 端到端入库：5 docs → 6 chunks，Qdrant `rag_chunks` collection count = 6

### 触发原因

- D6：改动 `backend/app/core/config.py` / `backend/app/core/exceptions.py`，但只是按 spec 追加 `qdrant_collection` 和 `VectorStoreError`，不是核心抽象重构。
- D2 Soft：新增 790 行，属于本任务“5 docs + pipeline + API + tests”的合理范围。

### 风险评估

低：本轮以增量追加为主，未删除公共 API；真实 LLM API key 缺失导致 `/query` 的生成答案整测按既有规则 skip。

### 最大亮点

最小 RAG 链路已跑通到 `ingest → embedding → Qdrant → retrieve`，并提供 `/api/v1/query` API 与可复现测试 fixtures。

### 给审查者的 3 个看点

1. `backend/app/services/rag_pipeline.py:19` 到 `backend/app/services/rag_pipeline.py:93`：核心 ingest/retrieve/generate 三段链路。
2. `backend/app/services/qdrant_store.py:24` 到 `backend/app/services/qdrant_store.py:85`：Qdrant collection/upsert/query 封装和异常链。
3. `backend/tests/services/test_rag_pipeline.py:45` 到 `backend/tests/services/test_rag_pipeline.py:146`：integration 与 unit 分层，以及脚本入口回归测试。

---

## 1. 任务概述

本任务实现了最小 RAG Pipeline：将 5 份中文测试文档切片、向量化并写入 Qdrant，再通过检索、rerank fallback 和 LLM prompt 入口支撑 `/api/v1/query`。实现遵循 #19 的模型抽象层，业务代码只调用 `get_llm()`、`get_embedding()`、`get_reranker()`，Qdrant 直接使用底层 `qdrant-client` SDK，避免引入不必要的 VectorStore 抽象。

---

## 2. 完成清单（对应 spec §4）

- [x] `backend/tests/fixtures/sample_docs/product_x_manual.md`
- [x] `backend/tests/fixtures/sample_docs/faq_general.md`
- [x] `backend/tests/fixtures/sample_docs/customer_case_acme.md`
- [x] `backend/tests/fixtures/sample_docs/team_handbook.md`
- [x] `backend/tests/fixtures/sample_docs/release_notes_v2.md`
- [x] `backend/app/models/query.py`
- [x] `backend/app/services/qdrant_store.py`
- [x] `backend/app/services/rag_pipeline.py`
- [x] `backend/app/prompts/base_qa.txt`
- [x] `backend/app/api/query.py`
- [x] `backend/app/api/router.py`
- [x] `backend/app/core/exceptions.py`
- [x] `backend/app/core/config.py`
- [x] `backend/scripts/ingest_test_docs.py`
- [x] `backend/tests/services/test_qdrant_store.py`
- [x] `backend/tests/services/test_rag_pipeline.py`
- [x] `backend/tests/api/test_query.py`
- [x] `backend/tests/agents/__init__.py`
- [x] `backend/pyproject.toml`
- [x] `backend/uv.lock`
- [x] `docs/ANTIPATTERNS.md`（§8 E3 产出，追加 F1）

---

## 3. 与 Spec 的偏差

- **偏差 1**：Spec §4.11 误列 `llama-index-vector-stores-qdrant`
  - Spec 原文：`uv add qdrant-client llama-index-core llama-index-vector-stores-qdrant`
  - 实际实现：仅保留 `qdrant-client`；`llama-index-core` 已是既有依赖，未重复引入；未安装 `llama-index-vector-stores-qdrant`
  - 理由：Spec §4.3 要求 `qdrant_store.py` 直用 `qdrant-client` SDK；`llama-index-vector-stores-qdrant` 与该实现路径冲突，且当前版本声明 `Python >=3.10, <3.14`，与项目 `backend/.python-version=3.14` 不兼容
  - Commit：`6368d38bac82715d40f8053e85baa5474220f62e`
  - 影响：降低依赖面，保持 Python 3.14；Qdrant 逻辑仍由 `qdrant-client.upsert()` / `query_points()` 完成
- **偏差 2**：触发 D6 / D2，但已由审查者预批准按 NEEDS_REVIEW 继续
  - Spec 原文：§4.7 要求追加 `VectorStoreError`，§4.8 要求追加 `qdrant_collection`
  - 实际实现：修改 `backend/app/core/exceptions.py:24` 和 `backend/app/core/config.py:28`
  - 理由：属于 spec 强制要求的增量字段/异常类，不是核心抽象重构；790 行新增来自 5 份 docs、pipeline、API 和测试，任务范围合理
  - Commit：N/A（审查者在 Step 8/9 前显式批准）
  - 影响：PR 总评标记为 NEEDS_REVIEW，审查者重点关注这两项即可

---

## 4. 本地验收结果

| 项目 | 结果 | 备注/原始输出 |
|------|------|--------------|
| uv sync | ✅ | `Resolved 102 packages` / `Checked 100 packages`，Python 3.14.5 |
| uv run pytest -v -m "not integration" | ✅ | `13 passed, 11 deselected, 2 warnings` |
| uv run pytest -v | ✅ | `20 passed, 4 skipped, 2 warnings` |
| 覆盖率 | ✅ | `TOTAL 316 Stmts / 83 Miss / 74%` |
| ruff check | ✅ | `All checks passed!` |
| ruff format --check | ✅ | `29 files already formatted` |
| mypy strict | ✅ | `Success: no issues found in 19 source files` |
| Part A3 grep（铁律+敏感词） | ✅ | `import dashscope` / `print(` / `import logging` / openai direct / hardcoded provider-model 均无命中 |
| commit message 规范 | ✅ | `feat: implement minimal RAG pipeline` + `Refs: #20` |
| 依赖安全 | ✅ | `uv pip check`: `All installed packages are compatible`; `qdrant-client 1.18.0`, License `Apache-2.0` |
| Docker 服务 | ✅ | `rag-infinity` / `rag-minio` / `rag-postgres` / `rag-qdrant` 均 `healthy` |
| Qdrant health | ✅ | `healthz check passed`, HTTP 200 |
| infinity health | ✅ | HTTP 200 |
| 入库脚本 | ✅ | 5 docs 入库，总计 6 chunks |
| Qdrant count | ✅ | `rag_chunks` collection count = 6 |
| retrieve 验证 | ✅ | 贴近安装问题最高 score = 0.55940914，sources 含 `product_x_manual` |
| CI workflow | ⏳ | PR #5 已创建；Handoff 提交后触发最终 CI |

### 关键命令原始输出

```text
uv run pytest -v -m "not integration"
13 passed, 11 deselected, 2 warnings in 13.98s
```

```text
uv run pytest -v -m "not integration" --cov=app --cov-report=term-missing --cov-report=xml
TOTAL 316 83 74%
Coverage XML written to file coverage.xml
```

```text
uv run pytest -v
20 passed, 4 skipped, 2 warnings in 74.39s (0:01:14)
```

```text
uv run ruff check .
All checks passed!

uv run ruff format --check .
29 files already formatted

uv run mypy app
Success: no issues found in 19 source files

uv pip check
All installed packages are compatible
```

```text
uv run python scripts/ingest_test_docs.py
customer_case_acme.md: 1 chunks
faq_general.md: 1 chunks
product_x_manual.md: 2 chunks
release_notes_v2.md: 1 chunks
team_handbook.md: 1 chunks
总计：6 chunks
```

---

## 5. 已知问题 / 风险

- 风险 1：本机 `LLM_API_KEY` 仍是占位值，真实云端 LLM 与百炼 rerank integration 用例被 skip
  - 影响范围：`POST /api/v1/query` 的真实答案生成没有在本机完成云端调用验收
  - 缓解措施：unit 测试覆盖 prompt 注入和 API 响应结构；retrieve/embedding/Qdrant 链路已真实跑通
- 风险 2：`retrieve()` 在 rerank 失败时 fallback 到向量检索顺序
  - 影响范围：占位 key 或 rerank 服务不可用时召回质量可能下降
  - 缓解措施：`backend/app/services/rag_pipeline.py:75` 只捕获 `LLMServiceError` 并记录 warning，不吞掉 Qdrant/embedding 错误
- 风险 3：两个 #18 遗留命中未在本任务修复
  - `backend/tests/api/test_health.py:20` 命中 `ANTIPATTERNS.md` D1
  - `backend/app/main.py:31` 仍有 hardcoded CORS origin

### 新增第三方依赖

- `qdrant-client==1.18.0`，License: Apache-2.0，用途：直接调用 Qdrant collection、upsert、query_points API

---

## 6. 给审查者的提示（至少 3 条）

- **重点 1**：`backend/app/services/rag_pipeline.py:24` 使用 `settings.qdrant_collection` 作为默认 collection，避免硬编码 `rag_chunks`；`ingest_file(..., collection=...)` 仅用于测试隔离。
- **重点 2**：`backend/app/services/qdrant_store.py:36` / `backend/app/services/qdrant_store.py:59` / `backend/app/services/qdrant_store.py:84` 均使用 `raise VectorStoreError(...) from exc` 保留异常链。
- **重点 3**：`backend/app/services/rag_pipeline.py:87` 每次读取 `prompts/base_qa.txt`，没有 inline 长 prompt，也没有内存缓存 prompt。
- **重点 4**：`backend/tests/api/test_health.py:20` 命中 `ANTIPATTERNS.md` D1（测试共享 app router）。这是 #18 遗留，建议加 backlog 任务清理。
- **重点 5**：`backend/app/main.py:31` 硬编码 CORS origin `"http://localhost:3000"`。这是 #18 遗留，建议加 backlog 任务移到 `settings.cors_origins`。

---

## 7. 给下一轮（#21 Ollama 切换）的提示

- **上下文 1**：入库入口在 `backend/scripts/ingest_test_docs.py:19`，运行方式是 `cd backend && uv run python scripts/ingest_test_docs.py`。
- **上下文 2**：查询入口在 `backend/app/api/query.py:12`，HTTP 路径是 `POST /api/v1/query`，请求模型见 `backend/app/models/query.py:4`。
- **上下文 3**：验证切换的最小步骤：改 `.env` 的 `LLM_BASE_URL` / `LLM_MODEL` → 重启后端 → 如 embedding 模型也切换则重跑 ingest 重新生成向量 → 重跑 query。
- **上下文 4**：Ollama 模式下需要特别处理 rerank；`gte-rerank-v2` 是百炼 rerank 能力，切本地后应禁用 rerank 或替换成本地 rerank 实现。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|----|------|------|
| A1 全项目 pytest | ✅ | `13 passed, 11 deselected`（CI 路径）；`20 passed, 4 skipped`（本地全量） |
| A2 静态检查 | ✅ | ruff check 0 errors；format 29 files already formatted；mypy 0 errors |
| A3 铁律+敏感词 grep | ✅ | `backend/app/` 无 `print(`、stdlib logging、dashscope import、直接 openai import、provider/model hardcode；API key pattern 无命中 |
| A4 spec §4 文件 | ✅ | §2 清单全部完成；未提交未跟踪 task spec |
| A5 依赖安全 | ✅ | `uv pip check` compatible；`qdrant-client` Apache-2.0；outdated: marshmallow/openai/pydantic-core/uvicorn |
| A6 commit message | ✅ | `feat: implement minimal RAG pipeline`，body 含 `Refs: #20` |
| A7 Handoff 完整性 | ✅ | §0-§8 已创建，含偏差、审查提示、下一轮提示和 `last_verified_commit` |
| A8 CI 复现 | ⏳ | PR #5 创建完成，Handoff commit push 后触发最终 CI |

### Part B 软指标

**B1 错误处理**：
外部调用失败不会静默吞掉。Qdrant 层将底层异常包装为 `VectorStoreError` 并保留异常链；pipeline 仅对 rerank 的 `LLMServiceError` 做降级，避免占位 key 阻断检索链路。

所有 except 块位置：
- `backend/app/services/qdrant_store.py:36`：`except Exception as exc` -> `raise VectorStoreError(...) from exc`
- `backend/app/services/qdrant_store.py:59`：`except Exception as exc` -> `raise VectorStoreError(...) from exc`
- `backend/app/services/qdrant_store.py:84`：`except Exception as exc` -> `raise VectorStoreError(...) from exc`
- `backend/app/services/rag_pipeline.py:75`：`except LLMServiceError as exc` -> log warning + return vector-order fallback
- 既有：`backend/app/services/llm.py:103` -> `raise LLMServiceError(...) from last_error`

无 `except: pass` 或 `except Exception: pass`。

**B2 偏差**：见 §3。

**B3 安全**：
敏感数据没有写入日志或响应。`logger` 只记录 rerank 失败消息 `backend/app/services/rag_pipeline.py:76`，不包含 API key；`Select-String "logger\..*api_key|print.*api_key"` 无命中。`qdrant_store` 不拼接 shell 命令，API 层只接收 Pydantic 校验后的 `QueryRequest`。

grep 证据：
- API key pattern：无命中
- `os.getenv|os.environ`：`backend/app/` 无命中
- hardcoded provider/model：无命中

**B4 性能**：
外部 IO 调用位置：
- `backend/app/services/rag_pipeline.py:25`：`Path.read_text` 通过 `asyncio.to_thread`
- `backend/app/services/rag_pipeline.py:35`：embedding batch 通过 `to_thread`
- `backend/app/services/rag_pipeline.py:50`：Qdrant ensure collection 通过 `to_thread`
- `backend/app/services/rag_pipeline.py:51`：Qdrant upsert 通过 `to_thread`
- `backend/app/services/rag_pipeline.py:58`：async embedding query
- `backend/app/services/rag_pipeline.py:59`：Qdrant query 通过 `to_thread`
- `backend/app/services/rag_pipeline.py:70`：rerank 通过 `to_thread`
- `backend/app/services/rag_pipeline.py:87`：prompt file read 通过 `to_thread`
- `backend/app/services/rag_pipeline.py:92`：LLM completion 通过 `to_thread`
- `backend/app/services/qdrant_store.py:26` / `45` / `74`：Qdrant SDK client operations

本任务未引入 client `@lru_cache`。最小版本未做批量 ingest 并发，避免过早优化。

**B5 可测性**：
公共函数→测试映射：
- `get_qdrant_client()` → `backend/tests/services/test_qdrant_store.py:17`
- `ensure_collection()` → `backend/tests/services/test_qdrant_store.py:27`
- `upsert_chunks()` → `backend/tests/services/test_qdrant_store.py:35`
- `search_chunks()` → `backend/tests/services/test_qdrant_store.py:35` / `backend/tests/services/test_qdrant_store.py:68`
- `ingest_file()` → `backend/tests/services/test_rag_pipeline.py:45` / `backend/tests/services/test_rag_pipeline.py:113`
- `retrieve()` → `backend/tests/services/test_rag_pipeline.py:52`
- `generate_answer()` → `backend/tests/services/test_rag_pipeline.py:62` / `backend/tests/services/test_rag_pipeline.py:94`
- `query()` endpoint → `backend/tests/api/test_query.py:21` / `backend/tests/api/test_query.py:41` / `backend/tests/api/test_query.py:47`

失败路径覆盖：unsupported file、Qdrant invalid URL、query validation、rerank failure fallback。真实 LLM 依赖用例在无 key 时 skip，没有 mock 假装真实生成成功。

**B6 配置合规**：
- `backend/app/core/config.py:28` 新增 `qdrant_collection`
- `backend/app/services/rag_pipeline.py:24` / `61` 使用 `settings.qdrant_collection`
- `backend/app/api/query.py:16` / `17` 使用 `settings.top_k` / `settings.rerank_n`
- `os.getenv|os.environ` grep：`backend/app/` 无命中
- hardcoded provider/model grep：无命中
- 既有 hardcoded URL：`backend/app/main.py:31` CORS origin，非 #20 新增

**B7 并发**：
async 函数列表：
- `backend/app/api/health.py:14`
- `backend/app/api/query.py:13`
- `backend/app/services/rag_pipeline.py:19`
- `backend/app/services/rag_pipeline.py:55`
- `backend/app/services/rag_pipeline.py:82`

同步阻塞调用在 async pipeline 中通过 `asyncio.to_thread` 包裹；`time.sleep` / `requests.get|post` grep 无命中。

**B8 下一轮暗坑**：
1. `backend/app/services/rag_pipeline.py:75`：rerank 失败会 fallback 到向量顺序，#21 切 Ollama 时要显式决定禁用 rerank 还是替换本地 rerank。
2. `backend/app/services/rag_pipeline.py:24`：ingest 默认 collection 来自 `settings.qdrant_collection`；#21 如果切换 embedding 模型，应重建或清空 collection，避免不同 embedding 模型向量混用。

### Part C 陷阱核查（18 项）

- C1 ✅ `backend/app/` 无 `print(`；脚本 print 位于 `backend/scripts/ingest_test_docs.py:24` / `26` 且有 `# noqa: T201`
- C2 ✅ 无 stdlib `import logging`
- C3 ✅ #20 新增代码无硬编码 URL/端口/模型名；既有 `backend/app/main.py:31` CORS hardcode 已在 §6 标注
- C4 ✅ 无 `type: ignore`
- C5 ✅ 无 `except: pass` 或 `except Exception: pass`
- C6 ✅ Qdrant 异常使用 `raise ... from exc`
- C7 ✅ Qdrant client 是短生命周期 SDK 对象；脚本无长期文件句柄；HTTP client 既有 `llm.py` 用 `with`
- C8 ✅ 本轮未给外部 client 工厂加 `@lru_cache`
- C9 ✅ API endpoint 是 `async def`
- C10 ✅ async 函数中阻塞 IO 用 `asyncio.to_thread`
- C11 ✅ 配置走 `settings`
- C12 ✅ 本轮未新增必填环境变量
- C13 ✅ 本轮新增业务参数 `qdrant_collection` 在 `Settings` 有默认值；未修改 `config.yaml`
- C14 ✅ 新依赖 `qdrant-client` 已在 §5 说明
- C15 ✅ 没有 mock 假装真实 LLM 成功；真实 LLM 无 key 时 skip
- C16 ✅ 公共函数有对应测试
- C17 ✅ `uv run python -c "import app.main"` 通过 mypy/import 路径验证覆盖
- C18 ✅ 新 endpoint 已在 `backend/app/api/router.py:5` 注册

ANTIPATTERNS 对照结果：
- 已检查反模式总数：6（A1/B1/C1/D1/E1/F1）
- 命中数：0（#20 新增代码）
- 既有命中 1：`backend/tests/api/test_health.py:20` 命中 D1，#18 遗留
- 既有命中 2：`backend/app/main.py:31` hardcoded CORS origin，#18 遗留
- 新增 F1：`docs/ANTIPATTERNS.md` 已追加“依赖列表与实现描述不一致”

### Part D 人工触发

- D1-D3 代码量：790 行 → D2 Soft；审查者已预批准，标记 NEEDS_REVIEW
- D4 修改已有文件数：实现 diff 5 个 main 既有文件；追加 `docs/ANTIPATTERNS.md` 后为 6 个，属于 §8 E3 产出，审查者已允许一起做
- D5 新增依赖：`qdrant-client`，Apache-2.0 → 通过
- D6 核心抽象改动：是，`backend/app/core/config.py` / `backend/app/core/exceptions.py` 仅追加字段/异常类，审查者已预批准
- D7 公共 API 删改：否
- D8 Part A 失败：否
- D9 Part C 失败：否（既有命中已标注为遗留）
- D10 覆盖率下降：未与 main coverage.xml 做精确对比；当前总覆盖率 74%，超过门槛
- D11 偏差数：2 → 通过

### Part E 自我反思

**E1 三个改进点**：
1. 当前 `backend/app/services/rag_pipeline.py:75` 对 rerank 失败采用 fallback。重做时会把 rerank 策略抽成可配置开关，例如 `settings.rerank_enabled`，让 Ollama 模式更清晰。本次没改是因为 #20 只要求最小链路，#21 才验证模型切换。
2. 当前 `backend/scripts/ingest_test_docs.py:12` 为直接执行脚本做了 `sys.path` bootstrap。重做时可以改为 `python -m scripts.ingest_test_docs` 或正式 CLI entrypoint，避免脚本内调整 import path。本次没改是因为 spec 明确要求 `uv run python scripts/ingest_test_docs.py`。
3. 当前 `backend/app/services/qdrant_store.py:24` 每次 ensure/upsert/search 都新建 Qdrant client。重做时可以引入显式生命周期管理的 client provider，但不能用 `@lru_cache` 缓存外部 client。本次没改是因为 `ANTIPATTERNS.md` E1 要求避免缓存 client，最小实现优先隔离和可测。

**E2 忠告**：
- 以后看到 spec 同时要求“底层 SDK 实现”和“高级抽象依赖”时，不要先安装依赖；先对照实现章节和 Python 版本约束，停下来确认。#20 已把这个写入 `ANTIPATTERNS.md` F1。

**E3 新发现反模式**：
- 反模式：依赖列表与实现描述不一致。
- 错误范例：Spec §4.3 要求直用 `qdrant-client`，§4.11 又要求安装 `llama-index-vector-stores-qdrant`。
- 正确范例：如果实现只调用 `qdrant-client.upsert/query_points`，依赖清单只保留 `qdrant-client`。
- 已追加到 `docs/ANTIPATTERNS.md`：F1。

### 修复轨迹

- 无 fix_attempt commit；实现阶段内修复了脚本入口和格式问题，并在首个代码 commit 前完成验证。

### 总评

⚠️ **NEEDS_REVIEW**（需关注但可合并）

last_verified_commit: 6368d38bac82715d40f8053e85baa5474220f62e
