from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.core.exceptions import MetadataExtractError
from app.models.document_meta import Audience, Visibility
from app.models.product_kb_metadata import ExtractMethod, FieldConfidence, ProductKBMetadata
from scripts import batch_extract_product_kb as batch
from scripts._xlsx_schema import METADATA_COLUMNS


def _metadata(doc_path: str, *, needs_review: bool = False) -> ProductKBMetadata:
    return ProductKBMetadata(
        doc_path=doc_path,
        extract_method=ExtractMethod.TEXT,
        product_module=FieldConfidence(value="client", confidence=91),
        product_version=FieldConfidence(value="4.86", confidence=82),
        platform=FieldConfidence(value="windows", confidence=93),
        target_audience=FieldConfidence(value="admin", confidence=84),
        doc_category=FieldConfidence(value="user_manual", confidence=95),
        sensitivity=FieldConfidence(value=2, confidence=86),
        audience=Audience.CUSTOMER_FACING,
        visibility=Visibility.PUBLIC,
        owner_dept=None,
        shared_depts=[],
        needs_review=needs_review,
        review_reasons=["Low confidence: product_version"] if needs_review else [],
    )


def test_scans_supported_extensions_recursively(tmp_path: Path) -> None:
    nested = tmp_path / "中文目录"
    nested.mkdir()
    for name in ("a.pdf", "b.txt", "c.md", "d.pptx", "e.xlsx", "f.doc", "g.jpg"):
        (nested / name).write_bytes(b"x")
    (nested / "ignored.png").write_bytes(b"x")

    result = batch.scan_input_files(tmp_path)

    assert [path.suffix for path in result] == [
        ".pdf",
        ".txt",
        ".md",
        ".pptx",
        ".xlsx",
        ".doc",
        ".jpg",
    ]


def test_row_from_metadata_has_schema_order() -> None:
    result = batch._row_from_metadata(_metadata("docs/sample.pdf"))

    assert list(result) == [key for key, _ in METADATA_COLUMNS]
    assert result["product_module"] == "client"
    assert result["product_module_conf"] == 91
    assert result["sensitivity"] == 2
    assert result["needs_review"] == "否"
    assert result["review_status"] == "pending"


def test_metadata_extract_error_writes_needs_review_row() -> None:
    exc = MetadataExtractError(review_reasons=["Unsupported extension .xlsx in lean MVP"])

    result = batch._row_from_extract_error("docs/secret.xlsx", exc)

    assert list(result) == [key for key, _ in METADATA_COLUMNS]
    assert result["doc_path"] == "docs/secret.xlsx"
    assert result["extract_method"] is None
    assert result["product_module"] is None
    assert result["product_module_conf"] == 0
    assert result["sensitivity"] is None
    assert result["sensitivity_conf"] == 0
    assert result["needs_review"] == "是"
    assert result["review_reasons"] == "Unsupported extension .xlsx in lean MVP"
    assert result["review_status"] == "pending"


def test_metadata_extract_error_uses_fallback_review_reason() -> None:
    result = batch._row_from_extract_error("docs/secret.xlsx", MetadataExtractError())

    assert result["review_reasons"] == "MetadataExtractError"


async def test_unexpected_exception_appends_failed_jsonl_without_path_internals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "secret-name.pdf"
    source.write_bytes(b"pdf")
    output = tmp_path / "metadata.xlsx"

    async def fail_extract(doc_path: str, doc_bytes: bytes) -> ProductKBMetadata:
        raise RuntimeError(f"internal temp path C:/private/cache for {doc_path}")

    monkeypatch.setattr(batch, "extract_product_kb_metadata", fail_extract)

    summary = await batch.batch_extract(tmp_path, output, show_progress=False)
    failed_path = tmp_path / "failed_docs.jsonl"
    record = json.loads(failed_path.read_text(encoding="utf-8"))

    assert summary.failed == 1
    assert set(record) == {"doc_path", "ext", "error_type"}
    assert record == {
        "doc_path": str(source),
        "ext": ".pdf",
        "error_type": "RuntimeError",
    }
    assert "internal temp path" not in failed_path.read_text(encoding="utf-8")


