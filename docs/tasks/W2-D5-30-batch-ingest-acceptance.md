# 任务 #30：400 份文档正式入库 + 抽检

> **版本**：v1.0
> **创建日期**：2026-06-05
> **预估工时**：脚本 0.5 工作日 + 跑批 2-6 小时 + 抽检 0.5 工作日
> **前置任务**：#27 metadata_approved.xlsx + #28 ingest_document + 🔴 **400 份原文件就位**
> **后续任务**：#31 黄金评估集（W3 D1）
> **优先级**：🔴 高（W2 关键周收尾，决定 Phase 1 数据治理成败）

---

## §1 任务背景

W2 末硬节点：400 份文档全部入库 + 抽检准确率 ≥ 95%。本任务用审核通过的 `metadata_approved.xlsx` 跑 `batch_ingest.py`，监控进度 + 抽检 50 份。

跟 #26 区别：#26 是**抽取**（输出 Excel），本任务是**入库**（写 PG + Qdrant + RustFS）。
跟 #29 区别：#29 是**单份 API**（前端用），本任务是**批量 CLI**（一次性跑完）。

---

## §2 范围

- ✅ `backend/scripts/batch_ingest.py`（读 metadata_approved.xlsx → 并发跑 ingest_document）
- ✅ `backend/scripts/spot_check.py`（抽检：随机 50 份核对入库后字段）
- ✅ 抽检报告生成（准确率 / 失败清单 / 待重做清单）
- ✅ 进度持久化（断点续跑）
- ✅ W2 入库报告模板 `docs/handoffs/W2-D5-30-handoff.md`（不是 spec，是结果产出）

- ❌ 不实现新业务表（沿用 #28 maintenance_record）
- ❌ 不做评估集（#31）

---

## §3 任务目标

1. `batch_ingest.py metadata_approved.xlsx ./historical_docs` 把 400 份并发入库（concurrency = `settings.ingest_concurrency`）
2. 单份失败不中断整批，记录到 `ingest_failed.jsonl`
3. 断点续跑：扫 document_meta 表 status=`ingested` 的 doc_id 跳过
4. 跑完输出统计：成功 / 失败 / 跳过 / 总耗时 / Qdrant chunks 总数 / RustFS 字节总量
5. `spot_check.py` 随机抽 50 份，校验：customer_id 正确 / doc_type 正确 / Qdrant 能检索到 / RustFS 能 load 回原文件
6. 准确率 < 95% 时**报警停下**，需要 #27 补审
7. 测试：mock ingest，覆盖并发 / 失败隔离 / 断点续跑 / 抽检准确率计算 ≥ 6 项

---

## §4 文件清单

### 4.1 `backend/scripts/batch_ingest.py`（新建）

```python
"""批量入库。读 metadata_approved.xlsx → 并发 ingest_document。

用法:
    uv run python scripts/batch_ingest.py ./metadata_approved.xlsx ./historical_docs
"""
# 核心结构：
# 1. df = pd.read_excel(approved_xlsx)  # 列符合 _xlsx_schema
# 2. async with SessionLocal() as session:
#        done_ids = await document_meta_repo.list_doc_ids_by_status(session, "ingested")
# 3. todo = [row for row in df.itertuples() if row.doc_id not in done_ids]
# 4. sem = asyncio.Semaphore(settings.ingest_concurrency)
# 5. async def _one(row):
#        async with sem:
#            try:
#                bytes_ = (docs_dir / row.doc_path).read_bytes()
#                async with SessionLocal() as s:
#                    await ingest_document(s, meta=_to_meta(row), doc_bytes=bytes_, doc_path=row.doc_path)
#                    await s.commit()
#                return ("ok", row.doc_id)
#            except Exception as exc:
#                logger.error(...)
#                _append_failed_jsonl(row.doc_id, str(exc))
#                return ("failed", row.doc_id)
# 6. 用 tqdm.asyncio.tqdm.gather 跑
# 7. 输出 ingest_summary.md
```

### 4.2 `backend/scripts/spot_check.py`（新建）

