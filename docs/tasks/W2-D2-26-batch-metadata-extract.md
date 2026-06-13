# 任务 #26：批量产品 KB 元数据抽取（199 份）

> **版本**：v2.0（lean MVP 重写，对齐 #25 v2）
> **创建日期**：v1.0 2026-06-05 / v2.0 2026-06-13
> **预估工时**：脚本 0.5 工作日 + 实际跑批 0.5-2 小时
> **前置任务**：#25 v2 已 merge（PR #18 / commit `18b5d16`）+ #25 follow-up（PR #19）+ 199 份就位 `C:\Users\Ruidoww\Documents\IPG知识库构建`
> **后续任务**：#27 业务方审核 metadata.xlsx → #28 双轨入库
> **优先级**：🔴 高（W2 主线，lean MVP 关键节点）

---

## §1 任务背景

#25 v2 提供单份 IP-Guard 产品资料抽取能力（`extract_product_kb_metadata`），本任务把它批量化：扫描 199 份产品资料目录，受控并发抽取，输出 `metadata.xlsx` 供你（lean MVP 阶段一人审）人工审核（#27），再灌入 Qdrant（#28）。

### 与 v1.0 的关键变更

v1.0 写于 #25 v2 重写之前，假设客户档案抽取 + customer_match 流程。lean MVP 锁定后整个语境转向产品 KB，本 v2.0 全面对齐：

| 维度 | v1.0（过期） | v2.0（当前） |
|---|---|---|
| 入口函数 | `extract_metadata` | `extract_product_kb_metadata(doc_path, doc_bytes)` |
| 抽取字段 | doc_type / customer_name / event_date / product / event_type / sensitivity | product_module / product_version / platform / target_audience / doc_category / sensitivity |
| 客户匹配 | 调 `customer_match.match()` | ❌ 不抽客户、不匹配 customer 表留空 |
| 数据规模 | 400 份历史档案 | 199 份 IP-Guard 产品资料 |
| 失败语义 | 单份失败 → `failed_docs.jsonl` | `MetadataExtractError` 是**预期**（不支持扩展名 / JSON 解析） → 进 needs_review 行；意外异常才进 `failed_docs.jsonl` |
| ACL 字段 | 无 | 5 字段 ACL（audience/visibility/owner_dept/shared_depts + sensitivity 1-5）随抽取入 xlsx |

### 数据现状

- 路径：`C:\Users\Ruidoww\Documents\IPG知识库构建`
- 数量：199 份 / 333 MB
- 格式：PDF 194（97.5%）+ xlsx 2 + doc 1 + jpg 2
- 含子目录，需递归扫描

---

## §2 范围

- ✅ `backend/scripts/batch_extract_product_kb.py`（扫目录 + 受控并发 + 输出 Excel）
- ✅ 并发控制（`asyncio.Semaphore(settings.ingest_concurrency)`，默认 5）
- ✅ 进度条（tqdm 包 `as_completed`）
- ✅ `MetadataExtractError` 转 needs_review 行写入 xlsx（不进 failed_docs.jsonl）
- ✅ 意外异常 → `failed_docs.jsonl`（含扩展名 + 异常类名，**不含路径**）
- ✅ 断点续跑（已抽取的 doc_path 跳过，基于现有 xlsx 已写入行）
- ✅ 共享列定义 `backend/scripts/_xlsx_schema.py`（#26 写、#27 读、#28 读共用）
- ✅ 脚本级测试（mock 入口，验并发 / 失败隔离 / 断点续跑 / 列完整 ≥ 7 项）

- ❌ 不入库（#28）
- ❌ 不抽客户名、不调 customer_match、不写 customer 表
- ❌ 不做审核 UI（#27 用 Excel 人工改）
- ❌ 不在脚本里加重试 / 限流（百炼 QPS 由 Semaphore 控制；失败由 needs_review 兜底）

---

## §3 任务目标

