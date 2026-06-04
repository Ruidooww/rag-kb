# Handoff: 任务 #21 - Ollama 切换演示（铁律 #7 验收）

> **执行者**：Codex  
> **完成日期**：2026-06-04  
> **分支**：feat/W1-D5-21-ollama-switch-demo  
> **PR**：#8  
> **PR URL**：https://github.com/Ruidooww/rag-kb/pull/8  
> **基于**：W1-D4-20-handoff.md / W1-D5-22-handoff.md

---

## 0. TL;DR

✅ **总评**：PASS（铁律 #7 验证通过）

### 关键结论

- 业务代码零改动：`backend/app/`、`backend/scripts/`、`backend/tests/` diff 全为空。
- `.env` 仅切换 3 个字段：`LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`。
- Ollama OpenAI-compatible endpoint 可用：`http://localhost:11434/v1`。
- 本机实际验证模型：`qwen2.5:3b`。
- `/api/v1/query` 在 Ollama 模式返回 HTTP 200，JSON 结构完整，`answer` 非空。
- `model_used=qwen2.5:3b`，证明模型名从配置读取。

### 关键数据

- Ollama query 耗时：`24.124022` 秒（curl total）。
- API 内部 `latency_ms=23904`。
- `answer_length=219`。
- `sources_count=5`。
- coverage：74%。
- `pytest -v`：`20 passed, 4 skipped, 2 warnings`。
- `pytest -v -m "not integration"`：`13 passed, 11 deselected, 2 warnings`。

### 风险 / 限制

百炼基线 query 返回 500，原因是原 `.env` 中 `LLM_API_KEY` 是中文 placeholder，OpenAI/httpx 组装 header 时报 `UnicodeEncodeError`。这不影响本任务结论：Ollama 模式通过，且业务代码零改动。

---

## 1. 任务概述

本任务验证迁移铁律 #7：业务代码不改，仅通过 `.env` 把 LLM 从百炼兼容端点切到本地 Ollama。实现产出包括 `.env.example` 的 Ollama 示例、`docs/migration-test.md` 真实迁移记录、#21 task spec，以及本 Handoff。

---

## 2. 完成清单

- [x] `.env` 本地临时切换到 Ollama，并在验证后恢复到百炼配置（未提交）
- [x] `.env.example` Ollama 示例更新为 `qwen2.5:3b`
- [x] `.env.example` Ollama 示例补充 `LLM_API_KEY=ollama-no-key-needed`
- [x] `docs/migration-test.md`
- [x] `docs/tasks/W1-D5-21-ollama-switch-demo.md`
- [x] `docs/handoffs/W1-D5-21-handoff.md`
- [x] 未修改任何 `.py` 文件
- [x] 未修改 `config.yaml`
- [x] 未修改 `docker-compose.yml`

---

## 3. 与 Spec 的偏差

- **偏差 1**：模型名从原 spec 示例 `qwen2.5:7b` 调整为 `qwen2.5:3b`。
  - 原因：本机实际可用模型经 `http://localhost:11434/api/tags` 验证为 `qwen2.5:3b`；用户已确认“qwen2.5”路线。
  - 处理：`docs/tasks/W1-D5-21-ollama-switch-demo.md`、`.env.example`、`docs/migration-test.md` 全部使用 `qwen2.5:3b`。
  - 影响：不影响铁律 #7 验收，反而与真实环境一致。
  - Commit：`d2131aa274bbcfa98b108c33a7e95ba84b0ad3b6`

- **偏差 2**：百炼基线和回滚后的 query 返回 500。
  - 原因：原 `.env` 中 `LLM_API_KEY` 是中文 placeholder：`sk-请填入你的百炼API_Key`，OpenAI/httpx header 只能接受 ASCII。
  - 处理：不修改业务代码，不提交 `.env`；在 `docs/migration-test.md` 中如实记录。Ollama 模式使用 ASCII 占位 `ollama-no-key-needed` 后返回 200。
  - 影响：无法做真实“百炼答案 vs Ollama 答案”质量对比，但不影响“业务代码零改动切到 Ollama”的核心验收。
  - Commit：`d2131aa274bbcfa98b108c33a7e95ba84b0ad3b6`

- **偏差 3**：PR #8 未触发 GitHub Actions checks。
  - 原因：`.github/workflows/self-review.yml` 当前只监听 `backend/**` 和 workflow 文件，本 PR 只改 `.env.example` 与 docs。
  - 处理：本地完整跑 pytest、coverage、ruff、format、mypy、pip check 和铁律扫描。
  - 影响：PR 页面没有 checks；审查者以本 Handoff §4 的本地验证结果为准。
  - Commit：`d2131aa274bbcfa98b108c33a7e95ba84b0ad3b6`

