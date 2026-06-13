from __future__ import annotations

from app.models.document_meta import DocumentMetaSchema
from app.models.product_kb_metadata import ProductKBMetadata
from scripts._xlsx_schema import METADATA_COLUMNS

EXPECTED_COLUMNS = [
    ("doc_path", "文件路径"),
    ("extract_method", "抽取路径"),
    ("product_module", "产品模块"),
    ("product_module_conf", "模块置信度"),
    ("product_version", "产品版本"),
    ("product_version_conf", "版本置信度"),
    ("platform", "平台"),
    ("platform_conf", "平台置信度"),
    ("target_audience", "目标用户"),
    ("target_audience_conf", "目标用户置信度"),
    ("doc_category", "文档类型"),
    ("doc_category_conf", "类型置信度"),
    ("sensitivity", "敏感度"),
    ("sensitivity_conf", "敏感度置信度"),
    ("audience", "受众边界"),
    ("visibility", "可见性"),
    ("owner_dept", "归属部门"),
    ("shared_depts", "跨部门白名单"),
    ("needs_review", "需审核"),
    ("review_reasons", "审核原因"),
    ("reviewed_product_module", "审核后产品模块"),
    ("reviewed_doc_category", "审核后文档类型"),
    ("reviewed_sensitivity", "审核后敏感度"),
    ("review_status", "审核状态"),
]


def test_metadata_columns_snapshot() -> None:
    assert METADATA_COLUMNS == EXPECTED_COLUMNS


def test_extracted_field_keys_match_product_kb_metadata() -> None:
    keys = {key for key, _ in METADATA_COLUMNS}
    extracted_fields = {
        "product_module",
        "product_version",
        "platform",
        "target_audience",
        "doc_category",
        "sensitivity",
    }

    assert extracted_fields <= set(ProductKBMetadata.model_fields)
    assert extracted_fields <= keys
    assert {f"{field}_conf" for field in extracted_fields} <= keys


def test_acl_field_keys_match_document_meta_anchor() -> None:
    keys = {key for key, _ in METADATA_COLUMNS}
    acl_fields = {"audience", "visibility", "owner_dept", "shared_depts"}

    assert acl_fields <= set(DocumentMetaSchema.model_fields)
    assert acl_fields <= keys