1. `batch_extract_product_kb.py <input_dir> <output_xlsx>` 递归扫描目录支持格式
2. 并发上限 = `settings.ingest_concurrency`，用 `asyncio.Semaphore` 控制
3. 调 `extract_product_kb_metadata(doc_path, doc_bytes)` 入口（不要碰已删的 `_route_by_extension`）
4. `MetadataExtractError`（不支持扩展名 / JSON 解析失败 / 低置信度）→ 写一行 xlsx，`needs_review=True`，对应字段值留空，review_reasons 从异常带出
5. 意外异常（OOM / IO / pdf2image 崩溃）→ `failed_docs.jsonl` 追加 `{doc_path, ext, error_type}`，**不写路径之外的内部细节**
6. 输出 `metadata.xlsx`：每行 = 一份文档，列 = `_xlsx_schema.METADATA_COLUMNS` 定义
7. 断点续跑：重跑时已在 xlsx 里的 `doc_path` 跳过；用 `pandas.read_excel` 读已写
8. 测试 ≥ 7 项（mock 入口，覆盖并发上限 / `MetadataExtractError` 转 needs_review / 意外异常隔离 / 断点续跑 / 列完整 / 进度条不抛 / 失败 jsonl 不含路径外细节）

---

## §4 文件清单

### 4.1 `backend/scripts/_xlsx_schema.py`（新建，共享列定义）

```python
"""Shared xlsx schema for #26 write / #27 review / #28 ingest read.

Single source of truth for column key / Chinese header / data type.
Any column change must update tests/scripts/test_xlsx_schema.py snapshot.
"""

from __future__ import annotations

METADATA_COLUMNS: list[tuple[str, str]] = [
    # 抽取字段（来自 ProductKBMetadata 6 个 FieldConfidence）
    ("doc_path", "文件路径"),
    ("extract_method", "抽取路径"),  # text / vision
    ("product_module", "产品模块"),
    ("product_module_conf", "模块置信度"),
    ("product_version", "产品版本"),
    ("product_version_conf", "版本置信度"),
    ("platform", "平台"),
    ("platform_conf", "平台置信度"),
    ("target_audience", "目标用户"),
    ("target_audience_conf", "目标用户置信度"),
    ("doc_category", "文档类型"),
    ("doc_category_conf", "类型置信度"),
    ("sensitivity", "敏感度"),  # int 1-5
    ("sensitivity_conf", "敏感度置信度"),
    # ACL 派生（来自 _apply_acl_defaults）
    ("audience", "受众边界"),
    ("visibility", "可见性"),
    ("owner_dept", "归属部门"),
    ("shared_depts", "跨部门白名单"),
    # 审核
    ("needs_review", "需审核"),  # 是 / 否
    ("review_reasons", "审核原因"),  # 用 " | " 连接
    # #27 业务方填写列（写入时留空）
    ("reviewed_product_module", "审核后产品模块"),
    ("reviewed_doc_category", "审核后文档类型"),
    ("reviewed_sensitivity", "审核后敏感度"),
    ("review_status", "审核状态"),  # pending / approved / rejected
]
```

### 4.2 `backend/scripts/batch_extract_product_kb.py`（新建）

要点：

```python
"""Batch extract product KB metadata for lean MVP IP-Guard 199 docs.

Usage:
    uv run python scripts/batch_extract_product_kb.py \
        "C:/Users/Ruidoww/Documents/IPG知识库构建" \
        ./data/metadata.xlsx
"""
# 核心结构（伪代码）：
# 1. scan_dir(input_dir) → list[Path]，递归 + 过滤 _SUPPORTED_INPUT_EXTENSIONS
#    支持集合：.pdf .txt .md .pptx .xlsx .doc .jpg（后 4 类会进 needs_review）
#    不在集合的扩展名：跳过，不计入 todo
# 2. load_done(output_xlsx) → set[str]，已抽取的 doc_path
#    若 xlsx 不存在，返回空集
# 3. todo = [p for p in scanned if str(p) not in done]
# 4. sem = asyncio.Semaphore(settings.ingest_concurrency)
# 5. async def _one(path: Path) -> _Row:
#        async with sem:
#            doc_bytes = await asyncio.to_thread(path.read_bytes)
#            try:
#                meta = await extract_product_kb_metadata(str(path), doc_bytes)
#                return _row_from_meta(meta)
#            except MetadataExtractError as exc:
#                return _row_from_extract_error(str(path), exc)
#            except Exception as exc:
#                _append_failed_jsonl(failed_path, path, exc)
#                logger.warning("Unexpected failure {} {}",
#                               path.suffix.lower() or "<none>",
#                               type(exc).__name__)
#                return None
# 6. results = []
#    async for row in _iter_completed(todo): ... # tqdm 包 as_completed
# 7. _append_rows_to_xlsx(output_xlsx, results)
#    断点续跑：用 pandas.read_excel 读已有 + concat 新行，写临时再 rename
# 8. logger.info "成功 N / needs_review M / 意外失败 K / 跳过 (已存在) S"
```

