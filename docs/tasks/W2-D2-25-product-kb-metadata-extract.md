# 任务 #25：产品 KB 元数据自动抽取（含 Task 0 契约修复）

> **版本**：v2.0（lean MVP 重写）
> **创建日期**：2026-06-12
> **预估工时**：Task 0 修契约 1.5 小时 + 主体抽取 1 工作日 = ~1.2 工作日
> **前置任务**：#24 已 merge（PR #17 / commit `75cec60`）+ #19 LLM 抽象层 + #67 LocalIdP
> **后续任务**：#26 跑 199 份批量抽取（lean MVP）
> **优先级**：🔴 高（W2 主线，阻塞 #26 / #28 / #30）

---

## §1 任务背景

lean MVP 范围已锁定（详见 `docs/REQUIREMENTS-v2.md` 或会话纪要）：

- **目标用户**：实施 + 售后（W4 末全员 30 人开放测试）
- **数据**：199 份 IP-Guard 产品资料（PDF 194 / xlsx 2 / doc 1 / jpg 2），333 MB
- **场景**：售后查产品配置策略 + 实施远程时快速查文档
- **砍掉**：客户档案 / 客户对比 / 服务路径 / 关系图 / 4 IdP 真实接入 / 多租户

本任务负责把这 199 份产品资料抽取成结构化 metadata，供 #26 批量化 + #28 入库 + #29-#30 实际跑批。

**关键转向（vs v1）**：
- ❌ 不抽客户名（199 份是产品 KB，没有客户绑定）
- ❌ 不调用 `customer_match.match()`（customer 表 lean MVP 留空）
- ✅ 抽取字段重定义：**产品模块 / 版本 / 平台 / 目标用户 / 文档类型 / 敏感度**

---

## §2 Task 0（前置）：修 DocumentMetaSchema 契约不一致

PR #17 (#24) 实施后发现：PR #13 锚定的 Pydantic `DocumentMetaSchema` 跟 #24 新建 ORM `DocumentMeta` **5 个 ACL 字段里 3 个红、1 个黄、1 个绿**。本任务**实施前**必须先修。

### 2.1 字段差异修复表

| 字段 | PR #13 Pydantic（锚定，不动） | 当前 #24 ORM | 修后 ORM |
|------|---------------|--------------|---------|
| `audience` | `Audience` StrEnum / 默认 `INTERNAL_ONLY` | `String(32)` / 默认 `"internal"` | `String(32)` / 默认 `"internal_only"` + check constraint |
| `owner_dept` | `str \| None`（可空）| `nullable=False` 必填 | **`nullable=True`** |
| `visibility` | `Visibility` StrEnum / 默认 `INTERNAL` | `String(32)` / 默认 `"internal"` | `String(32)` / 默认 `"internal"` + check constraint |
| `sensitivity` | `int` 1-5 / 默认 3 | **`String(32)` / 默认 "normal"** | **`Integer` / 默认 `3` + check (1-5)** |
| `shared_depts` | `list[str]` | `ARRAY(String(32))` | 不变 ✓ |

### 2.2 实现

- **新建 `backend/migrations/versions/0003_document_meta_acl_align.py`**：ALTER `document_meta` 表
  - `audience`: UPDATE 所有 "internal" → "internal_only"（lean MVP 当前是空表，no-op，但写完整 SQL）
  - `owner_dept`: ALTER COLUMN DROP NOT NULL
  - `sensitivity`: ALTER COLUMN TYPE Integer USING (CASE "normal" THEN 3 ELSE 3 END) + ADD CHECK (sensitivity BETWEEN 1 AND 5)
- **改 `backend/app/db/models/document_meta.py`**：5 个字段类型对齐到上表"修后 ORM"列
- **改 `backend/app/db/repos/document_meta.py`**：参数签名跟新类型对齐（sensitivity 接受 int 不是 str）
- **加测试 `backend/tests/db/test_document_meta_acl_contract.py`**（≥ 5 项）：
  - `test_audience_default_is_internal_only`
  - `test_owner_dept_can_be_null`
  - `test_sensitivity_is_int_range_1_to_5`
  - `test_sensitivity_check_constraint_rejects_0_and_6`
  - `test_orm_matches_pydantic_schema`（用 Pydantic schema 构造 dict → 写入 ORM 不抛错）

### 2.3 Task 0 验收

