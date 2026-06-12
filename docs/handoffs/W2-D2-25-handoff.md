# Handoff: 任务 #25 v2 - 产品 KB 元数据抽取 + DocumentMetaSchema 契约修复

> **执行者**：Codex
> **完成日期**：2026-06-13
> **分支**：feat/W2-D2-25-product-kb-extract
> **PR**：#18 - https://github.com/Ruidooww/rag-kb/pull/18
> **基于**：`docs/handoffs/W2-D1-24-handoff.md`

---

## 0. TL;DR

**总评：NEEDS_HUMAN（必须人工 review，不自动合并）**

### 关键数据

- Task 0：`document_meta` 五字段 ACL 契约通过 `0003` 对齐 PR #13 Pydantic 锚点
- 主体：单文档产品 KB 元数据抽取，TEXT/PDF 文本/PDF 视觉路由，统一经 `get_llm()`
- 目标测试：Task 0 `9 passed`；主体 `20 passed`
- 非 integration 全量：`153 passed, 19 deselected`，coverage `86%`
- 完整 pytest：`168 passed, 4 skipped`
- Self-review：Part A 本地通过；Part C 18/18 已对照；Part D 命中 D3 / D4 / D6 Hard
- 有效新增：排除 lock、handoff、tasks/reviews 后 `1176` 行；修改 7 个已有主文件
- 与 spec 偏差：3 条，均经用户明确放行
- fix_attempt：0 次

### 最大风险

`0003` 在已有数据环境会把全部旧 `sensitivity` 折叠为 `3`，downgrade 也会丢失 ACL 细节；生产执行前必须备份并 dry-run。

### 最大亮点

PR #13 的五字段 ACL 锚点、数据库 ORM/migration 和 #25 抽取输出已形成同一契约，同时保持 lean MVP 不入库、不并发、不接 CRM/IdP。

### 给审查者的 3 个看点

1. `backend/migrations/versions/0003_document_meta_acl_align.py:17` 的有损转换和 downgrade 是否符合后续部署策略。
2. `backend/app/services/product_kb_extract.py:42` 的 PDF 路由、错误脱敏和 unsupported extension 人工审核边界。
3. `backend/app/services/product_kb_extract.py:159` 的 `doc_category -> ACL` 映射是否满足 #26 / #28 接续要求。

---

## 1. 任务概述

本任务先执行 Task 0，通过 Alembic `0003` 和 ORM/schema 下游入参修复，将 #24 的 `document_meta` 数据库实现对齐 PR #13 的五字段 ACL Pydantic 锚点。随后实现 lean MVP 产品 KB 元数据抽取：prompt 文件化、LLM/VLM 统一走 `get_llm()`、低置信度标记人工审核，并明确把 Office/图片转换管线留到 Phase 2。

---

## 2. 完成清单（对应 spec §2 / §4）

### Task 0：DocumentMetaSchema 契约修复

- [x] `backend/migrations/versions/0003_document_meta_acl_align.py`
- [x] `backend/app/db/models/document_meta.py`
- [x] `backend/tests/db/test_document_meta_acl_contract.py`
- [x] 用户放行同步修复 `backend/app/models/customer.py::DocumentMetaCreate`
- [x] 用户放行同步修复 `backend/tests/db/test_customer_repo.py` nullability 断言
- [x] `backend/app/db/repos/document_meta.py` 保持不变；现有 `data.model_dump()` 自动跟随 schema

### 主体 §4.1-§4.7

- [x] §4.1 `backend/prompts/extract_product_kb.txt`
- [x] §4.2 `backend/app/models/product_kb_metadata.py`
- [x] §4.3 `backend/app/services/product_kb_extract.py`
- [x] §4.4 `backend/app/core/config.py`
- [x] §4.5 `backend/app/core/exceptions.py`
- [x] §4.6 `backend/tests/services/test_product_kb_extract.py`
- [x] §4.7 `backend/pyproject.toml`

