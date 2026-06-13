# Handoff: 任务 #26 - 批量产品 KB 元数据抽取

> **执行者**：Codex
> **完成日期**：2026-06-13
> **分支**：feat/W2-D2-26-batch-extract
> **PR**：#20 - https://github.com/Ruidooww/rag-kb/pull/20
> **基于**：`docs/handoffs/W2-D2-25-handoff.md`

---

## 0. TL;DR

**总评：NEEDS_HUMAN（代码层 PASS；实际跑批 deferred）**

代码层 PASS：`11 + 3` 目标测试、`165` non-integration、coverage `86%`、ruff / format / mypy app / mypy scripts / 铁律 grep 全过；实际跑批 deferred 至 `LLM_API_KEY` 配置真实百炼 key 后单独执行。

### 关键数据

- 共享 xlsx 契约：24 列，`scripts/_xlsx_schema.py::METADATA_COLUMNS` 单源
- 批处理：递归扫描、settings 并发、断点续跑、原子 xlsx 写入、锁文件重试一次
- 失败二分：`MetadataExtractError -> needs_review`；意外异常 -> 三字段脱敏 JSONL
- 目标测试：批处理 `11 passed`；schema `3 passed`
- 非 integration：`165 passed, 19 deselected`，coverage `86%`
- 完整 pytest：`180 passed, 4 skipped`
- 实际跑批：deferred，空结果 `metadata_sample.xlsx` 已删除
- 有效新增：`897` 行，Part D 命中 D2 Soft；新增 `tqdm` 为 `MPL-2.0 AND MIT`，命中 D5 人工确认

### 最大风险

真实百炼 key 未配置，TEXT/VISION 路由分布、六字段准确率和 199 份全量结果尚未获得。

### 最大亮点

批处理只调用 #25 公共入口，预期失败和意外失败被物理分流并由自动化测试锁定，且不会把 traceback、异常 message 或文件路径泄露到进度条/logger。

### 给审查者的 3 个看点

1. `backend/scripts/batch_extract_product_kb.py:146` 的失败语义二分和 JSONL 脱敏。
2. `backend/scripts/batch_extract_product_kb.py:167` 的 semaphore、`as_completed`、断点续跑和线程卸载。
3. `backend/scripts/_xlsx_schema.py:5` 的 24 列单源是否适合作为 #27 / #28 稳定契约。

---

## 1. 任务概述

本任务把 #25 单文档产品 KB 抽取入口批量化，递归扫描 199 份产品资料，按 `settings.ingest_concurrency` 控制并发，输出供 #27 审核和 #28 入库共用的稳定 xlsx。代码层实现和验收已完成；真实跑批受外部 `LLM_API_KEY` 占位符阻塞，经用户明确放行 deferred。

---

## 2. 完成清单（对应 spec §4）

- [x] §4.1 `backend/scripts/_xlsx_schema.py`
- [x] §4.2 `backend/scripts/batch_extract_product_kb.py`
- [x] §4.3 `backend/tests/scripts/test_batch_extract_product_kb.py`
- [x] §4.4 `backend/tests/scripts/test_xlsx_schema.py`
- [x] §4.5 `backend/pyproject.toml` / `backend/uv.lock`
- [x] §4.6 `.gitignore`
- [x] P4 实施计划：`docs/superpowers/plans/2026-06-13-batch-product-kb-extract.md`
- [ ] §5.2 真实 5 份试水 + 199 份全量跑批：deferred，见 §3 / §4 / §5

额外同步：`backend/scripts/verify_langgraph.py` 仅修正返回类型注解，使硬指标 `mypy scripts` 可执行并通过，不改变运行行为。

---

## 3. 与 Spec 的偏差