```powershell
& uv run alembic upgrade head             # 应用到 0003
& uv run alembic downgrade -1             # 回到 0002
& uv run alembic upgrade head             # 再次到 0003
& uv run pytest tests/db/test_document_meta_acl_contract.py -v   # ≥ 5 passed
```

完成后进入主体 §3。

---

## §3 主体任务目标

1. `extract_product_kb_metadata(doc_path, doc_bytes)` 输入单份产品资料，返回 `ProductKBMetadata`
2. **路径分发**：纯文本 PDF → text 路径；带图密集 PDF / PPT / xlsx → vision 路径（截图 + Omni VLM）
3. 抽取字段：
   - `product_module`：IP-Guard 模块（客户端 / 服务器 / 加密 / 网关 / 审批 / 数据分析 / ...）
   - `product_version`：版本号（如 V4 / 4.86.1941 / 4.6-4.8）或 None
   - `platform`：Windows / Mac / Linux / Web / 多平台
   - `target_audience`：管理员 / 实施 / 售后 / 销售 / 客户
   - `doc_category`：使用说明 / 部署文档 / FAQ / 测试用例 / 版本更新 / 故障排查
   - `sensitivity`：1-5 整数（公开使用说明=1，部署讲义=3，测试用例=4-5）
   - `audience` / `owner_dept` / `visibility` / `shared_depts`：按 doc_category 默认填（不靠 LLM）
4. 低置信度（任一字段 conf < `settings.extract_confidence_threshold`，默认 70）→ `needs_review=True`
5. 所有 LLM/VLM 调用走 `app.services.llm`（铁律 #1）
6. Prompt 在 `prompts/extract_product_kb.txt`（铁律 #5）
7. 测试 ≥ 9 项（mock get_llm，覆盖路径分发 / 字段抽取 / 低置信度标记 / JSON 解析失败）

---

## §4 文件清单

### 4.1 `backend/prompts/extract_product_kb.txt`（新建 jinja2）

```jinja2
你是 IP-Guard 产品文档元数据抽取专家。从以下产品资料中抽取结构化元数据。

## 抽取目标
判断这份产品文档涉及的：模块、版本、平台、目标用户、文档类型、敏感度。

## 字段枚举

### product_module（IP-Guard 模块，必选其一或多个用 "+" 连接）
{{ product_module_enum }}

### platform（必选一）
{{ platform_enum }}

### target_audience（必选一）
{{ target_audience_enum }}

### doc_category（必选一）
{{ doc_category_enum }}

### sensitivity（必选 1-5 的整数）
- 1: 公开使用说明（普通客户都能看）
- 2: 内部公开（员工都能看）
- 3: 内部限制（默认）
- 4: 部门机密（特定部门可见）
- 5: 高敏感（高管 + HR + 测试用例 / 安全策略源码）

## 待抽取文档内容

{{ doc_content }}

## 输出格式（严格 JSON，无 markdown 包裹）

```json
{
  "product_module": {"value": "...", "confidence": 0-100},
  "product_version": {"value": "...或null", "confidence": 0-100},
  "platform": {"value": "...", "confidence": 0-100},
  "target_audience": {"value": "...", "confidence": 0-100},
  "doc_category": {"value": "...", "confidence": 0-100},
  "sensitivity": {"value": 1-5整数, "confidence": 0-100}
}
```

不要输出 JSON 以外的任何文字。关键信息（版本号、模块名）必须来自文档原文。
```

### 4.2 `backend/app/models/product_kb_metadata.py`（新建）

