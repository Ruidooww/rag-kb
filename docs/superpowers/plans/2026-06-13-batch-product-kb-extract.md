# Batch Product KB Extract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a resumable, concurrency-limited batch CLI that calls only `extract_product_kb_metadata`, writes the shared #26/#27/#28 xlsx contract, and separates expected review rows from sanitized unexpected-failure JSONL records.

**Architecture:** `_xlsx_schema.py` owns the stable 24-column schema. `batch_extract_product_kb.py` recursively scans supported files, skips xlsx-completed paths, runs the public #25 entrypoint behind `settings.ingest_concurrency`, converts results/errors to rows, then atomically rewrites the workbook. Expected `MetadataExtractError` becomes a review row; unexpected exceptions become exactly three-key JSONL records.

**Tech Stack:** Python 3.14, asyncio, pandas/openpyxl, tqdm, pytest/pytest-asyncio, mypy strict, ruff.

---

## Scope And Dependency Map

```text
app.services.product_kb_extract.extract_product_kb_metadata
app.models.product_kb_metadata.ProductKBMetadata
app.core.exceptions.MetadataExtractError
app.core.config.settings.ingest_concurrency
                    |
                    v
scripts/batch_extract_product_kb.py
          |                    |
          v                    v
scripts/_xlsx_schema.py   failed_docs.jsonl
          |
          v
metadata.xlsx -> #27 review -> #28 ingest
```

- Main agent owns every file; no sub-agent dispatch because schema, writer, resume semantics, error semantics, and tests share one contract.
- Do not edit #25 public entrypoint or private helpers.
- Preserve user-authored `docs/tasks/W2-D2-26-batch-metadata-extract.md` and `docs/dispatch/W2-D2-26-dispatch.md`.
- Full 199-document run is blocked until the required 5-document trial is complete. The user explicitly waived the ¥100 stop threshold; record available cost evidence without using it as a blocker.

## Task 1: Lock The Shared Xlsx Contract

**Files:**
- Create: `backend/tests/scripts/test_xlsx_schema.py`
- Create: `backend/scripts/_xlsx_schema.py`

- [ ] Write failing snapshot, extracted-field, and ACL-anchor tests for the exact 24-column contract.
- [ ] Run `uv run pytest tests/scripts/test_xlsx_schema.py -v` and verify collection fails because `_xlsx_schema` does not exist.
- [ ] Add `METADATA_COLUMNS` as the only source of column keys and Chinese headers.
- [ ] Re-run the schema tests and verify at least 3 pass.

## Task 2: Lock Batch Behavior With Tests

**Files:**
- Create: `backend/tests/scripts/test_batch_extract_product_kb.py`
- Create: `backend/scripts/batch_extract_product_kb.py`

- [ ] Write failing tests for recursive supported-extension scanning and stable ordering.
- [ ] Write failing tests for `ProductKBMetadata` row conversion and exact schema order.
- [ ] Write failing tests for `MetadataExtractError` review rows with empty values, zero confidence, and fallback reason.
- [ ] Write failing test for unexpected exception JSONL with keys exactly `doc_path`, `ext`, `error_type`, and no exception message.
- [ ] Write failing tests for semaphore concurrency, resume skip, workbook append, and progress output without file/path disclosure.
- [ ] Run both target modules and verify failures are caused by missing batch implementation.
- [ ] Implement the minimal batch module:
  - `_SUPPORTED_INPUT_EXTENSIONS` filters `.pdf/.txt/.md/.pptx/.xlsx/.doc/.jpg`.
  - `scan_input_files()` recursively scans and sorts paths.
  - `_row_from_metadata()` and `_row_from_extract_error()` emit only schema keys.
  - `_append_failed_jsonl()` emits only the three locked keys.
  - `_load_done_paths()` reads existing xlsx paths.
  - `_write_rows()` concatenates existing/new rows in schema order and writes `metadata.xlsx.tmp` through a binary file handle before `os.replace`.
  - `_extract_one()` reads bytes with `asyncio.to_thread`, calls only `extract_product_kb_metadata`, and implements the failure split.
  - `batch_extract()` uses `asyncio.Semaphore(settings.ingest_concurrency)` and tqdm over `asyncio.as_completed`.
  - `main()` accepts input/output from `sys.argv`; no hardcoded paths or retries.
- [ ] Re-run both target modules and refactor only while green.

## Task 3: Dependency And Output Hygiene

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/uv.lock`
- Modify: `.gitignore`

- [ ] Add only missing `tqdm>=4.66`; retain existing pandas/openpyxl dependencies.
- [ ] Run `uv lock` and `uv sync`.
- [ ] Ignore `backend/data/metadata.xlsx`, `backend/data/metadata.xlsx.tmp`, `backend/data/metadata_sample.xlsx`, and `backend/data/failed_docs.jsonl`.
- [ ] Verify real output files remain untracked.

## Task 4: Automated Acceptance

- [ ] Run target tests:
  - `uv run pytest tests/scripts/test_batch_extract_product_kb.py -v`
  - `uv run pytest tests/scripts/test_xlsx_schema.py -v`
- [ ] Run full non-integration coverage: `uv run pytest -m "not integration" --cov=app`.
- [ ] Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app`, and `uv run mypy scripts`.
- [ ] Run locked greps for forbidden model imports, environment access, #25 private helpers, and customer/DB/Qdrant scope.
- [ ] Run `uv pip check` and dependency-license checks.

## Task 5: Mandatory Five-Document Trial

**Inputs/outputs:**
- Read: `backend/data/sample_5/`
- Generate, do not commit: `backend/data/metadata_sample.xlsx`
- Generate if needed, do not commit: `backend/data/failed_docs.jsonl`

- [ ] Confirm exactly five supported documents are present and record extension distribution without exposing names in logs.
- [ ] Run `uv run python scripts/batch_extract_product_kb.py ./data/sample_5 ./data/metadata_sample.xlsx`.
- [ ] Inspect the workbook and record for each document: `extract_method`, six extracted values, and six confidence scores.
- [ ] Record route distribution, success/review/failure totals, elapsed time, and available cost evidence.
- [ ] Estimate total 199-document cost when evidence is available; do not use cost as a stop condition.
- [ ] Do not run all 199 documents without a separate user release after the trial results.

## Task 6: Commit, PR, Self-Review, And Handoff

- [ ] Create `docs/handoffs/W2-D2-26-handoff.md` with actual automated and trial outputs, deviations, risks, Part A-E, and the per-document manual review table.
- [ ] Commit only #26-related implementation, user-authored task/dispatch docs, plan, and handoff.
- [ ] Push and create PR for #26.
- [ ] Run final CI/self-review; do not merge automatically on any Part D hard trigger.
