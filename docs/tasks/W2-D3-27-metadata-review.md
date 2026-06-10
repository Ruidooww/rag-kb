# 任务 #27：业务方分组审核元数据

> **版本**：v1.0
> **创建日期**：2026-06-05
> **预估工时**：脚本 0.5 工作日 + 业务方审核 6-8 小时/人（三组并行）
> **前置任务**：#26 输出 metadata.xlsx + 🔴 **业务方排期就位**
> **后续任务**：#30 用审核通过的 metadata.xlsx 正式入库
> **优先级**：🔴 高（W2 关键周主线，元数据准确率 ≥ 95% 的关键人工环节）

---

## §1 任务背景

#26 用 Omni 抽取的元数据有误差（客户匹配错 / 文档类型判断偏 / 敏感度漏判）。W2 末的硬指标是"抽检准确率 ≥ 95%"，靠业务方人工审核兜底。

本任务是 **流程任务 + 校验工具**：把 metadata.xlsx 拆给三组业务方审核，审核完用脚本校验 + 合并回单一可入库 Excel。

三组分工（按任务清单）：
- 销售组：~合同/方案/客户文档
- 售后组：~实施/维保/培训
- 产品组：~产品文档/FAQ

---

## §2 范围

- ✅ `backend/scripts/split_for_review.py`（按 owner_dept / doc_type 拆成三个分组 Excel）
- ✅ `backend/scripts/validate_review.py`（校验业务方填回的 Excel：必填项 / 枚举合法 / customer_id 存在）
- ✅ `backend/scripts/merge_reviewed.py`（三组合并回单一 `metadata_approved.xlsx`）
- ✅ 审核操作说明文档 `docs/sop/metadata-review-guide.md`
- ✅ 校验脚本测试

- ❌ 不做 Web 审核 UI（用 Excel，Phase 2 再考虑）
- ❌ 不做入库（#30）

---

## §3 任务目标

1. `split_for_review.py` 按 `owner_dept`（或 doc_type 归类规则）把 metadata.xlsx 拆成 `review_sales.xlsx` / `review_service.xlsx` / `review_product.xlsx`
2. 拆分时 `needs_review=是` 的行排在每个 Excel 顶部（业务方优先看）
3. `validate_review.py` 校验业务方填回的 Excel：
   - `review_status` ∈ {approved, rejected, pending}，不能有空
   - `reviewed_customer_id` 必须在 customer 表存在（或显式 null for 通用文档）
   - `reviewed_doc_type` ∈ doc_type 枚举
   - rejected 行必须填 `review_reasons`
4. `merge_reviewed.py` 合并三组 → `metadata_approved.xlsx`，只保留 `review_status=approved` 行，输出统计（通过/拒绝/待定数）
5. 校验失败给出**精确到行号 + 列名**的错误清单，业务方据此修正
6. 测试：拆分 / 校验各分支 / 合并 ≥ 8 项

---

## §4 文件清单

### 4.1 `backend/scripts/split_for_review.py`（新建）

要点：
- 读 metadata.xlsx（用 `_xlsx_schema.METADATA_COLUMNS`）
- 归类规则：优先 `reviewed_customer_id` 为空时按 `doc_type` 映射到组（合同→销售 / 维保→售后 / 产品→产品），映射表走 config 或脚本内常量 + 注释
- 每组 Excel `needs_review=是` 行置顶（pandas sort）
- 输出三个 Excel + 一份 `review_assignment.md`（哪组多少份）

### 4.2 `backend/scripts/validate_review.py`（新建）

要点：
```python
"""校验业务方填回的审核 Excel。

用法:
    uv run python scripts/validate_review.py ./review_sales_done.xlsx
退出码 0 = 全通过；1 = 有错误（清单打印 + 写 validation_errors.txt）
"""
# 校验项：
#   - review_status 非空且 ∈ 枚举
#   - approved 行 reviewed_doc_type ∈ doc_type 枚举
#   - reviewed_customer_id 非空时必须 DB 存在（async 查 customer_repo.get_by_id）
#   - rejected 行必须有 review_reasons
# 错误格式: "Row 23 [客户ID]: customer_id 999 不存在于 customer 表"
```

### 4.3 `backend/scripts/merge_reviewed.py`（新建）

要点：
- 读三个 done Excel → 先各自跑 validate（不通过则拒绝合并）
- 只保留 `review_status=approved`
- 输出 `metadata_approved.xlsx`（#30 入库直接读这个）
- 统计：总数 / approved / rejected / pending，写 `review_summary.md`

### 4.4 `docs/sop/metadata-review-guide.md`（新建）

业务方操作手册（非技术向）：
- 怎么打开分组 Excel
- 每列含义（特别是 needs_review / review_status 怎么填）
- 重点审核哪些（客户ID / 敏感度 / 文档类型）
- 填完怎么交回

### 4.5 `backend/tests/scripts/test_review_pipeline.py`（新建）

测试场景（≥ 8 项）：
- `test_split_routes_by_doc_type`
- `test_split_puts_needs_review_first`
- `test_validate_rejects_empty_status`
- `test_validate_rejects_invalid_doc_type`
- `test_validate_rejects_nonexistent_customer_id`
- `test_validate_requires_reason_for_rejected`
- `test_merge_keeps_only_approved`
- `test_merge_refuses_if_validation_fails`

---

## §5 验收标准

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'
& uv run pytest tests/scripts/test_review_pipeline.py -v   # ≥ 8 passed
& uv run pytest -m "not integration" --cov=app
& uv run ruff check . ; & uv run ruff format --check . ; & uv run mypy app

# 端到端（用样本数据）
& uv run python scripts/split_for_review.py ./metadata.xlsx
& uv run python scripts/validate_review.py ./review_sales.xlsx
& uv run python scripts/merge_reviewed.py ./review_*.xlsx
```

---

## §6 风险 & 已知问题

| 风险 | 缓解 |
|------|------|
| 业务方改坏 Excel 列结构（删列/改表头）| validate 脚本先校验列完整性，缺列直接报错 |
| 三组对同一份文档归类有歧义 | split 按 doc_type 主归类 + 重叠文档可多组看（标记 shared）|
| 业务方审核进度拖慢 W2 | 本任务交付脚本即可；实际审核排期是项目管理事项（你推进）|
| customer_id 校验需要连 DB | validate 脚本 async 查 PG；离线场景可加 `--skip-db-check` flag |

### 新增依赖

无（复用 #24 #26 的 pandas / openpyxl / sqlalchemy）。

---

## §7 禁止事项

- ❌ Excel 列定义不复用 `_xlsx_schema.py`（必须共用，防漂移）
- ❌ merge 时跳过 validate（必须先校验通过才合并）
- ❌ 校验错误信息不带行号/列名（业务方无法定位）
- ❌ 把真实审核 Excel（含真实客户）提交到 git
- ❌ 在脚本里硬编码 doc_type → 组 映射（走常量 + 注释说明，或 config）

---

## §8 参考

- `docs/tasks/W2-D2-26-batch-metadata-extract.md` § _xlsx_schema
- `docs/tasks/W2-D1-24-customer-master-data.md` § customer_repo
- `docs/RAG知识库_数据治理SOP.docx`（审核 SOP 母文档）

---

_v1.0 | 2026-06-05_