配套更新：`config.yaml`、`backend/uv.lock`；P4 实施计划位于 `docs/superpowers/plans/2026-06-13-product-kb-metadata-extract.md`。

Task 0 五字段最终契约：

| 字段 | 最终 ORM 契约 |
|---|---|
| `audience` | `String(32)`，默认 `internal_only`，check constraint |
| `owner_dept` | `String(32) \| None`，可空 |
| `visibility` | `String(32)`，默认 `internal`，check constraint |
| `sensitivity` | `Integer`，默认 `3`，check `1-5` |
| `shared_depts` | `ARRAY(String(32))`，保持不变 |

---

## 3. 与 Spec 的偏差

- **偏差 1：Task 0 同步修复下游 `DocumentMetaCreate` 和既有断言，repo 不改**
  - Spec：Task 0 列出 ORM、migration、repo 和契约测试。
  - 实际实现：经用户明确放行，额外修复 `app/models/customer.py::DocumentMetaCreate` 与 `tests/db/test_customer_repo.py`；`app/db/repos/document_meta.py` 因使用 `data.model_dump()` 无需修改。
  - 理由：否则 `0003` 后下游入参 schema 和既有断言仍违反 PR #13 锚点。
  - Commit：`587aa33c660bdd5a207b37451759539ac97f0c10`
  - 影响：ORM、入参 schema 和测试契约一致；repo 行为不变。

- **偏差 2：路由规则按用户确认收窄为 lean MVP**
  - Spec：`.pptx/.xlsx/带图密集.pdf` 走 VISION。
  - 实际实现：PDF 仅以 pypdf 输出非空/空白判定 TEXT/VISION，不做字符阈值或图像密度分析；`.pptx/.xlsx/.doc/.jpg` 及其他非 PDF、非 `.txt/.md` 扩展名当前抛脱敏 `MetadataExtractError`，并用仅含扩展名和 lean MVP 标记的 `review_reasons` 进入人工审核。
  - 理由：用户选择 Option B；LibreOffice/Office 图片转换管线由 Phase 2 独立 spec 触发。
  - Commit：`587aa33c660bdd5a207b37451759539ac97f0c10`
  - 影响：Office/图片文件不会在本任务自动抽取；无路径泄露，边界由测试名锁定。

- **偏差 3：补齐三类 `doc_category` ACL 兜底映射**
  - Spec：明确 customer-facing、test_case、deployment 等主映射，未完整锁定 `release_note/troubleshoot/other`。
  - 实际实现：用户接受 `release_note -> internal_only/internal/None`、`troubleshoot -> internal_only/internal/aftersales`、`other -> internal_only/internal/None`。
  - 理由：保证所有枚举值均产生确定、最小权限 ACL。
  - Commit：`587aa33c660bdd5a207b37451759539ac97f0c10`
  - 影响：#26 / #28 必须沿用 §7 完整映射，变更需单独产品决策。

### 分支上下文说明

`docs/dispatch/W2-D2-25-v2-dispatch.md` 来自用户预先提交的 commit `8bedc9529046d4147ad600f03dfcdcb5f0871a38`。本任务未创建、编辑或暂存该文件；它随目标分支进入 PR，但不计为实现偏差。

---

## 4. 本地验收结果

| 项目 | 结果 | 备注/原始输出摘要 |
|---|---|---|
| Task 0 Alembic 双向迁移 | 通过 | upgrade head / downgrade -1 / upgrade head；`current` 为 `0003 (head)` |
| Alembic 漂移 | 通过 | `No new upgrade operations detected.` |
| Task 0 契约测试 | 通过 | `9 passed, 1 warning in 2.05s` |
| 主体抽取测试 | 通过 | `20 passed, 1 warning in 0.52s` |
| 非 integration + coverage | 通过 | `153 passed, 19 deselected, 2 warnings in 56.38s`；TOTAL `86%` |
| 完整 pytest | 通过 | `168 passed, 4 skipped, 2 warnings in 96.73s` |
| ruff / format / mypy | 通过 | All checks passed；84 files formatted；48 source files 无类型错误 |
| `uv pip check` | 通过 | 所有已安装依赖兼容 |
| import smoke | 通过 | `import app.main; import app.services.product_kb_extract` |
| 铁律 / 敏感词 grep | 通过 | dashscope/openai/model URL/os env/print/logging/silent except/type ignore/secret logging 均无违规命中 |
| Pydantic 锚点 | 通过 | `git diff main -- backend/app/models/document_meta.py` 无输出 |
| 当前 PG ACL 状态 | 通过 | 空表；owner_dept nullable；sensitivity integer；shared_depts ARRAY；3 个命名 check 存在 |
| CI 首次运行 | 待 Handoff 推送后复现 | run `27431635538` 仅 A7 因缺少本文件失败 |

