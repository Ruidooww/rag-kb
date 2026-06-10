# 任务 #29：FastAPI BackgroundTasks 异步入库 + 进度查询

> **版本**：v1.0
> **创建日期**：2026-06-05
> **预估工时**：1 工作日
> **前置任务**：#28 ingest_document + #67 IdP（user 鉴权）+ 原则 P3（internal_router）
> **后续任务**：#30 跑批入库 + Phase 2 前端文档管理页
> **优先级**：🟡 中（W2 主线，但可与 #30 并行）

---

## §1 任务背景

#28 实现了核心入库逻辑（同步函数）。生产场景需要：
- 用户上传文档 → API 立刻返回 202 + doc_id，不阻塞
- 后台异步跑入库（解析 / embed / Qdrant / RustFS / PG 全套）
- 前端轮询进度查询 → 显示状态条
- 失败可重试

本任务用 FastAPI `BackgroundTasks` 包 `ingest_document`，加上状态机 + 进度查询 endpoint。

---

## §2 范围

- ✅ `POST /api/v1/internal/documents/upload`（multipart + 元数据 JSON）
- ✅ `GET /api/v1/internal/documents/{doc_id}/status`
- ✅ `POST /api/v1/internal/documents/{doc_id}/retry`
- ✅ document_meta 状态机：`uploaded → ingesting → ingested | failed`
- ✅ BackgroundTasks 包 ingest + 失败重试逻辑
- ✅ 挂 internal_router（原则 P3）
- ✅ 测试（mock ingest_document + 状态轮询 + 重试）

- ❌ 不做公开上传（外部用户不能传文档）
- ❌ 不做批量上传（#30 用 CLI 批量）
- ❌ 不做 WebSocket 推送进度（轮询够用）

---

## §3 任务目标

1. 上传 endpoint 接受 multipart 文件 + JSON 元数据（doc_type / customer_id / 5 ACL 字段）
2. 立刻写 document_meta status=`uploaded`，返回 202 + doc_id
3. BackgroundTasks 异步跑 `ingest_document`，状态推进
4. 失败时 status=`failed` + `error_message` 记录原因
5. Retry endpoint 把 status=`failed` 重置回 `uploaded` 重跑
6. Status endpoint 返回 status + progress 百分比（粗粒度：0/30/70/100）+ error_message
7. 所有 endpoint 经 `Depends(get_current_user)` 鉴权，**只允许 internal user**（铁律 #10 layer 2）
8. 测试 ≥ 10 项

---

## §4 文件清单

### 4.1 `backend/app/api/documents.py`（新建）

```python
internal_router = APIRouter(prefix="/documents", tags=["documents"])

@internal_router.post("/upload", status_code=202)
async def upload(
    file: UploadFile, meta_json: str = Form(...),
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> UploadResponse:
    _require_internal(user)
    meta = ApprovedMetaRow.model_validate_json(meta_json)
    doc_id = _gen_doc_id(meta)
    await document_meta_repo.create(session, doc_id, meta, status="uploaded")
    bytes_ = await file.read()
    background.add_task(_run_ingest, doc_id, bytes_, meta)
    return UploadResponse(doc_id=doc_id, status="uploaded")
```

### 4.2 `backend/app/api/document_status.py`（新建）

```python
@internal_router.get("/{doc_id}/status")
async def status(doc_id: str, user: User = Depends(get_current_user), ...) -> StatusResponse:
    _require_internal(user)
    meta = await document_meta_repo.get_by_doc_id(session, doc_id)
    if meta is None: raise HTTPException(404)
    return StatusResponse(
        doc_id=doc_id, status=meta.status, progress=_progress(meta.status),
        error_message=meta.error_message,
    )

@internal_router.post("/{doc_id}/retry")
async def retry(doc_id: str, background: BackgroundTasks, ...) -> StatusResponse:
    _require_internal(user)
    meta = await document_meta_repo.get_by_doc_id(session, doc_id)
    if meta.status != "failed": raise HTTPException(409, "Only failed documents can retry")
    await document_meta_repo.set_status(session, doc_id, "uploaded", error=None)
    bytes_ = await storage.load(doc_id)  # 从 RustFS 拉回原文件
    background.add_task(_run_ingest, doc_id, bytes_, meta.to_approved_row())
    return StatusResponse(...)
```