- **偏差 1：Spec §5.2 跑批验收 deferred**
  - Spec：自动化后执行 5 份试水，再执行 199 份全量并回填路由、准确率、成本、耗时和结果总数。
  - 实际实现：5 份诊断试水暴露 `.env` 的 `LLM_API_KEY` 是非 ASCII 占位符，无法产生有效元数据；用户明确放行将真实试水和全量跑批 deferred。
  - 理由：外部环境阻塞而非批处理代码问题；保留空结果没有审核价值。
  - Commit：`040f35b3b6fe722f88f61253c44dd2edf7b155c4`
  - 影响：代码可 review/merge，但运行时验收数据必须在真实 key 就位后补跑并回填本文件 §4。

- **偏差 2：用户取消 ¥100 预算停止阈值**
  - Spec：5 份估算后，预计总费用超过 ¥100 时暂停。
  - 实际实现：用户明确要求“不用管预算”；费用仅记录，不再作为停止条件。
  - 理由：用户直接产品决策。
  - Commit：`040f35b3b6fe722f88f61253c44dd2edf7b155c4`
  - 影响：真实 key 就位后的全量跑批不因费用估算自动停止。

- **偏差 3：同步修复既有 `mypy scripts` 基线**
  - Spec：硬指标要求 `uv run mypy scripts` 通过。
  - 实际实现：启用 `explicit_package_bases`，并把 `verify_langgraph.py::build_graph()` 从 `object` 精确标注为 `CompiledStateGraph[...]`。
  - 理由：首次运行硬指标时暴露 namespace package 重复模块名和既有错误返回类型；不修则 #26 无法满足验收。
  - Commit：`040f35b3b6fe722f88f61253c44dd2edf7b155c4`
  - 影响：脚本目录可被 mypy strict 检查；`verify_langgraph.py` 运行行为不变。

### 分支上下文说明

`docs/tasks/W2-D2-26-batch-metadata-extract.md` v2 和 `docs/dispatch/W2-D2-26-dispatch.md` 是用户在 Step 1 前预置的任务文档，本任务保留并纳入 PR，不计为实现偏差。

---

## 4. 本地验收结果

### 代码层自动化

| 项目 | 结果 | 原始输出摘要 |
|---|---|---|
| 批处理目标测试 | PASS | `11 passed, 1 warning in 3.24s` |
| xlsx schema 测试 | PASS | `3 passed, 1 warning in 0.03s` |
| 非 integration + coverage | PASS | `165 passed, 19 deselected, 2 warnings`；TOTAL `86%` |
| 完整 pytest | PASS | `180 passed, 4 skipped, 2 warnings in 167.99s` |
| ruff / format | PASS | `All checks passed!`；`88 files already formatted` |
| mypy app | PASS | `Success: no issues found in 48 source files` |
| mypy scripts | PASS | `Success: no issues found in 6 source files` |
| `uv pip check` | PASS | `All installed packages are compatible` |
| 入口锁定 grep | PASS | 无 #25 私有 helper、pypdf/pdf2image 自路由调用 |
| 范围 grep | PASS | 无 customer_match / CRM / IdP / Qdrant / DB 写入 |
| 脱敏 grep | PASS | 无 traceback / `str(exc)` / `repr(exc)` / secret logging |

### 实际跑批数据

| 指标 | 结果 |
|---|---|
| 总份数 | deferred |
| 成功 | deferred |
| needs_review | deferred |
| 意外失败 | deferred |
| TEXT 路由 | deferred |
| VISION 路由 | deferred |
| 抽取准确率 | deferred |
| 单份成本估算 | deferred |
| 实际耗时 | deferred |

5 份试水暴露的根因 = `LLM_API_KEY` 为占位符（非 ASCII），#25 入口已按预期把所有失败转 needs_review；脚本层失败二分逻辑正确（5/5 进 needs_review xlsx，0/5 进 failed_docs.jsonl）。该诊断试水耗时 `30.334s`，但不作为有效跑批耗时；空数据 `metadata_sample.xlsx` 已删除。

### 5 份人工核对表

| 预期 doc_category | 文件 | extract_method | product_module 值/置信度 | product_version 值/置信度 | platform 值/置信度 | target_audience 值/置信度 | doc_category 值/置信度 | sensitivity 值/置信度 | 人工准确率 |
|---|---|---|---|---|---|---|---|---|---|
| user_manual | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred |
| deployment | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred |
| test_case | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred |
| release_note | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred |
| troubleshoot | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred | deferred |

