# Product KB Metadata Extract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the `document_meta` ACL database contract with the locked PR #13 Pydantic schema, then extract lean-MVP IP-Guard product KB metadata through the unified LLM/VLM abstraction.

**Architecture:** Task 0 first changes only the `document_meta` ORM/repository contract and introduces Alembic `0003`; its migration and contract tests are a hard gate. The extraction service routes PDFs by whether `pypdf` returns non-blank text, renders a file-based Jinja2 prompt, calls `get_llm()`, parses structured JSON, and derives ACL defaults locally without writing PG/Qdrant. Non-PDF/non-text extensions are classified as vision but raise a sanitized review-required error because Office/image converters are explicitly deferred to a Phase 2 spec.

**Tech Stack:** Python 3.14, SQLAlchemy 2 async, Alembic, Pydantic v2, LlamaIndex `OpenAILike`, Jinja2, pypdf, pdf2image, Pillow, pytest.

---

## Scope And Collaboration Decision

- Only #25 v2 is implemented. No #25b, #26-#32 work.
- No customer extraction, `customer_match`, PG/Qdrant ingest, batch concurrency, CRM, or IdP integration.
- No sub-agent dispatch: Task 0 migration/ORM/repo and extraction model/service/tests share contracts and are highly coupled. The main agent owns all files and final integration verification.
- `backend/app/models/document_meta.py` is the locked PR #13 anchor and must remain byte-for-byte unchanged relative to `main`.
- User explicitly authorized aligning #17 downstream input schema `backend/app/models/customer.py::DocumentMetaCreate`; record this spec file-list gap in Handoff §3.
- `backend/app/db/repos/document_meta.py` remains unchanged because `data.model_dump()` automatically follows `DocumentMetaCreate`.
- User explicitly selected Option B: `.pptx/.xlsx/.doc/.jpg` and other non-PDF/non-text extensions are VISION-classified but unsupported in this lean MVP. They raise sanitized `MetadataExtractError` with extension-only review reasons; record this spec ambiguity resolution in Handoff §3.
- No LibreOffice converter, Office-specific Python converter, Docker package, or related dependency is added.
- Existing unrelated untracked `docs/dispatch/` is not read, modified, staged, or committed.

## File Dependency Graph

```text
backend/app/models/document_meta.py (locked anchor, no changes)
  -> backend/app/db/models/document_meta.py
      -> backend/migrations/versions/0003_document_meta_acl_align.py
      -> backend/app/models/customer.py::DocumentMetaCreate
      -> backend/tests/db/test_document_meta_acl_contract.py
      -> backend/tests/db/test_customer_repo.py

backend/app/core/config.py + config.yaml
backend/prompts/extract_product_kb.txt
  -> backend/app/models/product_kb_metadata.py
      -> backend/app/services/product_kb_extract.py
          -> backend/tests/services/test_product_kb_extract.py

backend/app/core/exceptions.py
  -> backend/app/services/product_kb_extract.py

backend/pyproject.toml + backend/uv.lock
  -> backend/app/services/product_kb_extract.py
```

## Task 0 Five-Field Contract Echo

1. `audience`: current ORM `String(32)`, default `"internal"`; aligned ORM `String(32)`, default `"internal_only"`, check values `internal_only/customer_facing/public`.
2. `owner_dept`: current ORM `nullable=False`; aligned ORM `Mapped[str | None]`, `nullable=True`.
3. `visibility`: current ORM `String(32)`, default `"internal"`; aligned ORM keeps that default and adds check values `public/internal/confidential`.
4. `sensitivity`: current ORM `String(32)`, default `"normal"`; aligned ORM `Integer`, default `3`, check range `1-5`.
5. `shared_depts`: stays `ARRAY(String(32))`, `nullable=False`, default empty list.

## Migration `0003` To ORM Mapping