```python
from __future__ import annotations
from enum import StrEnum
from pydantic import BaseModel, Field
from app.models.document_meta import Audience, Visibility


class ProductModule(StrEnum):
    CLIENT = "client"
    SERVER = "server"
    ENCRYPTION = "encryption"
    GATEWAY = "gateway"
    APPROVAL = "approval"
    DATA_ANALYSIS = "data_analysis"
    LICENSE = "license"
    BACKUP = "backup"
    SENSITIVE_DETECTION = "sensitive_detection"
    OTHER = "other"


class Platform(StrEnum):
    WINDOWS = "windows"
    MAC = "mac"
    LINUX = "linux"
    WEB = "web"
    MULTI = "multi"


class TargetAudience(StrEnum):
    ADMIN = "admin"
    IMPLEMENTATION = "implementation"
    AFTERSALES = "aftersales"
    SALES = "sales"
    CUSTOMER = "customer"


class DocCategory(StrEnum):
    USER_MANUAL = "user_manual"
    DEPLOYMENT = "deployment"
    FAQ = "faq"
    TEST_CASE = "test_case"
    RELEASE_NOTE = "release_note"
    TROUBLESHOOT = "troubleshoot"
    OTHER = "other"


class ExtractMethod(StrEnum):
    TEXT = "text"
    VISION = "vision"


class FieldConfidence(BaseModel):
    value: str | int | None = None
    confidence: int = Field(ge=0, le=100, default=0)


class ProductKBMetadata(BaseModel):
    doc_path: str
    extract_method: ExtractMethod
    product_module: FieldConfidence
    product_version: FieldConfidence
    platform: FieldConfidence
    target_audience: FieldConfidence
    doc_category: FieldConfidence
    sensitivity: FieldConfidence  # value is int 1-5

    # 由 doc_category 派生（不靠 LLM），直接填:
    audience: Audience = Audience.INTERNAL_ONLY
    visibility: Visibility = Visibility.INTERNAL
    owner_dept: str | None = None
    shared_depts: list[str] = Field(default_factory=list)

    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
```

### 4.3 `backend/app/services/product_kb_extract.py`（新建核心）

要点：
```python
async def extract_product_kb_metadata(
    doc_path: str,
    doc_bytes: bytes,
) -> ProductKBMetadata:
    """单份产品资料抽取入口。"""
    method = _route(doc_path)  # ext-based: .pptx/.xlsx/带图密集.pdf → VISION; else TEXT
    if method == ExtractMethod.TEXT:
        doc_content = _extract_text(doc_path, doc_bytes)
        raw = await _call_llm_text(doc_content)
    else:
        images = _to_pngs(doc_path, doc_bytes, max_pages=settings.vision_max_pages)
        raw = await _call_llm_vision(images)

    fields = _parse_json(raw)  # 失败 raise MetadataExtractError from exc
    meta = _build_metadata(doc_path, method, fields)
    _apply_acl_defaults(meta)         # 按 doc_category 派生 audience/visibility/owner_dept
    _check_needs_review(meta)         # 任一 conf < threshold → needs_review=True + reasons
    return meta


def _apply_acl_defaults(meta: ProductKBMetadata) -> None:
    """根据 doc_category 派生 ACL 字段（不靠 LLM）。"""
    cat = meta.doc_category.value
    if cat == DocCategory.USER_MANUAL.value:
        meta.audience = Audience.CUSTOMER_FACING
        meta.visibility = Visibility.PUBLIC
    elif cat == DocCategory.FAQ.value:
        meta.audience = Audience.CUSTOMER_FACING
        meta.visibility = Visibility.PUBLIC
    elif cat == DocCategory.TEST_CASE.value:
        meta.audience = Audience.INTERNAL_ONLY
        meta.visibility = Visibility.CONFIDENTIAL
        meta.owner_dept = "qa"
    elif cat == DocCategory.DEPLOYMENT.value:
        meta.audience = Audience.INTERNAL_ONLY
        meta.visibility = Visibility.INTERNAL
        meta.owner_dept = "impl"
    # ... 等
```

约束：
- LLM 调用走 `app.services.llm.get_llm()`，VLM 多模态用 `get_llm()` 的同一接口（百炼 OpenAI 兼容支持 image_url）
- prompt 渲染走 jinja2 `Environment`，模板从 `settings.prompts_dir` 读
- 文本解析：`pypdf` 提 PDF 文本；`.txt` / `.md` 直接读
- 视觉路径：`pdf2image` 转 PNG（DPI 走 `settings.vision_dpi`），单份限 `settings.vision_max_pages` 页（默认 20）

### 4.4 `backend/app/core/config.py`（追加）

```python
extract_confidence_threshold: int = 70
prompts_dir: str = "prompts"
vision_dpi: int = 150
vision_max_pages: int = 20
```

### 4.5 `backend/app/core/exceptions.py`（追加）

```python
class MetadataExtractError(AppException):
    error_code = "METADATA_EXTRACT_ERROR"
    status_code = 422
```

### 4.6 `backend/tests/services/test_product_kb_extract.py`（新建 ≥ 9 项）

全部 mock `get_llm`：

