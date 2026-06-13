# Codex 派单 prompt — 任务 #26

> **生成日期**：2026-06-13
> **用途**：lean MVP 路径 W2-D2 派单，#25 v2 + follow-up 已 merge 后下一步
> **使用方法**：复制下方代码块整段（从 `# 任务 #26` 到结尾）发给 Codex
> **配套阅读**：`docs/STATUS-2026-06-12.md` + `CLAUDE.md`（自动加载）
> **派单 prompt 设计要点**：
> - 3 道防漂移锁（任务编号 + spec 路径 + 分支名）
> - 入口物理锁定（`extract_product_kb_metadata`，禁止任何私有 helper）
> - 失败语义二分（MetadataExtractError 转 needs_review 行 vs 意外异常 jsonl）
> - 跑批前 5 份试水硬约束（费用 + 准确率）

---

## 派单 prompt 全文（直接复制给 Codex）

```text
# 任务 #26：批量产品 KB 元数据抽取（199 份，L1 标准）

请按以下规格执行。

## 🔒 任务锁定（避免走错任务）

- 本轮**只做** #26，**禁止**任何 #27 #28 #29 #30 #31 #32 #25b 范围工作
- 本轮 spec 唯一路径：`docs/tasks/W2-D2-26-batch-metadata-extract.md`（v2.0，lean MVP 重写）
- 本轮分支名唯一：`feat/W2-D2-26-batch-extract`
- Step 1 创建分支前必须 assert 分支名跟以上完全一致；不一致直接停下问用户
- spec 顶部明确：**v2.0 lean MVP 重写**，v1.0（客户档案抽取语境）已过期，不要参考

## 项目位置
C:\Users\Ruidoww\Desktop\RAG

## 必读文档（按顺序）

1. CLAUDE.md（v1.2，重点：铁律 #1 #2 #6 + 原则 P1 脱敏 + 原则 P4）
2. docs/CODEX_QUICK_REF.md（v1.2 速查卡）
3. docs/STATUS-2026-06-12.md（**必读 — lean MVP 路径全景**）
4. docs/tasks/W2-D2-26-batch-metadata-extract.md（本任务唯一 spec，v2.0）
5. docs/handoffs/W2-D2-25-handoff.md（上一轮 #25 v2，重点 §7 ACL 映射 + §5 已知风险）
6. docs/reviews/PR-18.md（#25 review，§6 F2 = #28 前 0003 dry-run 提醒；F1 = 已删孤儿函数）
7. backend/app/services/product_kb_extract.py（**入口签名锁定，本任务调用唯一入口**）
8. backend/app/models/product_kb_metadata.py（ProductKBMetadata schema）
9. backend/app/core/exceptions.py（MetadataExtractError 携带 needs_review + review_reasons）
10. backend/app/core/config.py（`ingest_concurrency` / `extract_confidence_threshold` 已就位）

## 分支名（本轮强制使用）
feat/W2-D2-26-batch-extract

## 本轮关键边界

### 入口物理锁定（最重要）

- ✅ 唯一允许调用：`from app.services.product_kb_extract import extract_product_kb_metadata`
- ❌ **禁止**调任何 `_route_*` / `_extract_pdf_text` / `_to_pngs` / `_call_llm_*` 私有 helper（PR #19 已删过一个孤儿 `_route_by_extension`，本任务不允许重蹈）
- ❌ 禁止在脚本里复用 `pdf2image` / `pypdf` 做"自己的路由判定"——所有判定走入口

### 失败语义二分（spec §3.4 + §3.5）

- `MetadataExtractError`（不支持扩展名 / JSON 解析失败 / 低置信度）= **预期失败**
  - 写一行 xlsx：抽取字段全留空（None / 0 confidence），`needs_review=True`
  - `review_reasons = exc.review_reasons or ["MetadataExtractError"]`
  - **不**进 `failed_docs.jsonl`
- 意外异常（OOM / IO / pdf2image 崩溃）= **真失败**
  - 进 `failed_docs.jsonl`，每行 3 个 key：`{doc_path, ext, error_type}`
  - **禁止**写 traceback / 异常 message / 路径外内部细节
  - logger.warning 只记扩展名 + 异常类名

### 共享 schema 单源（spec §4.1）

- ✅ `backend/scripts/_xlsx_schema.py::METADATA_COLUMNS` 是 #26/#27/#28 共用单源
- ❌ 禁止脚本里 inline 列名 / 中文表头
- 列变更必须同步更新 `tests/scripts/test_xlsx_schema.py` 快照

### 脱敏（原则 P1）

- 进度条 / logger / failed_docs.jsonl 中**只允许出现** `doc_path` 字段值本身（已是必要业务字段）
- 禁止：traceback、异常 message、临时路径、用户主目录展开后的别名
- 进度条只显示「N/M + 当前扩展名」，不显示文件名/路径

### lean MVP 边界（spec §2）

- ❌ 不抽客户名 / 不调 `customer_match.match()` / 不写 customer 表
- ❌ 不入库（#28 才做）
- ❌ 不在脚本里加重试 / 限流（失败由 needs_review 兜底，百炼 QPS 由 Semaphore 控制）

### 铁律对照

- 铁律 #1：脚本不能 `import dashscope` / `from openai`；调入口已经透传 `get_llm()`
- 铁律 #2 + #6：`ingest_concurrency` / `extract_confidence_threshold` 走 settings，**禁止**硬编码并发数 / 阈值
- 铁律 #5：脚本不写超 3 行的 prompt（本任务零 prompt，全部由 #25 入口处理）

## 执行原则

1. 严格遵守 CLAUDE.md 十条铁律 + 横切原则 P1 P4
2. 严格按 spec §4.1-§4.6 文件清单（4 文件：1 schema + 1 脚本 + 2 测试）
3. 本任务级别：**L1 标准** → Step 2 简短复述（≤ 3 句）+ 等用户 confirm
4. Step 7 任一 ❌ 必须停下修复（≤ 3 轮）
5. 遇 spec 模糊（pandas xlsx 续写策略 / asyncio.as_completed 用法 / Windows 中文路径）必须停下问
6. **跑全量 199 份前必须先 5 份试水**（spec §5.2 Step 1）——这是硬约束，违反 = 任务重做
7. 推 PR 前必须本地全验收通过；Handoff §4 真实输出不能编造

## Step 2 复述要点（≤ 3 句）

复述时必须命中：

1. 入口锁定 `extract_product_kb_metadata`，禁止任何 #25 私有 helper
2. 失败语义二分（MetadataExtractError → needs_review 行 vs 意外异常 → jsonl）
3. lean MVP 不扩范围（不抽客户、不入库、不调 customer_match）

## 验收硬指标

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'

# 目标测试
& uv run pytest tests/scripts/test_batch_extract_product_kb.py -v   # ≥ 7 passed
& uv run pytest tests/scripts/test_xlsx_schema.py -v                # ≥ 3 passed

# 全量
& uv run pytest -m "not integration" --cov=app                      # ≥ 161 passed（原 151 + 10）
& uv run ruff check . ; & uv run ruff format --check .
& uv run mypy app ; & uv run mypy scripts                            # 脚本也要过 mypy

# 铁律 grep（无命中）
Select-String -Path "backend/scripts/batch_extract_product_kb.py","backend/scripts/_xlsx_schema.py" `
  -Pattern "import dashscope|from openai|qwen|gte-rerank|os\.getenv|os\.environ"

