# 任务 #28：结构化双轨入库逻辑

> **版本**：v1.0
> **创建日期**：2026-06-05
> **预估工时**：1.5 工作日
> **前置任务**：#24 主数据表 + #25 抽取 + #27 审核 Excel + #63 RustFS 存储 + #19 Embedding 抽象
> **后续任务**：#29 异步入库 endpoint + #30 正式跑批入库
> **优先级**：🔴 高（W2 关键周主线）

---

## §1 任务背景

文档入库不是单一动作，按类型走不同路径：
- **结构化 Excel**（维保记录 / 客户清单）→ pandas 读 → 写入 PG 业务表
- **非结构化文档**（合同 / 方案 / 报告）→ 解析 → 切片 → bge-m3 → Qdrant
- **视觉文档**（PPT / 带图 PDF）→ 每页转 PNG → Omni 描述 → 入 Qdrant
- 所有路径都**同时写 `document_meta`**（带 Q1 5 字段 ACL + customer_id 等元数据）
- 原文件**统一进 RustFS**（铁律：业务码禁止直连 boto3）

本任务实现这套路由逻辑。

---

## §2 范围

- ✅ `backend/app/services/ingest.py`（统一入口 + 3 路径分发）
- ✅ `backend/app/services/ingest_text.py`（非结构化 → Qdrant）
- ✅ `backend/app/services/ingest_vision.py`（视觉 → Omni 描述 → Qdrant）
- ✅ `backend/app/services/ingest_structured.py`（Excel → PG 业务表，#28 范围内只做 maintenance_records 一类示范）
- ✅ Qdrant 入库 metadata 注入（customer_id / doc_type / event_date / ACL 5 字段）
- ✅ 原文件 RustFS 落地（走 `services/storage.py`）
- ✅ document_meta 表写入
- ✅ 单元 + 集成测试

- ❌ 不做异步 endpoint（#29）
- ❌ 不做 400 份跑批（#30）

---

## §3 任务目标

1. `ingest_document(doc_meta_row, doc_bytes)` 统一入口：判类型 → 分发到 3 路径
2. 所有路径成功后：
   - 原文件存 RustFS（key = doc_id）
   - 写 `document_meta` 行（status=`ingested`）
   - Qdrant chunks 带 metadata：`customer_id` / `doc_type` / `event_date` / `audience` / `visibility` / `owner_dept`
3. 任一步失败 → 整份回滚（PG 事务 + Qdrant 已写 chunks 删除 + RustFS 已存对象删除）
4. 测试覆盖三路径成功 + 失败回滚 + metadata 注入完整 ≥ 12 项

---

## §4 文件清单

### 4.1 `backend/app/services/ingest.py`（新建统一入口）

```python
async def ingest_document(
    session: AsyncSession,
    *,
    meta: ApprovedMetaRow,    # 来自 metadata_approved.xlsx 单行
    doc_bytes: bytes,
    doc_path: str,
) -> IngestResult:
    """统一入口。按 doc_type / 文件后缀分发。"""
    route = _route(meta.doc_type, doc_path)
    try:
        if route == IngestRoute.STRUCTURED:
            stats = await ingest_structured.ingest(session, meta, doc_bytes)
        elif route == IngestRoute.VISION:
            stats = await ingest_vision.ingest(session, meta, doc_bytes)
        else:
            stats = await ingest_text.ingest(session, meta, doc_bytes)
        await _persist_storage_and_meta(session, meta, doc_bytes, route, stats)
        return IngestResult(doc_id=meta.doc_id, route=route, **stats)
    except Exception:
        await _rollback(session, meta.doc_id)  # 删 Qdrant + RustFS + PG
        raise
```

### 4.2 `backend/app/services/ingest_text.py`

- 解析（PyPDF / docx2txt / markdown）→ LlamaIndex chunk → bge-m3 embed → Qdrant upsert
- 每个 chunk payload 注入 metadata（5 ACL 字段 + customer_id + chunk_idx）

### 4.3 `backend/app/services/ingest_vision.py`

- PPT/PDF → PNG（pdf2image）→ Omni VLM 描述每页 → 描述文本作为 chunk
- chunk metadata 加 `chunk_type=vision_desc` + `page_no`

### 4.4 `backend/app/services/ingest_structured.py`

- 判 Excel sheet 结构 → 路由到具体业务表（本任务示范 `maintenance_records`，新建一个 ORM model）
- 字段映射走显式 mapping dict，不靠列名猜
- 同步也写 document_meta（status=`ingested`，但 storage_key 指原 Excel）

### 4.5 `backend/app/db/models/maintenance_record.py`（示范业务表）

```python
class MaintenanceRecord(Base):
    __tablename__ = "maintenance_record"
    id: int (pk)
    doc_id: str (fk document_meta.doc_id)
    customer_id: int (fk customer.id)
    record_date: datetime
    record_type: str
    description: Text
    created_at: datetime
```

### 4.6 `backend/migrations/versions/0003_maintenance_record.py`

按 #24 模式手写，含 fk 约束 + 索引。

### 4.7 `backend/tests/services/test_ingest.py`（≥ 12 项）

- 三路径各成功 1 项
- 三路径各失败回滚 1 项
- Qdrant payload 含 5 ACL 字段断言
- RustFS 落地后能 load 回 bytes
- document_meta 行 status=ingested
- 失败时 PG 事务回滚 + Qdrant 已写 chunks 被删 + RustFS 对象被删

---

## §5 验收

```powershell
& uv run pytest tests/services/test_ingest.py -v          # ≥ 12 passed
& uv run pytest -m "not integration" --cov=app
& uv run alembic upgrade head    # 0003 应用
& uv run ruff check . ; & uv run mypy app
```

---

## §6 风险

| 风险 | 缓解 |
|------|------|
| 三路径回滚不彻底 | 显式 `_rollback`，测试断言 RustFS / Qdrant / PG 都干净 |
| Excel sheet 结构千变万化 | #28 范围只示范 maintenance_records 一种，其他类型后续扩 |
| Qdrant 与 PG 一致性（写 Q 成功写 PG 失败）| PG 事务在最外层，Qdrant 写成功后立刻写 PG；PG 失败 → 删 Qdrant |
| Embedding 调用慢 | `services/llm.get_embedding()` 已有 batch，每文档内部 batch 32 |

### 新增依赖

- `pypdf>=4`（PDF 文本提取）
- `docx2txt>=0.8` 或 `python-docx`（Word 文本提取）

---

## §7 禁止事项

- ❌ 直接 `import boto3`（走 `services/storage.py`）
- ❌ 直接 `from qdrant_client import ...`（走 `services/qdrant.py` 抽象，#19 已建）
- ❌ 直连 Embedding（走 `get_embedding()`）
- ❌ 任一路径失败不回滚就 raise（必须先回滚再 raise）
- ❌ Qdrant payload 漏掉任一 ACL 5 字段（#42 ACL filter 会失效）
- ❌ 硬编码 chunk_size（走 settings）

---

## §8 参考

- `docs/tasks/W2-D1-24-customer-master-data.md` § document_meta + Q1 5 字段
- `docs/tasks/W1-D4-20-min-rag-pipeline.md` § Qdrant payload schema
- `docs/handoffs/W2-D0-63-handoff.md` § RustFS storage 接口

---

_v1.0 | 2026-06-05_