---

## 4. 本地验收结果

| 项目 | 结果 | 备注 |
|------|------|------|
| PR 状态 | ✅ | PR #8, `MERGEABLE / CLEAN` |
| Ollama API | ✅ | `http://localhost:11434/api/tags` 返回 `qwen2.5:3b` |
| Qdrant | ✅ | `rag_chunks.points_count=6`, HTTP 200 |
| backend health（Ollama） | ✅ | HTTP 200 |
| `/api/v1/query`（Ollama） | ✅ | HTTP 200 |
| `model_used` | ✅ | `qwen2.5:3b` |
| `answer` | ✅ | 非空，219 字符 |
| `sources` | ✅ | 5 个 |
| `latency_ms` | ✅ | 23904 |
| `git diff --stat backend/app/` | ✅ | 空 |
| `git diff --stat backend/scripts/` | ✅ | 空 |
| `git diff --stat backend/tests/` | ✅ | 空 |
| `git diff --check` | ✅ | 无实质错误；仅 PowerShell 输出 LF/CRLF warning |
| `pytest -v -m "not integration"` | ✅ | `13 passed, 11 deselected, 2 warnings` |
| `pytest -v` | ✅ | `20 passed, 4 skipped, 2 warnings` |
| coverage | ✅ | `TOTAL 316 83 74%` |
| ruff check | ✅ | `All checks passed!` |
| ruff format --check | ✅ | `29 files already formatted` |
| mypy | ✅ | `Success: no issues found in 19 source files` |
| uv pip check | ✅ | `All installed packages are compatible` |
| 铁律扫描 | ✅ | `print(` / logging / dashscope / 非 llm.py openai / Key pattern 均无命中 |
| GitHub checks | ⚠️ | docs/config-example PR 未触发 workflow |

### 关键命令输出

```text
curl meta
http_status=200
elapsed_total=24.124022
elapsed_ms_stopwatch=24152

response metrics
model_used=qwen2.5:3b
answer_length=219
sources_count=5
latency_ms=23904
```

```text
C:\Users\Ruidoww\.local\bin\uv.exe run pytest -v -m "not integration"
13 passed, 11 deselected, 2 warnings in 12.81s
```

```text
C:\Users\Ruidoww\.local\bin\uv.exe run pytest -v
20 passed, 4 skipped, 2 warnings in 60.12s (0:01:00)
```

```text
C:\Users\Ruidoww\.local\bin\uv.exe run pytest -v -m "not integration" --cov=app --cov-report=term-missing --cov-report=xml
TOTAL 316 83 74%
13 passed, 11 deselected, 2 warnings in 13.46s
```

```text
C:\Users\Ruidoww\.local\bin\uv.exe run ruff check .
All checks passed!

C:\Users\Ruidoww\.local\bin\uv.exe run ruff format --check .
29 files already formatted

C:\Users\Ruidoww\.local\bin\uv.exe run mypy app
Success: no issues found in 19 source files

C:\Users\Ruidoww\.local\bin\uv.exe pip check
All installed packages are compatible
```

---

## 5. 已知问题 / 风险

- `.env` 原百炼 API Key 是中文 placeholder，会导致百炼 query 500；需要后续填真实 Key 或改成 ASCII placeholder。
- `LLM_PROVIDER` 本轮未改，因为任务明确要求 `.env` 切换只改 3 个字段；当前业务代码实际调用由 `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY` 决定。
- Rerank 仍走百炼 `gte-rerank-v2`，在 Ollama 模式下失败后 fallback 到向量顺序，这是 #20 既有逻辑。
- `ollama` CLI 和 `docker` CLI 当前不在 PowerShell PATH；HTTP API 均可达，因此本轮通过 HTTP 验证。
- PR #8 未触发 checks，与 #22 的 docs-only PR 行为一致，建议 #60 统一处理 workflow path / A7 口径。

### 新增依赖

无。

---

## 6. 给审查者的提示

