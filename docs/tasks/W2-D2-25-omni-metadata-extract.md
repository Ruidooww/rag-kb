# 任务 #25：Omni 元数据自动抽取脚本

> **版本**：v1.0
> **创建日期**：2026-06-05
> **预估工时**：1 工作日
> **前置任务**：#24 客户主数据（customer_alias 模糊匹配）+ #19 LLM 抽象层（get_llm / VLM 调用）
> **后续任务**：#26 跑 400 份批量抽取
> **优先级**：🔴 高（W2 关键周主线，阻塞 #26 #28 #30）

---

## §1 任务背景

400 份历史文档要入库，每份需要结构化元数据：客户、业务日期、产品、事件类型、文档类型、敏感程度。人工逐份填不现实，用 Omni（qwen3.5-omni-flash）自动抽取 + 业务方审核（#27）的双轨方案。

本任务建立**单份文档抽取能力 + Prompt 模板**，#26 在此基础上批量并发跑。

关键约束：
- 抽取的客户名走 #24 `customer_match.match()` 模糊匹配到内部 customer_id
- 视觉文档（PPT / 带图 PDF / 复杂 Excel）走截图 + VLM 路径
- 所有 LLM/VLM 调用走 `app.services.llm`（铁律 #1），不直连 dashscope

---

## §2 范围

- ✅ `prompts/extract_metadata.txt`（铁律 #5：Prompt 进文件，jinja2 注入）
- ✅ `backend/app/services/metadata_extract.py`（单份抽取核心）
- ✅ 客户名 → customer_id 模糊匹配集成（调 #24 `customer_match`）
- ✅ 视觉文档截图 + VLM 路径（PPT/PDF→PNG→Omni 描述）
- ✅ 抽取结果 Pydantic schema（带置信度字段）
- ✅ 单元测试（mock LLM 返回 + 真实 prompt 渲染）

- ❌ 不做批量并发（#26）
- ❌ 不做入库（#28）
- ❌ 不连真实云端跑全量（单测 mock，10 份样本人工验）

---

## §3 任务目标

1. `extract_metadata(doc_path)` 输入一份文档，返回 `ExtractedMetadata`（含 6 字段 + 每字段置信度）
2. 客户名抽取后自动走 `customer_match.match()`，命中 → 填 customer_id + matched_score；未命中 → customer_id=None + 标记 needs_review
3. 视觉文档（.pptx / .pdf 带图 / .xlsx）走 VLM 截图路径，纯文本走文本路径
4. Prompt 在 `prompts/extract_metadata.txt`，用 jinja2 注入 doc_type 枚举 + 客户别名候选
5. 低置信度（< 阈值 settings.extract_confidence_threshold）字段标 `needs_review=True`
6. 测试：mock LLM 下覆盖文本路径 / 视觉路径 / 客户命中 / 客户未命中 / 低置信度标记 ≥ 8 项

---

## §4 文件清单

### 4.1 `backend/prompts/extract_metadata.txt`（新建，jinja2）

```jinja2
你是文档元数据抽取专家。从以下文档内容中抽取结构化元数据。

## 已知客户别名候选（模糊匹配用，不强制）
{{ customer_hints }}

## 文档类型枚举（必须从中选一个）
{{ doc_type_enum }}

## 待抽取文档内容
{{ doc_content }}

## 输出要求
严格返回 JSON，每个字段附 confidence（0-100）：
{
  "customer_name": {"value": "...", "confidence": 0-100},
  "event_date": {"value": "YYYY-MM-DD 或 null", "confidence": 0-100},
  "product": {"value": "...", "confidence": 0-100},
  "event_type": {"value": "...", "confidence": 0-100},
  "doc_type": {"value": "从枚举选", "confidence": 0-100},
  "sensitivity": {"value": "normal/confidential/secret", "confidence": 0-100}
}
不要输出 JSON 以外的任何文字。关键数字/日期必须来自文档原文，禁止臆测。
```

### 4.2 `backend/app/models/metadata.py`（新建）

```python
from __future__ import annotations
from datetime import date
from enum import StrEnum
from pydantic import BaseModel, Field


class ExtractMethod(StrEnum):
    TEXT = "text"
    VISION = "vision"


class FieldConfidence(BaseModel):
    value: str | None = None
    confidence: int = Field(ge=0, le=100, default=0)


class ExtractedMetadata(BaseModel):
    doc_path: str
    extract_method: ExtractMethod
    customer_name: FieldConfidence
    customer_id: int | None = None           # 模糊匹配命中后填
    customer_match_score: int = 0
    event_date: FieldConfidence
    product: FieldConfidence
    event_type: FieldConfidence
    doc_type: FieldConfidence
    sensitivity: FieldConfidence
    needs_review: bool = False               # 任一字段低置信度 / 客户未命中
    review_reasons: list[str] = Field(default_factory=list)
```