### 关键命令原始输出摘要

```text
uv run pytest tests/scripts/test_batch_extract_product_kb.py -v
11 passed

uv run pytest tests/scripts/test_xlsx_schema.py -v
3 passed

uv run pytest -m "not integration" --cov=app --cov-report=term-missing
165 passed, 19 deselected
TOTAL 86%

uv run pytest -v
180 passed, 4 skipped

uv run ruff check .
All checks passed!

uv run ruff format --check .
88 files already formatted

uv run mypy app
Success: no issues found in 48 source files

uv run mypy scripts
Success: no issues found in 6 source files
```

---

## 5. 已知问题 / 风险

- **真实跑批阻塞**
  - `.env` 的 `LLM_API_KEY` 当前是占位符，5 份试水 + 全量 199 份待真实 key 就位后补跑；脚本本身已通过 14 自动化测试 + 路由/失败二分单测。
  - 在补跑前，不能声明六字段抽取准确率、TEXT/VISION 分布或 199 份成功率。

- **真实路径进入业务输出**
  - `failed_docs.jsonl` 和 xlsx 的 `doc_path` 是必要业务字段，允许记录真实路径；进度条/logger 不显示路径。
  - 这些产出已加入 `.gitignore`，不得提交到 Git。

- **断点续跑以字符串路径为键**
  - 当前按 `str(path)` 精确匹配已完成记录；同一文件改用相对/绝对路径会被视作不同文档。
  - #27 / #28 读取时应沿用本次输出的路径形式。

### 新增第三方依赖

- `tqdm==4.67.3`，License: `MPL-2.0 AND MIT`，用于仅显示完成数和扩展名的进度条。该组合 license 不属于 SELF_REVIEW 的精确白名单表达，交 reviewer 人工确认。
- `pandas==3.0.3`（BSD-3-Clause）与 `openpyxl==3.1.5`（MIT）已由 #24 引入，本任务复用并显式作为 xlsx 读写引擎。

---

## 6. 给审查者的提示

- **重点 1**：`backend/scripts/batch_extract_product_kb.py:156` 只调用 `extract_product_kb_metadata`，没有调用任何 #25 私有 helper。
- **重点 2**：`backend/scripts/batch_extract_product_kb.py:158-164` 核对 `MetadataExtractError` 与意外异常分流，以及 logger 只输出扩展名 + 异常类名。
- **重点 3**：`backend/scripts/batch_extract_product_kb.py:109-118` 核对 JSONL 每行仅 `doc_path/ext/error_type` 三个 key，无 message/traceback。
- **重点 4**：`backend/scripts/batch_extract_product_kb.py:129-144` 核对 xlsx 续写、临时文件原子替换和锁文件一次重试。
- **重点 5**：`backend/scripts/batch_extract_product_kb.py:175-198` 核对阻塞 IO 均卸载到线程，Semaphore 并发来自 settings。
- **重点 6**：`backend/scripts/_xlsx_schema.py:5` 核对 24 列顺序及 #27/#28 审核字段。

---

## 7. 给下一轮的提示