```python
"""W2 抽检脚本。随机抽 50 份核对入库正确性。

校验项：
- document_meta 行存在 + status=ingested
- customer_id ∈ customer 表
- RustFS 能 load 回 bytes（size > 0）
- Qdrant 该 doc_id 至少 1 个 chunk
- 5 ACL 字段非空（owner_dept / audience / visibility / sensitivity / shared_depts）

输出 spot_check_report.md：
- 总抽样 N / 通过 / 失败
- 准确率
- < 95% 告警
"""
```

### 4.3 `backend/tests/scripts/test_batch_ingest.py`（≥ 6 项）

- `test_skips_already_ingested`
- `test_concurrency_respects_limit`
- `test_single_failure_recorded_not_aborts`
- `test_summary_counts_correct`
- `test_spot_check_calculates_accuracy`
- `test_spot_check_warns_below_threshold`

### 4.4 `docs/handoffs/W2-D5-30-handoff.md`（跑批结果模板）

预填模板，跑批后业务方/Codex 填实际数：
- 总份数 / 成功 / 失败 / 跳过
- 总耗时 / 单份均耗时
- Qdrant chunks 总数 + 平均每份 chunks
- RustFS 占用字节
- 抽检 50 份准确率
- 失败 doc_id 清单 + 失败原因 Top-N
- 实际百炼费用（控制台拉）
- 下一步建议（如准确率 < 95% 怎么办）

### 4.5 `backend/app/db/repos/document_meta.py`（追加）

`list_doc_ids_by_status(session, status: str) -> set[str]` —— 断点续跑用。

---

## §5 验收

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'

# 1. 测试
& uv run pytest tests/scripts/test_batch_ingest.py -v   # ≥ 6 passed
& uv run pytest -m "not integration" --cov=app

# 2. 跑批（需要 400 份就位）
& uv run python scripts/batch_ingest.py ../metadata_approved.xlsx ../historical_docs

# 3. 抽检
& uv run python scripts/spot_check.py --sample 50
# 输出 spot_check_report.md，准确率 ≥ 95% 算 W2 通过

# 4. 一致性校验
$pgCount = (& uv run python -c "import asyncio; from app.db.base import SessionLocal; from app.db.repos.document_meta import count_ingested; print(asyncio.run(count_ingested(...)))")
# 应等于 metadata_approved.xlsx 行数
```

---

## §6 风险

| 风险 | 缓解 |
|------|------|
| 准确率 < 95% | spot_check 报警后停下；改流程：补 #27 审核 → 重跑 ingest |
| 跑批费用超预算（Embedding + VLM）| #26 已估单份成本；跑批前先跑 30 份预热估总费用 |
| 中途百炼 API 限流 | 失败重试机制（指数退避，可选）；调小 concurrency |
| Qdrant collection 满 | 1024 维 × 400 文档 × 平均 30 chunks ≈ 12K vectors，远低于限制 |
| RustFS 空间 | 400 文档平均 5MB ≈ 2GB，本地 disk 够用 |
| 跑到一半 Ctrl-C | 断点续跑救场，已 ingested 的 status 留在 PG 里 |

### 新增依赖

无（复用 #26 #28 已装）。

---

## §7 禁止事项

- ❌ 不做抽检直接宣布 W2 完成（W2 末硬指标 ≥ 95% 必须有数据支撑）
- ❌ 抽检 < 50 份样本（统计意义不够）
- ❌ 跑批前不做小批预热（费用失控）
- ❌ 把真实 `metadata_approved.xlsx` / `ingest_summary.md` 含真实客户数据的产物 commit 到 git
- ❌ 失败 doc_id 不写 `ingest_failed.jsonl` 就 `pass`（必须可追溯）
- ❌ 单份失败 `raise` 中断整批

---

## §8 参考

- `docs/tasks/W2-D3-28-dual-track-ingest.md` § ingest_document
- `docs/tasks/W2-D3-27-metadata-review.md` § metadata_approved.xlsx 列定义
- `docs/RAG知识库_完整任务书_V2.0.docx` § Week 2 验收标准

---

_v1.0 | 2026-06-05_