### 关键命令原始输出摘要

```text
uv run alembic current
0003 (head)

uv run alembic check
No new upgrade operations detected.

uv run pytest tests/db/test_document_meta_acl_contract.py -v
9 passed, 1 warning in 2.05s

uv run pytest tests/services/test_product_kb_extract.py -v
20 passed, 1 warning in 0.52s

uv run pytest -m "not integration" --cov=app
153 passed, 19 deselected, 2 warnings in 56.38s
TOTAL 86%

uv run pytest -v
168 passed, 4 skipped, 2 warnings in 96.73s

uv run ruff check .
All checks passed!

uv run ruff format --check .
84 files already formatted

uv run mypy app
Success: no issues found in 48 source files
```

---

## 5. 已知问题 / 风险

- **`0003` 对已有数据是有损迁移**
  - Upgrade 将所有旧字符串 `sensitivity` 转成 `3`；downgrade 将全部 sensitivity 转成 `"normal"`、null owner_dept 转成空字符串、`internal_only` 转回 `internal`。
  - 当前本地 PG 的 `document_meta` 是空表，因此双向迁移通过不代表有数据环境无业务损失。

- **Office/图片转换器不在 lean MVP**
  - `.pptx/.xlsx/.doc/.jpg` 等会抛通用 `MetadataExtractError("Failed to extract metadata")`，携带 extension-only review reason。
  - 5 份边界样本需进入 `needs_review` 人工兜底；LibreOffice 管线由 Phase 2 独立 spec 处理。

- **未做真实 5 份文档的 LLM/VLM 抽样**
  - 自动化测试全部 mock `get_llm()`，验证路由、prompt、解析和 ACL，不验证线上模型对 IP-Guard 资料的实际准确率。
  - W2 抽样需要真实模型凭证、真实资料和可用 Poppler 环境。

- **`doc_path` 是内部模型字段**
  - 当前任务无 API；`ProductKBMetadata.doc_path` 保留完整内部路径以便调用方关联。
  - 未来 endpoint 不得直接向外部用户返回该字段，必须 sanitize。

- **`FieldConfidence.value` 是通用类型**
  - 枚举主要由 prompt 约束，Pydantic 未对每个字段分别强制枚举。
  - 未知 `doc_category` 会落到最小权限 ACL 兜底并应人工审核；真实样本后再决定是否收紧 schema。

### 新增第三方依赖

- `jinja2==3.1.6`，BSD，用于文件化 prompt 渲染。
- `pypdf==6.13.2`，BSD-3-Clause，用于 PDF 文本判定与抽取。
- `pdf2image==1.17.0`，MIT，用于空白文本 PDF 的页面图像转换。
- `pillow==12.2.0`，MIT-CMU，用于图像编码；不属于 SELF_REVIEW 精确白名单字符串，交由 reviewer 确认。

---

## 6. 给审查者的提示

