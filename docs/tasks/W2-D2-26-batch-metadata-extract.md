# 任务 #26：批量元数据抽取（400 份）

> **版本**：v1.0
> **创建日期**：2026-06-05
> **预估工时**：0.5 工作日（脚本）+ 1-2 小时（实际跑批）
> **前置任务**：#25 单份抽取能力 + #24 客户主数据 + 🔴 **400 份原文件就位**
> **后续任务**：#27 业务方审核 metadata.xlsx
> **优先级**：🔴 高（W2 关键周主线）

---

## §1 任务背景

#25 提供了单份文档抽取能力，本任务把它批量化：扫描历史文档目录，并发抽取所有文档，输出一份 `metadata.xlsx` 供业务方审核（#27）。

关键约束：
- 并发受控（`settings.ingest_concurrency`，默认 5）避免打爆百炼 QPS
- 失败文档不中断整批，单独记录到失败清单
- 低置信度 / 客户未命中的项在 Excel 里高亮标记，供 #27 重点审核
- 输出 Excel 列结构必须跟 #27 审核流程对齐

---

## §2 范围

- ✅ `backend/scripts/batch_extract.py`（扫目录 + 并发抽取 + 输出 Excel）
- ✅ 并发控制（asyncio.Semaphore）+ 进度条（tqdm）
- ✅ 失败文档清单（failed_docs.jsonl）
- ✅ 置信度低 / 客户未命中标记列
- ✅ 断点续跑（已抽取的跳过，基于输出 Excel 已有行）
- ✅ 脚本级测试（mock extract_metadata，验并发 / 失败隔离 / Excel 列）

- ❌ 不做入库（#28）
- ❌ 不做审核 UI（#27 用 Excel 人工改）

---

## §3 任务目标

1. `batch_extract.py <input_dir> <output_xlsx>` 扫描目录所有支持格式，并发抽取
2. 并发上限 = `settings.ingest_concurrency`，用 `asyncio.Semaphore` 控制
3. 单份失败（抽取异常 / JSON 错）记录到 `failed_docs.jsonl`，**不中断整批**
4. 输出 `metadata.xlsx`：每行一份文档，列含 6 元数据字段 + confidence + customer_id + needs_review + review_reasons + 原文件路径
5. `needs_review=True` 的行在 Excel 里标记（单独 `_needs_review` 列 = "是"，供 #27 筛选）
6. 断点续跑：重跑时已在输出 Excel 里的 doc_path 跳过
7. 测试：mock `extract_metadata`，覆盖并发执行 / 失败隔离 / Excel 列完整 / 断点续跑 ≥ 6 项

---

## §4 文件清单

### 4.1 `backend/scripts/batch_extract.py`（新建）

要点：
```python
"""批量元数据抽取。

用法:
    uv run python scripts/batch_extract.py ./historical_docs ./metadata.xlsx
"""
# 核心结构（伪代码）：
# 1. scan_dir → 收集所有支持格式文件路径
# 2. load_done(output_xlsx) → 已抽取的 doc_path 集合（断点续跑）
# 3. sem = asyncio.Semaphore(settings.ingest_concurrency)
# 4. async def _one(path):
#        async with sem:
#            try: return await extract_metadata(path)
#            except Exception as exc:  # 记录失败，不抛
#                logger.warning(...); append failed_docs.jsonl; return None
# 5. results = await asyncio.gather(*[_one(p) for p in todo])
# 6. write_xlsx(results) → pandas DataFrame → openpyxl，needs_review 行标记
# 7. logger.info 总结：成功 N / 失败 M / 跳过 K
```

约束：
- `print()` 仅限 CLI 进度输出加 `# noqa: T201`；其余走 loguru
- tqdm 进度条包 `asyncio.as_completed`
- Excel 列顺序固定（供 #27 对齐），列名中文 + 英文 key 双行表头可选

### 4.2 `backend/scripts/_xlsx_schema.py`（新建，共享列定义）

定义 `METADATA_COLUMNS`（list[tuple[key, 中文表头]]），#26 写 + #27 读 + #28 读共用同一份，避免列名漂移。

```python
METADATA_COLUMNS = [
    ("doc_path", "文件路径"),
    ("doc_type", "文档类型"),
    ("doc_type_conf", "类型置信度"),
    ("customer_name", "客户名(抽取)"),
    ("customer_id", "客户ID(匹配)"),
    ("customer_match_score", "匹配分"),
    ("event_date", "业务日期"),
    ("product", "产品"),
    ("event_type", "事件类型"),
    ("sensitivity", "敏感度"),
    ("needs_review", "需审核"),
    ("review_reasons", "审核原因"),
    # #27 业务方填写列：
    ("reviewed_customer_id", "审核后客户ID"),
    ("reviewed_doc_type", "审核后文档类型"),
    ("review_status", "审核状态"),  # pending/approved/rejected
]
```

### 4.3 `backend/tests/scripts/test_batch_extract.py`（新建）

测试场景（≥ 6 项，mock `extract_metadata`）：
- `test_scans_all_supported_formats`
- `test_concurrency_respects_semaphore_limit`
- `test_single_failure_does_not_abort_batch`
- `test_failed_docs_written_to_jsonl`
- `test_resume_skips_already_extracted`
- `test_output_xlsx_has_all_columns`

---

## §5 验收标准

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'
& uv run pytest tests/scripts/test_batch_extract.py -v   # ≥ 6 passed
& uv run pytest -m "not integration" --cov=app
& uv run ruff check . ; & uv run ruff format --check . ; & uv run mypy app
```

实际跑批（需 400 份就位 + 真实 API key）：
```powershell
& uv run python scripts/batch_extract.py ./historical_docs ./metadata.xlsx
# 监控：成功率 / 失败清单 / 总耗时 / 百炼费用（控制台）
```
Handoff §4 必须记录：总份数 / 成功 / 失败 / needs_review 占比 / 实际耗时 / 估算费用。

---

## §6 风险 & 已知问题

| 风险 | 缓解 |
|------|------|
| 百炼 QPS 限流 | Semaphore 限并发 + 失败重试（指数退避，可选）|
| 400 份跑批费用超预算 | 先跑 10 份估单份成本 × 400；超 ¥X 停下问用户 |
| 大文件 OOM（视觉文档转 PNG）| `vision_max_pages` 限制 + 单份处理完释放 |
| Excel 写入被占用（用户开着）| 写临时文件再 rename；或加时间戳后缀 |
| 部分文档格式不支持（.doc 老格式 / 加密 PDF）| 记入失败清单，#27 人工处理 |

### 新增依赖

- `tqdm>=4.66`（进度条，MPL/MIT）

---

## §7 禁止事项

- ❌ 单份失败 `raise` 中断整批（必须 catch + 记录 + 继续）
- ❌ 硬编码并发数（走 `settings.ingest_concurrency`）
- ❌ 硬编码输入/输出路径（走 CLI 参数）
- ❌ Excel 列名跟 #27 / #28 不一致（必须共用 `_xlsx_schema.py`）
- ❌ 跑批前不做 10 份成本估算就直接全量（费用失控风险）
- ❌ 提交真实 `metadata.xlsx`（含真实客户）到 git（.gitignore 排除）

---

## §8 参考

- `docs/tasks/W2-D2-25-omni-metadata-extract.md` § extract_metadata
- `docs/tasks/W2-D1-24-customer-master-data.md` § customer_match
- `CLAUDE.md` v1.2 § 铁律 #2 #6 + § 禁止 print

---

_v1.0 | 2026-06-05_