- **真实 key 就位后的执行顺序**：sample_5 试水 → 人工核对 6 字段准确率 → 全量 199 份 → 结果回填本 Handoff §4 跑批数据表。
- **补跑前清理**：确认 `backend/data/metadata_sample.xlsx`、`backend/data/metadata.xlsx`、`backend/data/failed_docs.jsonl` 不存在或明确要续跑；避免把占位 key 产生的 needs_review 空行当作有效结果。
- **#27 / #28 schema 契约**：直接 import `scripts._xlsx_schema.METADATA_COLUMNS`，不得在下游 inline 列名或更改顺序。
- **失败语义**：`MetadataExtractError` 是预期人工审核行，不进入 failed JSONL；只有 IO/OOM/未预期异常进入 JSONL。
- **0003 迁移提醒**：#28 入库前继续遵守 PR-18 F2，先备份并 dry-run 有损 migration。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|---|---|---|
| A1 全项目 pytest | PASS | `180 passed, 4 skipped`；non-integration `165 passed`；coverage `86%` |
| A2 静态检查 | PASS | ruff / format / mypy app / mypy scripts / pip check 全通过 |
| A3 铁律+敏感词 grep | PASS | 模型直连、私有 helper、os env、客户/DB/Qdrant、异常细节输出均无命中 |
| A4 spec §4 文件 | PASS（代码层） | §4.1-§4.6 已完成；§5.2 运行验收经用户放行 deferred |
| A5 依赖安全 | NEEDS_HUMAN | pip check 通过；新增 tqdm 为 `MPL-2.0 AND MIT` |
| A6 commit message | PASS | `feat: #26 batch extract product KB metadata (199 docs)`，body 含 `Refs: #26` |
| A7 Handoff 完整性 | PASS | 本文件包含 §0-§8、Part A-E、deferred 跑批表 |
| A8 CI 复现 | pending | PR #20 Self-Review 已触发，Handoff 推送后复现 |

### Part B 软指标

**B1 错误处理**：`batch_extract_product_kb.py:142` 对 xlsx 锁文件仅重试一次；`:158` 把 `MetadataExtractError` 转审核行；`:160` 把意外异常写三字段 JSONL并继续批次；`:223` CLI 顶层用通用消息处理 IO/ValueError。无 `except: pass` 或异常 message 输出。

**B2 偏差**：见 §3，共 3 条，均有明确原因和影响。

**B3 安全**：`batch_extract_product_kb.py:109` 的 JSONL 只有 `doc_path/ext/error_type`；`:163` logger 只有 ext + class；进度条只显示 ext。grep 无 `logger.*api_key`、`print.*api_key`、`traceback`、`str(exc)`、`repr(exc)` 命中。

**B4 性能与副作用**：`batch_extract_product_kb.py:155` 文件读取、`:162` JSONL 写入、`:175-177` 扫描/续跑读取和 `:198` xlsx 写入均通过 `asyncio.to_thread`；`:179` semaphore 使用 settings。无 DB/Qdrant 写入、N+1 或模型调用重试/限流；xlsx 锁文件仅按 spec 重试一次。

**B5 可测性**：扫描、schema 行转换、预期失败、意外失败、并发上限、断点续跑、列完整、进度脱敏、列表序列化和 xlsx 锁重试均有测试；共 14 项。真实 LLM 准确率不由 mock 测试替代，明确 deferred。

**B6 配置合规**：并发仅来自 `settings.ingest_concurrency`；输入/输出路径只来自 CLI；脚本无 `os.getenv/os.environ`、模型名、URL、阈值或 prompt。

**B7 并发与线程安全**：`batch_extract()` 通过 `asyncio.as_completed` 消费任务，通过 Semaphore 限制并发；JSONL 追加使用 `asyncio.Lock` 串行化；阻塞 IO 全部线程卸载，无共享可变业务状态。

**B8 下一轮暗坑**：

1. `batch_extract_product_kb.py:120` 断点续跑严格按字符串路径匹配，补跑时需沿用相同 CLI 路径形式。
2. `batch_extract_product_kb.py:158` 的预期失败仍会写入 xlsx；补跑前必须删除占位 key 产生的空行，避免被 resume 跳过。
3. `batch_extract_product_kb.py:129` 每批结束一次性合并写 xlsx；进程中途终止时，已完成但尚未写盘的结果不会保留。

### Part C 陷阱核查（18 项）