- **重点 1**：`backend/migrations/versions/0003_document_meta_acl_align.py:17` 核对 upgrade/downgrade 有损行为，以及 revision `0003` / down_revision `0002`。
- **重点 2**：`backend/app/db/models/document_meta.py:11` 核对五字段 ACL 与 `app/models/document_meta.py` 锚点一致，尤其 `shared_depts` 仍为 `ARRAY(String(32))`。
- **重点 3**：`backend/app/models/customer.py:61` 核对下游 `DocumentMetaCreate` 同步对齐且未反向修改 PR #13 锚点。
- **重点 4**：`backend/app/services/product_kb_extract.py:42` 核对 unsupported extension 只记录扩展名，不回显路径；LLM/VLM 调用统一走 `get_llm()`。
- **重点 5**：`backend/app/services/product_kb_extract.py:159` 核对完整 ACL 映射和默认最小权限行为。
- **重点 6**：`backend/app/services/product_kb_extract.py:184` 核对低置信度阈值来自 settings，且没有写入 PG/Qdrant、调用 customer_match/CRM/IdP 或引入批量并发。

---

## 7. 给下一轮的提示

- **Task 0 数据迁移注意**：`0003` 已在干净空表 PostgreSQL 双向迁移通过。未来有数据时，执行前必须备份并 dry-run；upgrade 会把旧 sensitivity 全部折叠为 `3`，downgrade 会把 owner_dept null 变空字符串、sensitivity 变 `"normal"`、audience `internal_only` 变 `internal`。

- **#26 / #28 必须沿用的 ACL 映射**：

  | doc_category | audience | visibility | owner_dept |
  |---|---|---|---|
  | `user_manual`, `faq` | `customer_facing` | `public` | `None` |
  | `test_case` | `internal_only` | `confidential` | `qa` |
  | `deployment` | `internal_only` | `internal` | `impl` |
  | `troubleshoot` | `internal_only` | `internal` | `aftersales` |
  | `release_note`, `other` | `internal_only` | `internal` | `None` |

  当前抽取器统一令 `shared_depts=[]`；`sensitivity` 由 LLM 产出且必须是 `1-5`。

- **IP-Guard 产品模块枚举**：`backend/app/models/product_kb_metadata.py:10` 的 `ProductModule` 可能不完整。W2 抽样 5 份后可扩 enum；`backend/app/services/product_kb_extract.py:121` 会动态把 enum 渲染进 prompt，只有语义变化时才需同步修改 prompt 文案。

- **Poppler 跨平台部署**：Windows dev 安装 `conda-forge poppler`；CI / Docker 安装 `poppler-utils`。本任务不修改 Docker/CI，因为 backend 容器和 Office 转换管线不在 scope。

- **Phase 2 转换管线**：`.pptx/.xlsx/.doc/.jpg` 当前只进入脱敏错误 + 人工审核路径。LibreOffice/图片转换必须由独立 spec 引入，不要顺手把依赖塞进本任务。

- **未来 API 安全**：本任务无 endpoint，J1/K1 对 API response 为 N/A；未来 API 不得直接返回 `doc_path` 或底层异常。复用 `MetadataExtractError` 的通用消息，详细原因只写安全的内部日志。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|---|---|---|
| A1 全项目 pytest | 通过 | `168 passed, 4 skipped`；非 integration `153 passed, 19 deselected`；coverage `86%` |
| A2 静态检查 | 通过 | ruff check / format / mypy / pip check / import smoke 全通过 |
| A3 铁律+敏感词 grep | 通过 | dashscope/openai/model URL/os env/print/logging/silent except/type ignore/secret logging 无违规命中 |
| A4 spec §2 / §4 文件 | 通过 | Task 0 与 §4.1-§4.7 均完成；批准偏差见 §3 |
| A5 依赖安全 | 需人工确认 | pip check 通过；Jinja2/PyPDF/pdf2image 为允许 license；Pillow 为 MIT-CMU |
| A6 commit message | 通过 | 实现 commit `feat: add #25 product KB metadata extraction`，body 含 `Refs: #25`；预存 dispatch commit 见 §3 |
| A7 Handoff 完整性 | 通过 | 本文件含 §0-§8、§3 偏差、§6/§7 提示、Part A-E |
| A8 CI 复现 | 待本文件推送后复现 | 首次 run `27431635538` 仅因 A7 缺本文件失败 |

### Part B 软指标