### 4.3 `backend/app/services/metadata_extract.py`（新建核心）

要点：
- `async def extract_metadata(doc_path: str) -> ExtractedMetadata`
- 文档类型判定：`.pptx`/`.pdf`(带图)/`.xlsx` → VISION；`.docx`/`.txt`/`.md`/纯文本 PDF → TEXT
- TEXT 路径：解析正文 → 渲染 prompt → `get_llm().acomplete()` → 解析 JSON
- VISION 路径：每页转 PNG → `get_llm()` VLM 多模态调用（图片 base64）→ 解析 JSON
- 客户匹配：抽到 customer_name 后 `async with SessionLocal()` 调 `customer_match.match()`
- 低置信度：任一字段 confidence < `settings.extract_confidence_threshold`(默认 70) → needs_review=True + review_reasons 记录
- JSON 解析失败 → `raise MetadataExtractError(...) from exc`（不静默）
- prompt 渲染用 jinja2 `Environment`，模板从 `backend/prompts/` 读

### 4.4 `backend/app/core/config.py`（追加）

```python
extract_confidence_threshold: int = 70
prompts_dir: str = "prompts"
vision_dpi: int = 150            # PPT/PDF 转 PNG 分辨率
vision_max_pages: int = 20       # 单份视觉文档最大处理页数
```

### 4.5 `backend/app/core/exceptions.py`（追加）

```python
class MetadataExtractError(AppException):
    error_code = "METADATA_EXTRACT_ERROR"
    status_code = 422
```

### 4.6 `backend/tests/services/test_metadata_extract.py`（新建）

测试场景（≥ 8 项，全部 mock `get_llm`）：
- `test_text_path_extracts_all_fields`
- `test_vision_path_for_pptx`
- `test_customer_name_matched_fills_customer_id`
- `test_customer_name_unmatched_flags_needs_review`
- `test_low_confidence_field_flags_needs_review`
- `test_invalid_json_raises_extract_error`
- `test_prompt_renders_with_customer_hints_and_enum`
- `test_doc_type_routing_text_vs_vision`

---

## §5 验收标准

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'
& uv run pytest tests/services/test_metadata_extract.py -v   # ≥ 8 passed
& uv run pytest -m "not integration" --cov=app               # 回归不降
& uv run ruff check . ; & uv run ruff format --check . ; & uv run mypy app

# 铁律 grep
grep -rE "import dashscope|from openai" backend/app/services/metadata_extract.py   # 无命中
grep -rE "qwen|gte-rerank|https://dashscope" backend/app/services/metadata_extract.py  # 无命中（走 settings）
```

人工抽样（#26 前置）：10 份代表性文档（含 ≥ 2 份视觉文档）真实跑一次，人工核对抽取准确率，记录到 Handoff §4。

---

## §6 风险 & 已知问题

| 风险 | 缓解 |
|------|------|
| Omni JSON 输出不稳定（夹带 markdown ```json``` 包裹）| 解析前 strip code fence；失败 raise 不静默 |
| 视觉文档转 PNG 依赖（pdf2image/pillow + poppler）| §4.4 依赖审计；poppler 走 docker 镜像装 |
| 客户别名候选过多撑爆 prompt | customer_hints 只传 top-N（按 region/industry 预筛）或全量名称列表（400 个可接受）|
| VLM 调用成本（每页一次）| `vision_max_pages` 限制；#26 批量时监控费用 |

### 新增依赖

- `jinja2>=3.1`（Prompt 模板，铁律 #5）
- `pdf2image>=1.17` + `pillow>=10`（视觉路径，PDF/PPT→PNG）
- `python-pptx>=1.0`（PPT 解析，可选——也可统一转 PDF 再截图）

---

## §7 禁止事项

- ❌ `import dashscope` / 直连 OpenAI（铁律 #1，走 `get_llm`）
- ❌ Prompt 写在 Python 字符串里超过 3 行（铁律 #5，进 prompts/）
- ❌ 硬编码 confidence 阈值 / DPI / 模型名（铁律 #2 #6，走 settings）
- ❌ JSON 解析失败 `except: pass`（必须 raise MetadataExtractError from exc）
- ❌ 在本任务直接写入 PG / Qdrant（入库是 #28，本任务只抽取）
- ❌ customer 匹配用精确字符串比较（必须走 #24 `customer_match.match()`）

---

## §8 参考

- `CLAUDE.md` v1.2 § 铁律 #1 #2 #5 #6
- `docs/tasks/W2-D1-24-customer-master-data.md` § customer_match
- `docs/tasks/W1-D3-19-llamaindex-abstract.md` § get_llm / VLM 调用
- 百炼多模态文档：https://help.aliyun.com/zh/model-studio/

---

_v1.0 | 2026-06-05_