async def test_concurrency_respects_semaphore_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = [tmp_path / f"{index}.pdf" for index in range(4)]
    for source in sources:
        source.write_bytes(b"pdf")
    in_flight = 0
    max_in_flight = 0
    release = asyncio.Event()

    async def controlled_extract(doc_path: str, doc_bytes: bytes) -> ProductKBMetadata:
        nonlocal in_flight, max_in_flight
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        if max_in_flight >= 2:
            release.set()
        await release.wait()
        await asyncio.sleep(0)
        in_flight -= 1
        return _metadata(doc_path)

    monkeypatch.setattr(batch.settings, "ingest_concurrency", 2)
    monkeypatch.setattr(batch, "extract_product_kb_metadata", controlled_extract)

    summary = await batch.batch_extract(tmp_path, tmp_path / "metadata.xlsx", show_progress=False)

    assert summary.written == 4
    assert max_in_flight == 2


async def test_resume_skips_already_extracted_doc_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first.write_bytes(b"pdf")
    second.write_bytes(b"pdf")
    output = tmp_path / "metadata.xlsx"
    pd.DataFrame([batch._row_from_metadata(_metadata(str(first)))]).to_excel(output, index=False)
    seen: list[str] = []

    async def record_extract(doc_path: str, doc_bytes: bytes) -> ProductKBMetadata:
        seen.append(doc_path)
        return _metadata(doc_path)

    monkeypatch.setattr(batch, "extract_product_kb_metadata", record_extract)

    summary = await batch.batch_extract(tmp_path, output, show_progress=False)

    assert seen == [str(second)]
    assert summary.skipped == 1
    assert summary.written == 1
    assert list(pd.read_excel(output)["doc_path"]) == [str(first), str(second)]


async def test_output_xlsx_has_all_columns_from_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"pdf")
    output = tmp_path / "metadata.xlsx"

    async def successful_extract(doc_path: str, doc_bytes: bytes) -> ProductKBMetadata:
        return _metadata(doc_path)

    monkeypatch.setattr(batch, "extract_product_kb_metadata", successful_extract)

    await batch.batch_extract(tmp_path, output, show_progress=False)

    assert list(pd.read_excel(output).columns) == [key for key, _ in METADATA_COLUMNS]
    assert not output.with_suffix(output.suffix + ".tmp").exists()


async def test_progress_bar_does_not_log_doc_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "do-not-leak-this-name.pdf"
    source.write_bytes(b"pdf")

    async def successful_extract(doc_path: str, doc_bytes: bytes) -> ProductKBMetadata:
        return _metadata(doc_path)

    monkeypatch.setattr(batch, "extract_product_kb_metadata", successful_extract)

    await batch.batch_extract(tmp_path, tmp_path / "metadata.xlsx", show_progress=True)
    captured = capsys.readouterr()

    assert source.name not in captured.out
    assert source.name not in captured.err
    assert ".pdf" in captured.err


def test_row_from_metadata_joins_list_fields() -> None:
    metadata = _metadata("docs/sample.pdf", needs_review=True)
    metadata.shared_depts = ["qa", "impl"]

    result: dict[str, Any] = batch._row_from_metadata(metadata)

    assert result["shared_depts"] == "qa | impl"
    assert result["review_reasons"] == "Low confidence: product_version"
    assert result["needs_review"] == "是"


def test_write_rows_retries_replace_once_when_workbook_is_locked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "metadata.xlsx"
    real_replace = batch.os.replace
    attempts = 0

    def flaky_replace(source: Path, destination: Path) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("workbook locked")
        real_replace(source, destination)

    monkeypatch.setattr(batch.os, "replace", flaky_replace)

    batch._write_rows(output, [batch._row_from_metadata(_metadata("docs/sample.pdf"))])

    assert attempts == 2
    assert output.exists()