# 入口锁定 grep（无命中）—— 禁止脚本调任何 #25 私有 helper
Select-String -Path "backend/scripts/batch_extract_product_kb.py" `
  -Pattern "_route_|_extract_pdf_text|_to_pngs|_call_llm_|_build_metadata|_apply_acl_defaults"

# jsonl 脱敏断言（在测试里硬断言）
# test_unexpected_exception_appends_failed_jsonl_without_path_internals
#   断言每行 json keys == {"doc_path", "ext", "error_type"}
```

## 实际跑批（自动化全过 + Step 2 复述用户 confirm 后才能跑）

```powershell
# Step A：5 份试水（强制）
& uv run python scripts/batch_extract_product_kb.py ./data/sample_5 ./data/metadata_sample.xlsx
# 停下：估单份成本 × 199（仅记录）；准确率人工核对 5 份；路由分布写 Handoff §4

# Step B：全量 199 份（用户放行后）
& uv run python scripts/batch_extract_product_kb.py `
    "C:\Users\Ruidoww\Documents\IPG知识库构建" `
    ./data/metadata.xlsx
```

`data/sample_5/` 5 份样本由用户提供清单（5 类 doc_category 各 1 份）——派单时未提供则在 Step 2 复述里追问。

## 提交规范

- 单 squash commit subject：`feat: #26 batch extract product KB metadata (199 docs)`
- Body 含：覆盖铁律（#1 + #2 + #6）+ 原则 P1 脱敏 + 失败语义二分 + `_xlsx_schema` 单源 + 验收数据 + 「为 #27 审核 + #28 入库留稳定 xlsx 契约」声明
- `Refs: #26`
- Co-Authored-By: Codex

按 Step 1 开始执行。Step 2 复述完等用户 confirm 才能进 Step 3。
```

---

## 派单后预期流程

1. Codex 收到 prompt → Step 1 创建分支 `feat/W2-D2-26-batch-extract`
2. Step 2 读完必读文档 → 给出 ≤ 3 句复述（命中入口锁定 / 失败二分 / lean MVP 边界）
3. **你转给 Claude 核对**：
   - 入口锁定是否点到（不许调任何 #25 私有 helper）
   - 失败语义二分（MetadataExtractError vs 意外异常）有没有点到
   - 5 份试水样本清单 Codex 是否主动追问
4. 没问题 → 你回 Codex「confirm，进 Step 3」（顺手提供 sample_5 清单）
5. Codex 自跑 Step 3-7（实现 + 测试）
6. Step 8 5 份试水跑批 → Handoff §4 写入路由分布 + 准确率 + 单份成本
7. 你 review 试水结果 → 放行 / 调阈值后再放行全量
8. Codex 跑全量 → Handoff §4 完整数据 → PR
9. PR 上来 → Claude 写 review → 你 squash merge

## 故障 / 偏差处理

| 情况 | 处理 |
|---|---|
| Codex 复述漏了入口锁定 | 让它重新复述，强调禁止任何 #25 私有 helper |
| Codex 想 import `_route_by_extension` | 立刻打断，该函数 PR #19 已删（参考 review §6 F1）|
| Codex 在脚本里复用 pypdf/pdf2image 自己判路由 | 立刻打断，引用「入口物理锁定」段 |
| Codex 把 MetadataExtractError 丢进 failed_docs.jsonl | 立刻打断，引用「失败语义二分」段 |
| Codex 在 jsonl / 进度条里写 traceback / 路径外细节 | 立刻打断，引用「脱敏」段 + 原则 P1 |
| Codex 想调 customer_match / 抽客户名 | 立刻打断，引用 lean MVP 边界 |
| Codex 跳过 5 份试水直接跑全量 | 立刻打断，spec §5.2 Step 1 是硬约束 |
| Codex 自合并 PR（D3/D4/D6 触发）| NEEDS_HUMAN 上报，不自合并 |

---

_文件版本：v1.0 | 2026-06-13_