**B1 错误处理**：`backend/app/services/product_kb_extract.py:66` 对 `MetadataExtractError` 原样抛出；`:68` 捕获其他异常，日志只记录安全扩展名和异常类型，再用 `raise MetadataExtractError() from exc` 保留异常链。`backend/app/services/product_kb_extract.py:52` 对 unsupported extension 主动抛通用异常，review reason 不含路径。无 `except: pass` 或 `except Exception: pass`。

**B2 偏差**：见 §3，共 3 条，均经用户明确放行。

**B3 安全**：`backend/app/core/exceptions.py:24` 的对外默认消息为 `"Failed to extract metadata"`；错误路径测试位于 `backend/tests/services/test_product_kb_extract.py:193`。无 secret logging、SQL/命令拼接或 API response；内部 `doc_path` 风险已在 §5/§7 标注。

**B4 性能与副作用**：`backend/app/services/product_kb_extract.py:45` 的 UTF-8 文本解码在内存执行；`:48` pypdf 和 `:54` pdf2image 均通过 `anyio.to_thread.run_sync` 卸载；`:107` / `:112` 是唯一外部 LLM/VLM IO。无数据库写入、N+1、重复外部调用或 LLM client 缓存。

**B5 可测性**：

- `extract_product_kb_metadata()` -> `test_text_path_extracts_all_fields`、PDF 两条路由测试、unsupported/error 脱敏测试
- `_route_by_extension()` -> `test_route_text_vs_vision_by_extension`
- `_apply_acl_defaults()` -> 两个固定 ACL 测试 + 参数化完整映射测试
- `_check_needs_review()` -> `test_low_confidence_field_flags_needs_review`
- `_render_prompt()` -> `test_prompt_renders_with_enums`
- `DocumentMeta` / `DocumentMetaCreate` -> `test_document_meta_acl_contract.py` 9 项

所有 LLM 调用均 mock；真实 LLM 5 文档抽样未执行，已列为风险。

**B6 配置合规**：`backend/app/core/config.py:61-64` 定义 threshold、prompts_dir、vision_dpi、vision_max_pages，`config.yaml` 已同步。目标路径无 `os.getenv` / `os.environ`、硬编码模型名或 DashScope URL；prompt 位于文件，不在 Python 中写长 prompt。

**B7 并发与线程安全**：公共抽取入口和 LLM helper 为 async；pypdf/pdf2image 阻塞工作在线程执行。无共享可变状态、无批量并发、无同步 HTTP。

**B8 下一轮暗坑**：

1. `backend/migrations/versions/0003_document_meta_acl_align.py:29` 的 sensitivity 类型转换有损，生产数据不可直接套用空表验证结论。
2. `backend/app/services/product_kb_extract.py:42` 当前对 Office/图片输入主动失败；#26 不得把 VISION 分类误认为已经有可用转换器。
3. `backend/app/models/product_kb_metadata.py:52` 的 `FieldConfidence.value` 未按字段强制 enum；W2 抽样后再决定是否收紧，避免在无真实样本时过度约束。

### Part C 陷阱核查（18 项）

- C1 通过：`backend/app/` / `backend/scripts/` 无未标注 `print()` 调试残留
- C2 通过：无新增 stdlib `import logging`
- C3 通过：无硬编码 URL、端口、模型名、秘钥或业务阈值
- C4 通过：无新增无说明 `# type: ignore`
- C5 通过：无 `except: pass` / `except Exception: pass`
- C6 通过：未知异常使用 `raise MetadataExtractError() from exc`
- C7 通过：BytesIO/文件和外部 client 生命周期由库/现有抽象管理，无泄漏
- C8 通过：未给 `get_llm()` 或副作用工厂新增缓存
- C9 N/A：本任务无 API endpoint
- C10 通过：async 路径中的 pypdf/pdf2image 已线程卸载
- C11 通过：新增配置全部走 settings
- C12 N/A：未新增环境变量
- C13 通过：`config.yaml` 已同步
- C14 通过：新增依赖和 license 已在 §5 说明
- C15 通过：mock 只隔离外部 LLM；路由、解析、ACL、异常和数据库约束执行真实逻辑
- C16 通过：公共抽取入口、模型契约和主要 helper 均有对应测试
- C17 通过：import smoke / mypy / 完整 pytest 通过，无循环依赖
- C18 通过：`DocumentMetaCreate` 下游调用契约已同步；无 API 调用方