| Migration `0003` operation | ORM contract |
|---|---|
| Update `audience='internal'` to `internal_only`; add `ck_document_meta_audience` | `audience` default `internal_only`; only `Audience` values accepted |
| Drop `owner_dept` NOT NULL | `owner_dept: Mapped[str | None]` |
| Add `ck_document_meta_visibility` | only `Visibility` values accepted |
| Convert `sensitivity` to integer using the spec's `CASE ... ELSE 3`; add `ck_document_meta_sensitivity` | `sensitivity: Mapped[int]`, default `3`, valid `1-5` |
| Leave `shared_depts` unchanged | `ARRAY(String(32))`, default empty list |

Downgrade removes the three checks, restores `owner_dept` NOT NULL after replacing nulls with an empty string, converts sensitivity back to `String(32)` with `"normal"`, and converts `internal_only` back to `internal`. This is intentionally data-lossy for post-`0003` ACL values and must be recorded in Handoff §7.

## `0002` Conflict Verification

1. Assert `0003.down_revision == "0002"`.
2. Run `alembic upgrade head`, `downgrade -1`, `upgrade head`, and confirm `0003 (head)`.
3. Run `alembic check` to ensure the final ORM metadata does not request another migration.
4. Assert `git diff main -- backend/app/models/document_meta.py` is empty.

---

### Task 1: Task 0 RED - Lock The ACL Contract In Tests

**Files:**
- Create: `backend/tests/db/test_document_meta_acl_contract.py`

- [ ] Add module-scoped PostgreSQL table setup and cleanup matching existing #24 DB test patterns.
- [ ] Add at least these contract tests:
  - `test_audience_default_is_internal_only`
  - `test_owner_dept_can_be_null`
  - `test_visibility_check_constraint_rejects_unknown`
  - `test_sensitivity_is_int_range_1_to_5`
  - `test_sensitivity_check_constraint_rejects_0_and_6`
  - `test_shared_depts_stays_array_of_string_32`
  - `test_orm_matches_pydantic_schema`
- [ ] Run:

```powershell
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run pytest tests/db/test_document_meta_acl_contract.py -v
```

Expected: failures show the current #24 ORM still has `"internal"`, non-null `owner_dept`, and string sensitivity.

### Task 2: Task 0 GREEN - Align ORM, Repository Contract, And Alembic `0003`

**Files:**
- Modify: `backend/app/db/models/document_meta.py`
- Modify: `backend/app/models/customer.py`
- Modify: `backend/tests/db/test_customer_repo.py`
- Create: `backend/migrations/versions/0003_document_meta_acl_align.py`

- [ ] Add named SQLAlchemy check constraints for audience, visibility, and sensitivity.
- [ ] Change owner department nullability and sensitivity integer typing/default.
- [ ] Keep `shared_depts` as PostgreSQL `ARRAY(String(32))`.
- [ ] Align `DocumentMetaCreate` to the locked five-field contract; keep repository code unchanged.
- [ ] Change the existing #24 test assertion from `owner_dept.nullable is False` to `is True`.
- [ ] Implement reversible `0003` directly after `0002`.
- [ ] Run the Task 0 target tests until green.
- [ ] Run the Task 0 hard gate:

```powershell
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run alembic upgrade head
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run alembic downgrade -1
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run alembic upgrade head
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run alembic current
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run alembic check
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run pytest tests/db/test_document_meta_acl_contract.py -v
```

Expected: `0003 (head)`, no new upgrade operations, and at least 5 passed. If any command fails, stop before Task 3.

### Task 3: Extraction RED - Lock Models, Routing, ACL Defaults, And Error Safety

**Files:**
- Create: `backend/tests/services/test_product_kb_extract.py`

