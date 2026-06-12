from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.core.exceptions import MetadataExtractError
from app.models.document_meta import Audience, Visibility
from app.models.product_kb_metadata import DocCategory, ExtractMethod
from app.services import product_kb_extract
from app.services.product_kb_extract import extract_product_kb_metadata


def _raw_metadata(
    *,
    doc_category: str = "user_manual",
    sensitivity: int = 1,
    confidence: int = 90,
) -> str:
    return json.dumps(
        {
            "product_module": {"value": "client", "confidence": confidence},
            "product_version": {"value": "V4", "confidence": confidence},
            "platform": {"value": "windows", "confidence": confidence},
            "target_audience": {"value": "admin", "confidence": confidence},
            "doc_category": {"value": doc_category, "confidence": confidence},
            "sensitivity": {"value": sensitivity, "confidence": confidence},
        }
    )


class FakeLLM:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.completed_prompts: list[str] = []
        self.chat_messages: list[object] = []

    async def acomplete(self, prompt: str) -> SimpleNamespace:
        self.completed_prompts.append(prompt)
        return SimpleNamespace(text=self.raw)

    async def achat(self, messages: list[object]) -> SimpleNamespace:
        self.chat_messages.extend(messages)
        return SimpleNamespace(message=SimpleNamespace(content=self.raw))


async def test_text_path_extracts_all_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_llm = FakeLLM(_raw_metadata())
    monkeypatch.setattr(product_kb_extract, "get_llm", lambda: fake_llm)

    meta = await extract_product_kb_metadata("manual.txt", b"IP-Guard V4 client manual")

    assert meta.extract_method == ExtractMethod.TEXT
    assert meta.product_module.value == "client"
    assert meta.product_version.value == "V4"
    assert meta.platform.value == "windows"
    assert meta.target_audience.value == "admin"
    assert meta.doc_category.value == "user_manual"
    assert meta.sensitivity.value == 1
    assert fake_llm.completed_prompts


def test_vision_path_for_pptx() -> None:
    assert product_kb_extract._route_by_extension("deck.pptx") == ExtractMethod.VISION


def test_route_text_vs_vision_by_extension() -> None:
    assert product_kb_extract._route_by_extension("manual.txt") == ExtractMethod.TEXT
    assert product_kb_extract._route_by_extension("notes.md") == ExtractMethod.TEXT
    assert product_kb_extract._route_by_extension("deck.pptx") == ExtractMethod.VISION
    assert product_kb_extract._route_by_extension("sheet.xlsx") == ExtractMethod.VISION


async def test_unsupported_extension_raises_extract_error() -> None:
    with pytest.raises(MetadataExtractError) as exc_info:
        await extract_product_kb_metadata("private/folder/config.xlsx", b"xlsx")

    error = exc_info.value
    assert str(error) == "Failed to extract metadata"
    assert error.needs_review is True
    assert error.review_reasons == ["Unsupported extension .xlsx in lean MVP"]
    assert "private/folder" not in str(error)
    assert all("private/folder" not in reason for reason in error.review_reasons)