- C1 通过：无调试 print；CLI 摘要 print 均有 `# noqa: T201`
- C2 通过：无 stdlib logging
- C3 通过：无硬编码 URL、端口、模型、秘钥、并发数或阈值
- C4 通过：无新增 `# type: ignore`
- C5 通过：无静默吞错
- C6 通过：本任务没有包装后重抛异常；意外异常按 spec 消费并记录安全类型
- C7 通过：文件句柄使用 `with`，连接/client 不在本任务创建
- C8 通过：无副作用工厂缓存
- C9 N/A：无 API endpoint
- C10 通过：async 路径阻塞 IO 均通过 `asyncio.to_thread`
- C11 通过：并发参数走 settings，无散落 env
- C12 N/A：未新增环境变量
- C13 N/A：未新增业务配置参数
- C14 通过：新增 tqdm 已在 PR/Handoff 说明
- C15 通过：mock 只隔离外部 #25 入口；扫描、IO、xlsx、JSONL、并发和错误分流执行真实逻辑
- C16 通过：公共扫描/批处理入口与主要行为均有测试
- C17 通过：`import app.main; import scripts.batch_extract_product_kb`、mypy 和完整 pytest 通过
- C18 通过：无公共 API 删除；共享 xlsx schema 同 PR 提供

**ANTIPATTERNS.md 显式对照**：

- I1 sub-agent：未派 sub-agent；schema、脚本、测试和最终集成由主 agent 集中维护并跑全量验收。
- J1 路由分流：N/A，本任务无 API/router。
- K1 脱敏：N/A 于 API response；脚本进度/logger/JSONL 已按 P1 精神做最小信息输出。

### Part D 人工触发

- D1-D3：有效新增 `897` 行，命中 D2 Soft；主要体量来自批处理实现、14 项行为测试和执行计划，拆分会割裂同一失败/续跑契约。
- D4：修改 5 个 main 上已有文件，未超过阈值。
- D5 Hard：新增直接依赖 tqdm，license 为 `MPL-2.0 AND MIT`，需人工确认。
- D6：未修改 `backend/app/core/*` 或 `services/llm.py`。
- D7：无公共 API 删除/重命名。
- D8：代码层 Part A 无失败；运行时 §5.2 经用户放行 deferred。
- D9：Part C 无失败。
- D10：coverage `86%`，与上一轮持平。
- D11：3 条偏差，未超过阈值。

### Part E 自我反思

**E1 三个改进点**：

1. `batch_extract_product_kb.py:198` 当前在整批完成后一次性写 xlsx；更大规模时可按固定批次 checkpoint，降低进程中断损失。本任务不加是因为 spec 要求 lean MVP，且 199 份规模可控。
2. `batch_extract_product_kb.py:120` 以路径字符串作为 resume key；长期可改为规范化相对路径或内容 hash。本任务不改是为了保持 xlsx 契约简单，并避免进入 #28 去重范围。
3. 试水前只检查了 key 是否非空，没有检查是否为明显占位符/非 ASCII。重做时会在运行验收前加只读环境预检脚本；本任务不把它加入产品代码，因为 key 管理由部署环境负责。

**E2 忠告**：批处理测试全绿不等于真实模型准确率已验证；外部 key、模型权限和真实文档试水必须作为独立运行验收门槛记录，不能用 mock 结果代替。

**E3 新发现反模式**：仅检查 secret “非空”会让占位符进入真实调用并产生大量可恢复空结果。当前通过删除空 xlsx和 deferred 明确阻断；后续部署 checklist 应增加 secret 格式预检，但不在本任务扩改通用反模式文档。

### 修复轨迹

- fix_attempt:0：功能按 TDD 实现；开发阶段补齐 xlsx 锁文件一次重试和 `mypy scripts` 基线，无提交后修复轮次。
- 诊断试水：5/5 被 #25 入口按预期转 `MetadataExtractError`，0/5 写入 failed JSONL；因 key 占位符未作为有效跑批验收。

### 总评

**NEEDS_HUMAN（代码层 PASS；实际跑批 deferred）**

原因：新增 tqdm 的组合 license 命中 D5 人工确认；同时真实 key 未就位，缺少 spec §5.2 路由、准确率和 199 份跑批验收数据。禁止自动合并。

**last_verified_commit**: `040f35b3b6fe722f88f61253c44dd2edf7b155c4`