- `test_text_path_extracts_all_fields`
- `test_vision_path_for_pptx`
- `test_acl_defaults_for_user_manual_audience_customer_facing`
- `test_acl_defaults_for_test_case_visibility_confidential`
- `test_low_confidence_field_flags_needs_review`
- `test_invalid_json_raises_extract_error`
- `test_prompt_renders_with_enums`
- `test_route_text_vs_vision_by_extension`
- `test_sensitivity_is_int_in_metadata`（落地 Task 0 契约）

### 4.7 `backend/pyproject.toml`（追加依赖）

```toml
"jinja2>=3.1",
"pypdf>=4",
"pdf2image>=1.17",
"pillow>=10",
```

注：`pdf2image` 需要系统 poppler；docker-compose 加 backend 容器时装 poppler-utils。

---

## §5 验收标准

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'

# Task 0
& uv run alembic upgrade head      # 应用 0003
& uv run alembic downgrade -1 ; & uv run alembic upgrade head    # 双向验证
& uv run pytest tests/db/test_document_meta_acl_contract.py -v   # ≥ 5 passed

# 主体
& uv run pytest tests/services/test_product_kb_extract.py -v     # ≥ 9 passed
& uv run pytest -m "not integration" --cov=app                   # 124 → ≥ 138 passed; coverage ≥ 80%
& uv run ruff check . ; & uv run ruff format --check . ; & uv run mypy app

# 铁律 grep
grep -rE "import dashscope|from openai" backend/app/services/product_kb_extract.py
grep -rE "qwen|gte-rerank|https://dashscope" backend/app/services/product_kb_extract.py
# 全部无命中
```

人工抽样（合并前可选）：拿 5 份代表性文档（如「Web控制台使用说明.pdf」/「Mac客户端安装说明.pdf」/「IP-Guard产品测试用例（全模块）.pdf」）真实跑一次，人工核对抽取准确率，记录到 Handoff §4。

---

## §6 风险 & 已知问题

| 风险 | 缓解 |
|------|------|
| product_module 跨多个模块（如「服务器迁移」涉及客户端 + 服务器）| value 允许 "client+server" 形态；prompt 明确这种写法 |
| 视觉 PDF 转 PNG 慢（10MB PDF 30+ 页耗时长）| `vision_max_pages=20` 默认；超出页数取首尾 |
| Omni JSON 输出夹带 markdown 包裹 | 解析前 strip ```json fence；失败 raise，不静默 |
| `sensitivity` 抽取偏低（5 用得少）| 业务方人工审核兜底（你一个人审 199 份） |
| 同名带后缀文件（如 `(1)` / `20250630`）| 本任务只抽不入库；去重在 #26 / #27 处理 |
| poppler 跨平台 | Windows dev 装 conda-forge poppler；CI 镜像装 poppler-utils；docker 同 |

### 新增依赖

- `jinja2`（MIT）/ `pypdf`（BSD）/ `pdf2image`（MIT）/ `pillow`（HPND，已在白名单）
- 全部 MIT/BSD/ISC/HPND 白名单内

---

## §7 禁止事项

- ❌ `import dashscope` / 直连 OpenAI（铁律 #1，走 `get_llm`）
- ❌ Prompt 写在 Python 字符串里超过 3 行（铁律 #5，进 prompts/）
- ❌ 硬编码 confidence 阈值 / DPI / 模型名（铁律 #2 #6，走 settings）
- ❌ JSON 解析失败 `except: pass`（必须 raise MetadataExtractError from exc）
- ❌ 在本任务直接写入 PG / Qdrant（入库是 #28，本任务只抽取）
- ❌ **抽取客户名**（本批 199 份没有客户；当前 lean MVP customer 表留空，无 customer_match 调用）
- ❌ 跳过 Task 0（DocumentMetaSchema 契约不修就跑主体，#26-#30 会因类型不匹配翻车）
- ❌ Task 0 改 PR #13 锚定的 `app/models/document_meta.py` Pydantic（锚点不动，改 ORM 对齐 Pydantic）

---

## §8 参考

- `CLAUDE.md` v1.2 § 铁律 #1 #2 #5 #6
- `docs/handoffs/W2-D1-24-handoff.md` § 3 偏差 + § 6 重点 3（DocumentMetaSchema 差异来源）
- `backend/app/models/document_meta.py`（PR #13 锚定，不动）
- `backend/app/db/models/document_meta.py`（#24 新建，Task 0 修）
- `docs/tasks/W2-D2-26-batch-metadata-extract.md`（下游消费）

---

_v2.0 | 2026-06-12 | lean MVP 重写 + Task 0 契约修复_