async def test_pdf_with_extractable_text_routes_to_text(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_llm = FakeLLM(_raw_metadata())
    monkeypatch.setattr(product_kb_extract, "get_llm", lambda: fake_llm)
    monkeypatch.setattr(product_kb_extract, "_extract_pdf_text", lambda _data: "PDF text")

    meta = await extract_product_kb_metadata("manual.pdf", b"%PDF")

    assert meta.extract_method == ExtractMethod.TEXT
    assert fake_llm.completed_prompts
    assert fake_llm.chat_messages == []


async def test_pdf_with_blank_text_routes_to_vision(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_llm = FakeLLM(_raw_metadata())
    monkeypatch.setattr(product_kb_extract, "get_llm", lambda: fake_llm)
    monkeypatch.setattr(product_kb_extract, "_extract_pdf_text", lambda _data: "")
    monkeypatch.setattr(product_kb_extract, "_to_pngs", lambda _data: [b"png"])

    meta = await extract_product_kb_metadata("scanned.pdf", b"%PDF")

    assert meta.extract_method == ExtractMethod.VISION
    assert fake_llm.completed_prompts == []
    assert fake_llm.chat_messages


def test_acl_defaults_for_user_manual_audience_customer_facing() -> None:
    meta = product_kb_extract._build_metadata(
        "manual.txt",
        ExtractMethod.TEXT,
        json.loads(_raw_metadata(doc_category=DocCategory.USER_MANUAL.value)),
    )

    product_kb_extract._apply_acl_defaults(meta)

    assert meta.audience == Audience.CUSTOMER_FACING
    assert meta.visibility == Visibility.PUBLIC
    assert meta.owner_dept is None


def test_acl_defaults_for_test_case_visibility_confidential() -> None:
    meta = product_kb_extract._build_metadata(
        "test-case.txt",
        ExtractMethod.TEXT,
        json.loads(_raw_metadata(doc_category=DocCategory.TEST_CASE.value, sensitivity=5)),
    )

    product_kb_extract._apply_acl_defaults(meta)

    assert meta.audience == Audience.INTERNAL_ONLY
    assert meta.visibility == Visibility.CONFIDENTIAL
    assert meta.owner_dept == "qa"


@pytest.mark.parametrize(
    ("category", "audience", "visibility", "owner_dept"),
    [
        (DocCategory.USER_MANUAL, Audience.CUSTOMER_FACING, Visibility.PUBLIC, None),
        (DocCategory.FAQ, Audience.CUSTOMER_FACING, Visibility.PUBLIC, None),
        (DocCategory.TEST_CASE, Audience.INTERNAL_ONLY, Visibility.CONFIDENTIAL, "qa"),
        (DocCategory.DEPLOYMENT, Audience.INTERNAL_ONLY, Visibility.INTERNAL, "impl"),
        (DocCategory.RELEASE_NOTE, Audience.INTERNAL_ONLY, Visibility.INTERNAL, None),
        (DocCategory.TROUBLESHOOT, Audience.INTERNAL_ONLY, Visibility.INTERNAL, "aftersales"),
        (DocCategory.OTHER, Audience.INTERNAL_ONLY, Visibility.INTERNAL, None),
    ],
)
def test_acl_defaults_by_doc_category(
    category: DocCategory,
    audience: Audience,
    visibility: Visibility,
    owner_dept: str | None,
) -> None:
    meta = product_kb_extract._build_metadata(
        "manual.txt",
        ExtractMethod.TEXT,
        json.loads(_raw_metadata(doc_category=category.value)),
    )

    product_kb_extract._apply_acl_defaults(meta)

    assert meta.audience == audience
    assert meta.visibility == visibility
    assert meta.owner_dept == owner_dept
    assert meta.shared_depts == []


def test_low_confidence_field_flags_needs_review(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(product_kb_extract.settings, "extract_confidence_threshold", 70)
    fields = json.loads(_raw_metadata())
    fields["platform"]["confidence"] = 69
    meta = product_kb_extract._build_metadata("manual.txt", ExtractMethod.TEXT, fields)

    product_kb_extract._check_needs_review(meta)

    assert meta.needs_review is True
    assert meta.review_reasons == ["Low confidence: platform"]


async def test_invalid_json_raises_extract_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(product_kb_extract, "get_llm", lambda: FakeLLM("not-json"))

    with pytest.raises(MetadataExtractError) as exc_info:
        await extract_product_kb_metadata("manual.txt", b"content")

    assert str(exc_info.value) == "Failed to extract metadata"


async def test_extract_error_does_not_leak_doc_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(product_kb_extract, "get_llm", lambda: FakeLLM("not-json"))
    secret_path = "C:/customers/secret-name/manual.txt"

    with pytest.raises(MetadataExtractError) as exc_info:
        await extract_product_kb_metadata(secret_path, b"content")

    assert secret_path not in str(exc_info.value)
    assert all(secret_path not in reason for reason in exc_info.value.review_reasons)


def test_prompt_renders_with_enums() -> None:
    prompt = product_kb_extract._render_prompt("IP-Guard content")

    assert "client" in prompt
    assert "windows" in prompt
    assert "user_manual" in prompt
    assert "IP-Guard content" in prompt


async def test_sensitivity_is_int_in_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        product_kb_extract, "get_llm", lambda: FakeLLM(_raw_metadata(sensitivity=4))
    )

    meta = await extract_product_kb_metadata("test.txt", b"test")

    assert meta.sensitivity.value == 4
    assert isinstance(meta.sensitivity.value, int)
