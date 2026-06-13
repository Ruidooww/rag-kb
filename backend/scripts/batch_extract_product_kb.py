"""Batch extract product KB metadata for lean MVP IP-Guard documents."""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from tqdm import tqdm

BACKEND_ROOT = Path(__file__).parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.exceptions import MetadataExtractError  # noqa: E402
from app.models.product_kb_metadata import ProductKBMetadata  # noqa: E402
from app.services.product_kb_extract import extract_product_kb_metadata  # noqa: E402
from scripts._xlsx_schema import (  # noqa: E402
    EXTRACTED_FIELD_KEYS,
    METADATA_COLUMN_KEYS,
)

_SUPPORTED_INPUT_EXTENSIONS = {".pdf", ".txt", ".md", ".pptx", ".xlsx", ".doc", ".jpg"}
_FAILED_FILENAME = "failed_docs.jsonl"

MetadataRow = dict[str, Any]


@dataclass(frozen=True)
class BatchSummary:
    scanned: int
    written: int
    needs_review: int
    failed: int
    skipped: int


@dataclass(frozen=True)
class _Outcome:
    ext: str
    row: MetadataRow | None
    failed: bool = False


def scan_input_files(input_dir: Path) -> list[Path]:
    """Return supported input files recursively in stable path order."""

    return sorted(
        (
            path
            for path in input_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in _SUPPORTED_INPUT_EXTENSIONS
        ),
        key=lambda path: str(path).casefold(),
    )


def _exclude_output_files(paths: list[Path], output_xlsx: Path) -> list[Path]:
    excluded = {
        output_xlsx.resolve(),
        output_xlsx.with_suffix(output_xlsx.suffix + ".tmp").resolve(),
    }
    return [path for path in paths if path.resolve() not in excluded]


def _empty_row() -> MetadataRow:
    row: MetadataRow = dict.fromkeys(METADATA_COLUMN_KEYS)
    for field_name in EXTRACTED_FIELD_KEYS:
        row[f"{field_name}_conf"] = 0
    row["needs_review"] = "否"
    row["review_reasons"] = ""
    row["review_status"] = "pending"
    return row


def _row_from_metadata(metadata: ProductKBMetadata) -> MetadataRow:
    payload = metadata.model_dump(mode="json")
    row = _empty_row()
    row["doc_path"] = payload["doc_path"]
    row["extract_method"] = payload["extract_method"]
    for field_name in EXTRACTED_FIELD_KEYS:
        field_payload = payload[field_name]
        row[field_name] = field_payload["value"]
        row[f"{field_name}_conf"] = field_payload["confidence"]
    row["audience"] = payload["audience"]
    row["visibility"] = payload["visibility"]
    row["owner_dept"] = payload["owner_dept"]
    row["shared_depts"] = " | ".join(payload["shared_depts"])
    row["needs_review"] = "是" if payload["needs_review"] else "否"
    row["review_reasons"] = " | ".join(payload["review_reasons"])
    return row


def _row_from_extract_error(doc_path: str, exc: MetadataExtractError) -> MetadataRow:
    row = _empty_row()
    row["doc_path"] = doc_path
    row["needs_review"] = "是"
    row["review_reasons"] = " | ".join(exc.review_reasons or ["MetadataExtractError"])
    return row


def _append_failed_jsonl(failed_path: Path, doc_path: Path, exc: Exception) -> None:
    failed_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "doc_path": str(doc_path),
        "ext": doc_path.suffix.lower() or "<none>",
        "error_type": type(exc).__name__,
    }
    with failed_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _load_done_paths(output_xlsx: Path) -> set[str]:
    if not output_xlsx.exists():
        return set()
    existing = pd.read_excel(output_xlsx)
    if "doc_path" not in existing:
        raise ValueError("Existing metadata workbook is missing doc_path")
    return {str(value) for value in existing["doc_path"].dropna()}