- **重点 1**：看 `docs/migration-test.md:459` 到 `docs/migration-test.md:468`，这里是铁律 #7 的核心验收结论。
- **重点 2**：看 `docs/migration-test.md:303` 到 `docs/migration-test.md:321`，这里记录了 Ollama query 的 HTTP 200、耗时、`model_used` 和 sources 数。
- **重点 3**：看 `.env.example:40` 到 `.env.example:43`，确认 Ollama 示例是 `qwen2.5:3b` 和 `ollama-no-key-needed`。
- **重点 4**：看 `backend/app/api/query.py:25`、`backend/app/services/llm.py:42` 到 `backend/app/services/llm.py:44`，`model_used` 和 LLM client 都来自 `settings`。
- **重点 5**：看 `docs/migration-test.md:162` 和 `docs/migration-test.md:451`，百炼 500 是 placeholder Key 编码问题，不是迁移逻辑问题。

---

## 7. 给后续任务的提示

- **上下文 1**：本轮迁移凭证在 `docs/migration-test.md`，可作为 Week 1 收官时铁律 #7 的验收材料。
- **上下文 2**：Ollama 切换 SOP 的三行是 `LLM_BASE_URL=http://localhost:11434/v1`、`LLM_MODEL=qwen2.5:3b`、`LLM_API_KEY=ollama-no-key-needed`。
- **上下文 3**：如果后续要做“百炼 vs Ollama 答案质量对比”，必须先填真实百炼 Key；当前百炼 query 不能作为质量基线。
- **上下文 4**：如果要让配置语义更一致，需要单独决定是否把 `LLM_PROVIDER` 纳入切换字段；本轮为了遵守“三字段切换”没有改它。
- **上下文 5**：Ollama 模式下 rerank 仍然会走百炼并 fallback，后续全本地化任务需要处理本地 rerank。
- **上下文 6**：PowerShell 下 `Invoke-WebRequest` 在一次 Ollama 响应解析时出现客户端对象异常；`curl.exe` + UTF-8 请求文件更稳定。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|----|------|------|
| A1 全项目 pytest | ✅ | `20 passed, 4 skipped, 2 warnings` |
| A1 CI 路径 pytest | ✅ | `13 passed, 11 deselected, 2 warnings` |
| A1 覆盖率 | ✅ | `TOTAL 316 83 74%` |
| A2 静态检查 | ✅ | ruff check / ruff format / mypy 全通过 |
| A3 七条铁律 + 敏感词扫描 | ✅ | PowerShell `Select-String` 等价检查无命中 |
| A4 spec §4 文件 | ✅ | `.env.example`、`docs/migration-test.md`、task spec、本 Handoff |
| A5 依赖安全扫描 | ✅ | 未新增依赖；`uv pip check` compatible |
| A6 commit message | ✅ | `docs: verify Ollama switch for #21`，body 含 `Refs: #21` |
| A7 Handoff 完整性 | ✅ | §0-§8 齐全，含 `last_verified_commit` |
| A8 CI 复现 | ⚠️ | PR #8 未触发 workflow；见 §3 偏差 3 |

### Part B 软指标

**B1 错误处理**：本轮没有新增或修改 `except` 块。外部调用失败仍由既有逻辑处理：`backend/app/services/rag_pipeline.py:75` 捕获 `LLMServiceError` 后 rerank fallback；`backend/app/services/qdrant_store.py` 仍用 `raise VectorStoreError(...) from exc`。百炼 placeholder 的 `UnicodeEncodeError` 未在本轮修复，因为禁止修改业务代码。

**B2 偏差**：见 §3，共 3 条：模型口径调整、百炼 placeholder 导致 query 500、docs/config-example PR 未触发 CI。

**B3 安全**：`.env` 未提交，`LLM_API_KEY` 输出均遮蔽。`docs/migration-test.md` 只记录 placeholder 字面值用于解释错误，没有真实 Key。敏感 Key pattern 扫描无命中。

**B4 性能与副作用**：本轮无业务代码改动。外部 IO 包括 Ollama HTTP tags、Qdrant collection 查询、FastAPI `/api/v1/query` 请求；Ollama query 总耗时 24.124 秒，符合小模型本地首次/低配运行预期。

**B5 可测性**：没有新增公共函数。迁移行为用真实 HTTP 调用验证，单元/集成测试仍全绿；`docs/migration-test.md:303` 到 `docs/migration-test.md:321` 记录了可复核指标。

**B6 配置合规**：模型切换只走 `.env`。代码证据：`backend/app/services/llm.py:42` 到 `backend/app/services/llm.py:44` 使用 `settings.llm_model` / `settings.llm_base_url` / `settings.llm_api_key`；`backend/app/api/query.py:25` 返回 `settings.llm_model`。

