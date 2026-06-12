# Customer Master Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement task #24 only: four PostgreSQL customer-master tables, async repositories, fuzzy matching, Excel initialization, sample data, and acceptance coverage.

**Architecture:** `customer` is the local master record and parent of `customer_alias`, `customer_product`, and optional `document_meta.customer_id`. ORM models define runtime behavior; migration `0002` mirrors those models exactly and revises `0001`. Pydantic schemas remain independent from `app.models.crm`, while CLI scripts call repositories/services through `SessionLocal`.

**Tech Stack:** Python 3.14, SQLAlchemy 2 async, Alembic, PostgreSQL 16, Pydantic v2, rapidfuzz, pandas/openpyxl, pytest.

---

## File Dependency Graph

```text
config.yaml -> app/core/config.py -> services/customer_match.py
                            \-----> scripts/init_customer_master.py
app/db/base.py -> app/db/models/customer.py ---------> app/db/repos/customer.py
              \-> app/db/models/document_meta.py ----> app/db/repos/document_meta.py
ORM models ----> migrations/versions/0002_customer_master_data.py
app/models/customer.py -> repos/document_meta.py + services/customer_match.py
repos + services -> scripts/*.py -> backend/data/customer_master_init_sample.xlsx
all implementation files -> tests/db + tests/services + tests/scripts
```

## Migration 0002 ↔ ORM Mapping

| Migration table | ORM class | Locked constraints |
|---|---|---|
| `customer` | `Customer` | nullable `external_id`, unique external ID, name/owner indexes |
| `customer_alias` | `CustomerAlias` | unique + indexed alias, cascade FK |
| `customer_product` | `CustomerProduct` | unique `(customer_id, product_code)`, cascade FK |
| `document_meta` | `DocumentMeta` | optional customer FK; exactly five ACL fields; `shared_depts` is PostgreSQL `ARRAY(String(32))` |

## Sub-Agent Decision

No sub-agent dispatch. ORM, migration, repositories, schemas, configuration, scripts, and tests share tightly coupled names and constraints. The main agent owns all files so migration numbering, ACL field definitions, and schema signatures cannot drift. This also avoids ANTIPATTERN I1.

## Execution Tasks

### Task 1: RED tests for schemas, ORM, repositories, and migration shape

- [ ] Add `tests/db/test_customer_repo.py` with customer, alias, product, document-meta, ACL-lock, and migration-metadata assertions.
- [ ] Run the file and verify collection/import failures are caused by missing #24 modules.
- [ ] Implement §4.1-§4.6 and package exports, then rerun until green.

### Task 2: RED tests for fuzzy matching and settings

- [ ] Add `tests/services/test_customer_match.py` covering exact, alias exact, fuzzy threshold, empty query, ordering, configured defaults, and 400-customer performance.
- [ ] Verify failure because `app.services.customer_match` and settings fields are absent.
- [ ] Add `customer_master_excel_path`, `customer_match_fuzzy_threshold`, and `customer_match_limit` to `config.yaml`/`Settings`; implement §4.7; rerun until green.

### Task 3: RED tests for Excel initialization and CLIs

- [ ] Add `tests/scripts/test_init_customer_master.py` for creation, idempotency, unknown external ID, and non-sensitive errors.
- [ ] Verify failure because scripts/sample workbook are absent.
- [ ] Implement §4.8-§4.9 and generate §4.14 fictional workbook; ensure CLI arguments override settings defaults.

### Task 4: Dependencies and documentation

- [ ] Add rapidfuzz/pandas/openpyxl to `backend/pyproject.toml`, sync lock/environment, and verify licenses.
- [ ] Add the ≤15-line customer-master quick reference required by §4.15.
- [ ] Confirm no #25-#30 files or behavior changed.

### Task 5: Migration and full acceptance

- [ ] Before testing `0002`, run `alembic downgrade base && alembic upgrade 0001 && alembic current` to prove `0001` remains independently valid.
- [ ] Run `upgrade head`, `downgrade -1`, `upgrade head`, and `current`; inspect all four tables and indexes.
- [ ] Run ≥21 target tests, non-integration regression, coverage, ruff, format, mypy, CLI E2E, dependency checks, and required greps.
- [ ] Run complete SELF_REVIEW Part A-E and record actual evidence in `docs/handoffs/W2-D1-24-handoff.md`.

## Scope and Ambiguity Guard

- Implement only task #24 and only the files needed by §4.1-§4.15 plus this required plan/handoff/package exports.
- `customer_alias.confidence` records source trust and does not alter fuzzy score in #24.
- `DocumentMeta.shared_depts` uses callable `default=list`; no JSON and no extra ACL fields.
- Future `weighted_score = fuzzy_score * (confidence / 100)` is a Phase 2 #41 product decision and must be recorded in Handoff §7, not implemented here.