def _write_rows(output_xlsx: Path, rows: list[MetadataRow]) -> None:
    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    if output_xlsx.exists():
        existing = pd.read_excel(output_xlsx).reindex(columns=METADATA_COLUMN_KEYS)
    else:
        existing = pd.DataFrame(columns=METADATA_COLUMN_KEYS)
    appended = pd.DataFrame(rows, columns=METADATA_COLUMN_KEYS)
    combined = pd.concat([existing, appended], ignore_index=True)
    temporary = output_xlsx.with_suffix(output_xlsx.suffix + ".tmp")
    with temporary.open("wb") as handle:
        combined.to_excel(handle, index=False, engine="openpyxl")
    try:
        os.replace(temporary, output_xlsx)
    except PermissionError:
        os.replace(temporary, output_xlsx)


async def _extract_one(
    path: Path,
    semaphore: asyncio.Semaphore,
    failed_path: Path,
    failed_lock: asyncio.Lock,
) -> _Outcome:
    ext = path.suffix.lower() or "<none>"
    async with semaphore:
        try:
            doc_bytes = await asyncio.to_thread(path.read_bytes)
            metadata = await extract_product_kb_metadata(str(path), doc_bytes)
            return _Outcome(ext=ext, row=_row_from_metadata(metadata))
        except MetadataExtractError as exc:
            return _Outcome(ext=ext, row=_row_from_extract_error(str(path), exc))
        except Exception as exc:
            async with failed_lock:
                await asyncio.to_thread(_append_failed_jsonl, failed_path, path, exc)
            logger.warning("Unexpected batch extraction failure {} {}", ext, type(exc).__name__)
            return _Outcome(ext=ext, row=None, failed=True)


async def batch_extract(
    input_dir: Path,
    output_xlsx: Path,
    *,
    show_progress: bool = True,
) -> BatchSummary:
    """Extract all supported files and append rows to the review workbook."""

    scanned = await asyncio.to_thread(scan_input_files, input_dir)
    scanned = await asyncio.to_thread(_exclude_output_files, scanned, output_xlsx)
    done = await asyncio.to_thread(_load_done_paths, output_xlsx)
    todo = [path for path in scanned if str(path) not in done]
    semaphore = asyncio.Semaphore(settings.ingest_concurrency)
    failed_lock = asyncio.Lock()
    failed_path = output_xlsx.with_name(_FAILED_FILENAME)
    tasks = [
        asyncio.create_task(_extract_one(path, semaphore, failed_path, failed_lock))
        for path in todo
    ]
    rows: list[MetadataRow] = []
    failed = 0
    with tqdm(total=len(tasks), unit="doc", disable=not show_progress) as progress:
        for future in asyncio.as_completed(tasks):
            outcome = await future
            progress.set_postfix_str(outcome.ext, refresh=False)
            progress.update()
            if outcome.row is not None:
                rows.append(outcome.row)
            if outcome.failed:
                failed += 1

    await asyncio.to_thread(_write_rows, output_xlsx, rows)
    needs_review = sum(row["needs_review"] == "是" for row in rows)
    summary = BatchSummary(
        scanned=len(scanned),
        written=len(rows),
        needs_review=needs_review,
        failed=failed,
        skipped=len(scanned) - len(todo),
    )
    logger.info(
        "Batch extraction complete: written {} needs_review {} failed {} skipped {}",
        summary.written,
        summary.needs_review,
        summary.failed,
        summary.skipped,
    )
    return summary


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: batch_extract_product_kb.py <input_dir> <output_xlsx>")  # noqa: T201
        return 2
    try:
        summary = asyncio.run(batch_extract(Path(sys.argv[1]), Path(sys.argv[2])))
    except (OSError, ValueError):
        logger.error("Batch extraction could not complete")
        return 1
    print(  # noqa: T201
        f"written={summary.written} needs_review={summary.needs_review} "
        f"failed={summary.failed} skipped={summary.skipped}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