### 4.3 `backend/app/api/_internal_guard.py`（新建辅助）

```python
def _require_internal(user: User) -> None:
    if user.is_external:
        raise PermissionDeniedError("Permission denied")  # 同 N1 不回显
```

### 4.4 `backend/app/services/_run_ingest.py`（BackgroundTasks worker）

```python
async def _run_ingest(doc_id: str, doc_bytes: bytes, meta: ApprovedMetaRow) -> None:
    async with SessionLocal() as session:
        try:
            await document_meta_repo.set_status(session, doc_id, "ingesting")
            await ingest_document(session, meta=meta, doc_bytes=doc_bytes, doc_path=doc_id)
            await document_meta_repo.set_status(session, doc_id, "ingested")
            await session.commit()
        except Exception as exc:
            logger.error("Ingest failed doc_id={} err={}", doc_id, exc)
            async with SessionLocal() as s2:
                await document_meta_repo.set_status(s2, doc_id, "failed", error=str(exc))
                await s2.commit()
```

### 4.5 `backend/migrations/versions/0004_document_meta_status_error.py`

给 document_meta 加 `error_message: Text nullable=True` 列（如果 #24 没加）。

### 4.6 `backend/tests/api/test_documents.py`（≥ 10 项）

- `test_upload_returns_202_with_doc_id`
- `test_upload_persists_meta_with_uploaded_status`
- `test_upload_triggers_background_ingest`
- `test_external_user_upload_returns_403`
- `test_external_user_status_returns_403`
- `test_status_returns_404_for_unknown_doc`
- `test_retry_only_works_for_failed_status`
- `test_retry_resets_to_uploaded`
- `test_status_error_message_persisted_on_failure`
- `test_progress_mapping`

---

## §5 验收

```powershell
& uv run pytest tests/api/test_documents.py -v   # ≥ 10 passed
& uv run pytest -m "not integration" --cov=app
& uv run alembic upgrade head
& uv run mypy app

# 路由分流验证
grep -nE "include_router.*documents" backend/app/api/router.py
# 必须挂在 internal_router 下，不能在 public_router / 顶层 api_router
```

---

## §6 风险

| 风险 | 缓解 |
|------|------|
| BackgroundTasks 进程崩溃 task 丢失 | MVP 可接受；生产换 Celery/RQ（Phase 2 backlog）|
| 大文件上传超时 | uvicorn timeout 调大；前端切片上传是 Phase 2 |
| 并发上传打爆 | Phase 1 内部使用，30 人量级 OK；后续加限流 |
| Retry 无限循环 | retry 端点要求 status=failed 才允许；不自动 retry |
| upload 时 user 不在 customer ACL 内 | #42 ACL 中间件兜底，本任务先不做（Handoff §7 标注）|

---

## §7 禁止事项

- ❌ 挂在 public_router 或顶层 api_router（违反原则 P3）
- ❌ external user 能 reach 任一 endpoint（违反铁律 #10 layer 2）
- ❌ `PermissionDeniedError` 错误信息回显 doc_id / 工具名（N1 复盘）
- ❌ BackgroundTasks worker 抛异常不写 status=failed（必须 catch 写 PG）
- ❌ Retry 重新走 storage.load 失败时不报错（RustFS 拿不回原文件 → 显式 raise）

---

## §8 参考

- `docs/tasks/W2-D3-28-dual-track-ingest.md` § ingest_document
- `CLAUDE.md` v1.2 § 原则 P3 + § 铁律 #10
- `docs/reviews/PR-15.md` § N1 错误信息脱敏

---

_v1.0 | 2026-06-05_