**ANTIPATTERNS.md 显式对照**：

- I1 sub-agent 协作：未派 sub-agent。Task 0、migration、ORM、schema、service 和测试高度耦合，由主 agent 集中维护并在集成后执行完整验收。
- J1 路由分流：N/A，本任务无 API/router。
- K1 脱敏：N/A 于 API response；本任务无 endpoint。`MetadataExtractError` 对外通用化，路径不进入错误消息或 review reason；未来 API 必须额外 sanitize `doc_path`。

### Part D 人工触发

- D1-D2：不适用；有效新增超过 1000 行。
- D3 Hard：排除 lock、handoff、tasks/reviews 后有效新增 `1176` 行，禁止自动合并。
- D4 Hard：修改 7 个 main 上已有非 lock 文件，必须人工 review。
- D5：新增 Jinja2/PyPDF/pdf2image/Pillow；前三者为允许 license，Pillow `MIT-CMU` 交 reviewer 确认。
- D6 Hard：修改 `backend/app/core/config.py` 和 `backend/app/core/exceptions.py`。
- D7：无公共 API 删除或重命名。
- D8：本地 Part A 无失败；首次 CI 只因 Handoff 尚未创建而 A7 失败。
- D9：Part C 无失败。
- D10：coverage `86%`，相对上一轮 `85%` 无下降。
- D11：3 条偏差，未超过阈值。

### Part E 自我反思

**E1 三个改进点**：

1. 当前 `backend/app/models/product_kb_metadata.py:52` 使用通用 `FieldConfidence`，重做时会在真实 5 文档样本验证后评估字段专用泛型/模型，以更早拦截 enum 漂移。本次不收紧是因为 IP-Guard 模块枚举尚未经过 W2 抽样。
2. 当前 `backend/app/services/product_kb_extract.py:121` 每次调用创建 Jinja2 Environment，重做时可评估无副作用模板缓存。本次不改是因为单文档 lean MVP 无性能证据，且要避免给涉及文件系统的工厂过早加缓存。
3. 当前 `backend/migrations/versions/0003_document_meta_acl_align.py:29` 按 spec 将所有旧 sensitivity 折叠为 `3`。有真实历史数据时应先设计显式值映射或离线清洗；本次不扩展是因为当前表为空且 Task 0 契约锁定。

**E2 忠告**：不要把 `_route_by_extension()` 返回 VISION 理解为 Office/图片转换已经实现；当前公共抽取入口会对这些扩展名主动失败并交给人工审核，Phase 2 必须单独设计转换器。

**E3 新发现反模式**：同一扩展名的“路由分类”与“可执行转换能力”容易被混为一谈。当前通过公共入口主动失败、脱敏 review reason 和精确测试名锁定边界；未修改 `ANTIPATTERNS.md`，因为这是本任务已记录的 Phase 2 产品边界，尚未形成跨任务反复出现的通用反模式。

### 修复轨迹

- fix_attempt:0：Task 0 和主体均按 TDD 先观察失败，再实现至目标、全量、迁移和静态检查全部通过；无完成后修复轮次。
- CI 首次 run `27431635538`：仅 A7 因 Handoff 尚未创建失败；本文件推送后重新复现。

### 总评

**NEEDS_HUMAN（必须人工 review，不自动合并）**

原因：本地 Part A 与 Part C 已通过，但 Part D 明确命中 D3、D4、D6 Hard；同时 `0003` 对未来已有数据环境存在有损迁移风险。按任务锁定规则直接上报 reviewer。

**last_verified_commit**: `587aa33c660bdd5a207b37451759539ac97f0c10`
