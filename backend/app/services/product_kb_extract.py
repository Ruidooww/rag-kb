"""Lean-MVP product KB metadata extraction."""

from __future__ import annotations

import json
from collections.abc import Mapping
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from anyio import to_thread
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from llama_index.core.llms import ChatMessage, ImageBlock, TextBlock
from loguru import logger
from pdf2image import convert_from_bytes
from pypdf import PdfReader

from app.core.config import settings
from app.core.exceptions import MetadataExtractError
from app.models.document_meta import Audience, Visibility
from app.models.product_kb_metadata import (
    DocCategory,
    ExtractMethod,
    Platform,
    ProductKBMetadata,
    ProductModule,
    TargetAudience,
)
from app.services.llm import get_llm

_TEXT_EXTENSIONS = {".txt", ".md"}
_FIELD_NAMES = (
    "product_module",
    "product_version",
    "platform",
    "target_audience",
    "doc_category",
    "sensitivity",
)


async def extract_product_kb_metadata(doc_path: str, doc_bytes: bytes) -> ProductKBMetadata:
    """Extract one product document without persisting it."""

    suffix = Path(doc_path).suffix.lower()
    try:
        if suffix in _TEXT_EXTENSIONS:
            method = ExtractMethod.TEXT
            raw = await _call_llm_text(doc_bytes.decode("utf-8"))
        elif suffix == ".pdf":
            pdf_text = await to_thread.run_sync(_extract_pdf_text, doc_bytes)
            if pdf_text.strip():
                method = ExtractMethod.TEXT
                raw = await _call_llm_text(pdf_text)
            else:
                method = ExtractMethod.VISION
                images = await to_thread.run_sync(_to_pngs, doc_bytes)
                raw = await _call_llm_vision(images)
        else:
            reason = f"Unsupported extension {suffix or '<none>'} in lean MVP"
            raise MetadataExtractError(review_reasons=[reason])

        fields = _parse_json(raw)
        meta = _build_metadata(doc_path, method, fields)
        _apply_acl_defaults(meta)
        _check_needs_review(meta)
        return meta
    except MetadataExtractError:
        raise
    except Exception as exc:
        logger.warning(
            "Product KB metadata extraction failed for extension {}: {}",
            suffix or "<none>",
            type(exc).__name__,
        )
        raise MetadataExtractError() from exc


def _route_by_extension(doc_path: str) -> ExtractMethod:
    return (
        ExtractMethod.TEXT
        if Path(doc_path).suffix.lower() in _TEXT_EXTENSIONS
        else ExtractMethod.VISION
    )


def _extract_pdf_text(doc_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(doc_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _to_pngs(doc_bytes: bytes) -> list[bytes]:
    pages = convert_from_bytes(
        doc_bytes,
        dpi=settings.vision_dpi,
        first_page=1,
        last_page=settings.vision_max_pages,
    )
    images: list[bytes] = []
    for page in pages:
        buffer = BytesIO()
        page.save(buffer, format="PNG")
        images.append(buffer.getvalue())
    return images


async def _call_llm_text(doc_content: str) -> str:
    response = await get_llm().acomplete(_render_prompt(doc_content))
    return str(response.text)


async def _call_llm_vision(images: list[bytes]) -> str:
    blocks: list[TextBlock | ImageBlock] = [
        TextBlock(text=_render_prompt("See attached document page images.")),
        *[ImageBlock(image=image, image_mimetype="image/png") for image in images],
    ]
    response = await get_llm().achat([ChatMessage(role="user", blocks=blocks)])
    return str(response.message.content or "")


def _render_prompt(doc_content: str) -> str:
    prompts_dir = Path(settings.prompts_dir)
    if not prompts_dir.is_absolute():
        prompts_dir = Path(__file__).parents[2] / prompts_dir
    environment = Environment(
        loader=FileSystemLoader(prompts_dir),
        autoescape=False,
        undefined=StrictUndefined,
    )
    template = environment.get_template("extract_product_kb.txt")
    return template.render(
        product_module_enum=", ".join(member.value for member in ProductModule),
        platform_enum=", ".join(member.value for member in Platform),
        target_audience_enum=", ".join(member.value for member in TargetAudience),
        doc_category_enum=", ".join(member.value for member in DocCategory),
        doc_content=doc_content,
    )


def _parse_json(raw: str) -> dict[str, Any]:
    normalized = raw.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        normalized = "\n".join(lines[1:-1]).strip()
    parsed = json.loads(normalized)
    if not isinstance(parsed, Mapping):
        raise ValueError("Metadata response must be a JSON object")
    return {str(key): value for key, value in parsed.items()}


def _build_metadata(
    doc_path: str,
    method: ExtractMethod,
    fields: Mapping[str, Any],
) -> ProductKBMetadata:
    return ProductKBMetadata(doc_path=doc_path, extract_method=method, **dict(fields))


def _apply_acl_defaults(meta: ProductKBMetadata) -> None:
    category = str(meta.doc_category.value)
    if category in {DocCategory.USER_MANUAL.value, DocCategory.FAQ.value}:
        meta.audience = Audience.CUSTOMER_FACING
        meta.visibility = Visibility.PUBLIC
        meta.owner_dept = None
    elif category == DocCategory.TEST_CASE.value:
        meta.audience = Audience.INTERNAL_ONLY
        meta.visibility = Visibility.CONFIDENTIAL
        meta.owner_dept = "qa"
    elif category == DocCategory.DEPLOYMENT.value:
        meta.audience = Audience.INTERNAL_ONLY
        meta.visibility = Visibility.INTERNAL
        meta.owner_dept = "impl"
    elif category == DocCategory.TROUBLESHOOT.value:
        meta.audience = Audience.INTERNAL_ONLY
        meta.visibility = Visibility.INTERNAL
        meta.owner_dept = "aftersales"
    else:
        meta.audience = Audience.INTERNAL_ONLY
        meta.visibility = Visibility.INTERNAL
        meta.owner_dept = None
    meta.shared_depts = []


def _check_needs_review(meta: ProductKBMetadata) -> None:
    reasons = [
        f"Low confidence: {field_name}"
        for field_name in _FIELD_NAMES
        if cast(Any, getattr(meta, field_name)).confidence < settings.extract_confidence_threshold
    ]
    meta.needs_review = bool(reasons)
    meta.review_reasons = reasons