约束：
- 入口固定 `extract_product_kb_metadata`，不要复用任何 `_route_*` 私有 helper
- `print()` 仅 CLI 启动/结束摘要可用 + `# noqa: T201`；其余 loguru
- tqdm 进度条只显示「已完成 / 总数」+ 当前扩展名，**不显示路径**
- Excel 写入：临时 `*.xlsx.tmp` → `os.replace`，避免用户开着 xlsx 锁文件
- `failed_docs.jsonl` 每行 `{"doc_path": str(path), "ext": ".xlsx", "error_type": "RuntimeError"}` —— 不含 traceback、不含异常 message
- `_row_from_extract_error`：抽取字段 + 置信度全留空（None / 0），`needs_review=True`，`review_reasons = exc.review_reasons or ["MetadataExtractError"]`
- 共享列 `METADATA_COLUMNS` 单源真相，DataFrame 列顺序按 key 顺序对齐

### 4.3 `backend/tests/scripts/test_batch_extract_product_kb.py`（新建 ≥ 7 项）

全部 mock `extract_product_kb_metadata`：

- `test_scans_supported_extensions_recursively`
- `test_concurrency_respects_semaphore_limit`（用 `asyncio.Event` 校验同时 in-flight ≤ N）
- `test_metadata_extract_error_writes_needs_review_row`
- `test_unexpected_exception_appends_failed_jsonl_without_path_internals`（断言 jsonl 行只含 doc_path / ext / error_type 三个 key）
- `test_resume_skips_already_extracted_doc_paths`
- `test_output_xlsx_has_all_columns_from_schema`（snapshot 对齐 `METADATA_COLUMNS`）
- `test_progress_bar_does_not_log_doc_path`（caplog / capsys 验进度条不暴露路径）

### 4.4 `backend/tests/scripts/test_xlsx_schema.py`（新建）

- `test_metadata_columns_snapshot`：固定 24 列（按 4.1 列表），任何变更必须显式更新快照
- `test_extracted_field_keys_match_product_kb_metadata`：6 个抽取字段 key 跟 `ProductKBMetadata` 字段名一致（防漂移）
- `test_acl_field_keys_match_document_meta_anchor`：4 个 ACL key 跟 PR #13 锚点 `DocumentMetaSchema` 字段名一致

### 4.5 `backend/pyproject.toml`（追加依赖）

```toml
"tqdm>=4.66",      # MIT，进度条
"pandas>=2.2",     # BSD-3-Clause，xlsx 读写
"openpyxl>=3.1",   # MIT，pandas xlsx 引擎
```

注：`pandas` + `openpyxl` 同时引入，写 `pd.ExcelWriter(engine="openpyxl")` 显式指定，避免落到不可控默认。

### 4.6 `.gitignore` 追加

```
# #26 批量抽取产出（含真实产品资料映射，不入库）
backend/data/metadata.xlsx
backend/data/metadata.xlsx.tmp
backend/data/failed_docs.jsonl
```

---

## §5 验收标准

### 5.1 自动化（spec lock）

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'

& uv run pytest tests/scripts/test_batch_extract_product_kb.py -v   # ≥ 7 passed
& uv run pytest tests/scripts/test_xlsx_schema.py -v                # ≥ 3 passed
& uv run pytest -m "not integration" --cov=app                      # 全量增量 ≥ +10 passed
& uv run ruff check . ; & uv run ruff format --check . ; & uv run mypy app
& uv run mypy scripts                                                # 脚本也要过 mypy

# 铁律 grep
Select-String -Path "backend/scripts/batch_extract_product_kb.py" `
  -Pattern "import dashscope|from openai|qwen|gte-rerank|os.getenv|os.environ"
# 应全部无命中
```

### 5.2 实际跑批（人工，验收前先跑 5 份试水）

**Step 1**：先抽 5 份代表性文档估单份成本