**B7 并发与线程安全**：不适用，无 async 逻辑或共享状态改动。验证期间启动过临时 `uvicorn` 进程，任务结束前已关闭。

**B8 下一轮暗坑**：

1. `docs/migration-test.md:476`：中文 placeholder Key 会导致 header 编码错误，后续要填真实 Key 或换 ASCII placeholder。
2. `docs/migration-test.md:480`：Ollama 下 rerank 仍是百炼 fallback，不是全本地化。
3. `docs/migration-test.md:490`：`LLM_PROVIDER` 是否纳入切换字段需要后续单独定口径。

### Part C 陷阱核查（18 项）

- C1 ✅ `backend/app/` 无 `print(` 命中。
- C2 ✅ `backend/app/` 无 stdlib `logging` 命中。
- C3 ✅ 本轮无业务代码硬编码 URL/端口/模型名；模型名只在 `.env.example` 和 docs。
- C4 ✅ 无 `# type: ignore` 新增。
- C5 ✅ 无 `except: pass` 或 `except Exception: pass` 新增。
- C6 ✅ 无异常链改动。
- C7 ✅ 无文件/连接/HTTP client 代码改动。
- C8 ✅ 无外部 client 工厂缓存改动。
- C9 ✅ 无 endpoint 改动。
- C10 ✅ 无 async 代码改动。
- C11 ✅ 无 `os.getenv()` / `os.environ` 新增。
- C12 ✅ 无新增必填环境变量，只补充示例值。
- C13 ✅ 未修改 `config.yaml`。
- C14 ✅ 无新增第三方依赖。
- C15 ✅ 无测试逻辑改动。
- C16 ✅ 无公共函数新增。
- C17 ✅ `mypy app` 和全量 pytest 通过。
- C18 ✅ 无公共 API 删除或变更。

ANTIPATTERNS 对照结果：

- 已检查反模式总数：6（A1/B1/C1/D1/E1/F1）
- 本轮新增命中：0
- 既有 D1 / CORS 遗留仍由 #59 处理，本轮不改代码。

### Part D 人工触发

- D1-D3 代码量：0 行代码，docs/spec/report 943 行，低于代码阈值。
- D4 修改 main 上已有代码文件数：0。
- D5 新增依赖：无。
- D6 核心抽象改动：否。
- D7 公共 API 删改：否。
- D8 Part A 失败：否；A8 是 workflow 未触发，不是检查失败。
- D9 Part C 失败：否。
- D10 覆盖率下降：否，仍为 74%。
- D11 偏差数：3，未超过阈值；均已解释。

### Part E 自我反思

**E1 三个改进点**：

1. 当前 `docs/migration-test.md:187` 明确只改 3 个字段，因此 `LLM_PROVIDER` 保持原值。重做时可以先和审查者确认是否允许把 `LLM_PROVIDER` 也改为 `ollama`，让配置语义更一致。本次没改是为了严格遵守“三字段切换”的验收口径。
2. 当前 `docs/migration-test.md:276` 记录了 `Invoke-WebRequest` 客户端解析异常。重做时可以一开始就使用 `curl.exe` + UTF-8 请求文件，减少 PowerShell 对中文 JSON 的干扰。本次保留该过程是因为它真实发生且服务端返回 200。
3. 当前 `docs/migration-test.md:398` 的回滚验证只能证明恢复到原配置和原行为，不能证明百炼可生成答案。重做时应先准备 ASCII placeholder 或真实百炼 Key，再做完整质量对比。本次没改 `.env` 原始 Key 是因为 `.env` 不应被本任务提交，且禁止改业务代码绕过错误。

**E2 忠告**：

- 验证 Ollama 迁移时优先用 HTTP API 判断服务是否可用，不要只依赖 `ollama` CLI；本机 CLI 不在 PATH，但 `http://localhost:11434/api/tags` 正常返回。

**E3 新发现反模式**：

- 未新增反模式。`LLM_PROVIDER` 语义与实际 LLM endpoint 不一致是本任务三字段切换口径带来的文档风险，已在 §5/§7 标注；是否形成反模式建议后续在 #60 或配置治理任务里统一决定。

### 修复轨迹

- 无 fix_attempt。实现阶段只做了模型名口径同步：将 #21 spec 中 `qwen2.5:7b` 替换为实际验证的 `qwen2.5:3b`。

### 总评

✅ PASS（铁律 #7 验证通过，可合并）

last_verified_commit: d2131aa274bbcfa98b108c33a7e95ba84b0ad3b6