- [ ] Add tests for all required behavior, including:
  - `test_text_path_extracts_all_fields`
  - `test_vision_path_for_pptx`
  - `test_unsupported_extension_raises_extract_error`
  - `test_pdf_with_extractable_text_routes_to_text`
  - `test_pdf_with_blank_text_routes_to_vision`
  - `test_acl_defaults_for_user_manual_audience_customer_facing`
  - `test_acl_defaults_for_test_case_visibility_confidential`
  - `test_acl_defaults_for_release_note`
  - `test_acl_defaults_for_troubleshoot`
  - `test_acl_defaults_for_other`
  - `test_low_confidence_field_flags_needs_review`
  - `test_invalid_json_raises_extract_error`
  - `test_extract_error_does_not_leak_doc_path`
  - `test_prompt_renders_with_enums`
  - `test_sensitivity_is_int_in_metadata`
- [ ] Mock `get_llm`, `pypdf`, and image conversion at service boundaries; do not call real LLM/VLM.
- [ ] Run the target file and verify RED due to missing model/service.

### Task 4: Extraction GREEN - Add Configuration, Prompt, Model, Service, And Dependencies

**Files:**
- Create: `backend/prompts/extract_product_kb.txt`
- Create: `backend/app/models/product_kb_metadata.py`
- Create: `backend/app/services/product_kb_extract.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/core/exceptions.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Modify: `config.yaml`

- [ ] Add settings/config values:
  - `extract_confidence_threshold: int = 70`
  - `prompts_dir: str = "prompts"`
  - `vision_dpi: int = 150`
  - `vision_max_pages: int = 20`
- [ ] Add `MetadataExtractError` with status `422`.
- [ ] Add the spec-provided Jinja2 prompt file; do not put a multi-line prompt in Python.
- [ ] Add the spec enums and `ProductKBMetadata`.
- [ ] Implement routing:
  - `.pptx/.xlsx/.doc/.jpg` and any other non-PDF/non-text extension -> VISION classification, then sanitized unsupported-extension error
  - `.txt/.md` -> TEXT
  - `.pdf` with non-blank pypdf output -> TEXT
  - `.pdf` with blank pypdf output -> VISION
- [ ] Use `anyio.to_thread.run_sync` for pypdf/pdf2image/Pillow blocking work.
- [ ] Call text and vision paths only through `get_llm()`.
- [ ] Parse optional JSON fences; on any extraction failure log detailed context with `logger.warning` and raise `MetadataExtractError("Failed to extract metadata") from exc`.
- [ ] Derive ACL without LLM:
  - `user_manual`, `faq` -> `customer_facing/public/None`
  - `test_case` -> `internal_only/confidential/qa`
  - `deployment` -> `internal_only/internal/impl`
  - `troubleshoot` -> `internal_only/internal/aftersales`
  - `release_note`, `other` -> `internal_only/internal/None`
- [ ] Mark review when any field confidence is below settings threshold.
- [ ] Add `jinja2`, `pypdf`, `pdf2image`, and `pillow`; update lockfile.
- [ ] Run extraction target tests until at least 9 pass.

### Task 5: Integrated Verification And Documentation

**Files:**
- Create: `docs/handoffs/W2-D2-25-handoff.md`

- [ ] Re-run Task 0 migration and contract hard gate.
- [ ] Run extraction target tests.
- [ ] Run:

```powershell
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run pytest -m "not integration" --cov=app --cov-report=term-missing
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run ruff check .
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run ruff format --check .
& 'C:\Users\Ruidoww\.local\bin\uv.exe' run mypy app
```

- [ ] Run required iron-law greps and assert the Pydantic anchor diff is empty.
- [ ] Complete SELF_REVIEW Part A-E, explicitly marking I1 no-sub-agent and J1/K1 N/A because there is no API.
- [ ] Write Handoff §7 with:
  - empty-PG success and future populated-table migration cautions
  - full doc_category-to-ACL mapping for #26/#28
  - IP-Guard module enum expansion/prompt update procedure
  - Windows Poppler via conda-forge; CI/Docker via `poppler-utils`
- [ ] Commit/push/create PR only after all local acceptance commands pass. Do not merge on any Part D hard trigger.