```powershell
# 复制 5 份代表性资料到 ./data/sample_5/
# 例如：
#   - Web 控制台使用说明.pdf（user_manual / 文本路径）
#   - Mac客户端安装说明.pdf（deployment / 可能视觉）
#   - IP-Guard产品测试用例（全模块）.pdf（test_case）
#   - V4.86 版本更新.pdf（release_note）
#   - 某模块故障排查.pdf（troubleshoot）

& uv run python scripts/batch_extract_product_kb.py ./data/sample_5 ./data/metadata_sample.xlsx
```

- 单份成本 × 199 估算总费用（仅记录，不阈值阻塞）
- 抽取准确率人工核对 5 份：每个字段对/错记入 Handoff §4
- 路由分布（text vs vision）记 Handoff §4

**Step 2**：全量 199 份

```powershell
& uv run python scripts/batch_extract_product_kb.py `
    "C:\Users\Ruidoww\Documents\IPG知识库构建" `
    ./data/metadata.xlsx
```

- Handoff §4 必填：总份数 / 成功 / needs_review / 意外失败 / 实际耗时 / 估算费用 / 路由分布

---

## §6 风险 & 已知问题

| 风险 | 缓解 |
|---|---|
| 百炼 QPS 限流（429） | Semaphore=5 控并发；若仍 429 → 失败转 needs_review，不重试 |
| 大 PDF OOM（视觉路径转 PNG） | `vision_max_pages=20` 已限；单份处理完释放 buffer |
| Excel 写入被占用（用户开着 xlsx） | 写 `.xlsx.tmp` + `os.replace`；被占用时 retry 一次再 raise |
| `.xlsx / .doc / .jpg / .pptx` 5 份边界 | 入口抛 `MetadataExtractError`，自动进 needs_review；你 30 分钟手填即可 |
| 同名带后缀文件（`(1)` / 日期）| 本任务不去重；#27 / #28 处理 |
| Windows 路径中文 + 反斜杠 | `Path()` + `str(path)` 统一；不要拼 f-string |
| 进度条泄漏路径 | 只显示 `已完成/总数 + ext`；测试断言 capsys 无路径 |

### 新增第三方依赖

- `tqdm` MIT / `pandas` BSD-3-Clause / `openpyxl` MIT — 均在白名单

---

## §7 禁止事项

- ❌ 调任何 #25 私有 helper（如已删的 `_route_by_extension`）；只用 `extract_product_kb_metadata` 公共入口
- ❌ `MetadataExtractError` 当作"失败"丢进 `failed_docs.jsonl`（它是预期 needs_review）
- ❌ 在 `failed_docs.jsonl` / 进度条 / logger 里输出 traceback / 异常 message / 路径之外的内部细节
- ❌ 单份意外失败 `raise` 中断整批（必须 catch + 记录 + 继续）
- ❌ 硬编码并发数 / 输入/输出路径 / 模型名（全部走 settings + CLI 参数）
- ❌ Excel 列名跟 `_xlsx_schema.METADATA_COLUMNS` 不一致（必须共用单源真相）
- ❌ 跑全量 199 份前不做 5 份试水（准确率失控风险）
- ❌ 提交真实 `metadata.xlsx` / `failed_docs.jsonl` 到 git（.gitignore 必须先就位）
- ❌ 调用 `customer_match` / 抽取客户名 / 写 customer 表（违反 lean MVP 边界）
- ❌ 业务代码 `import dashscope` / `from openai` / 直连模型（铁律 #1）

---

## §8 参考

- `backend/app/services/product_kb_extract.py:42` `extract_product_kb_metadata` 入口
- `backend/app/models/product_kb_metadata.py:59` `ProductKBMetadata` schema
- `backend/app/core/exceptions.py:24` `MetadataExtractError(needs_review, review_reasons)`
- `backend/app/core/config.py:57` `ingest_concurrency`
- `docs/handoffs/W2-D2-25-handoff.md` §7 ACL 映射表
- `docs/reviews/PR-18.md` §6 F2（#28 入库前 0003 dry-run 提醒）
- `CLAUDE.md` v1.2 § 铁律 #1 #2 #6 + 原则 P1（脱敏）

---

_v2.0 | 2026-06-13 | lean MVP 重写：199 份产品 KB、入口对齐 #25 v2、MetadataExtractError 转 needs_review_
