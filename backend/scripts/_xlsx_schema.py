"""Shared xlsx schema for #26 write / #27 review / #28 ingest read."""

from __future__ import annotations

METADATA_COLUMNS: list[tuple[str, str]] = [
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

METADATA_COLUMN_KEYS: tuple[str, ...] = tuple(key for key, _ in METADATA_COLUMNS)
EXTRACTED_FIELD_KEYS: tuple[str, ...] = (
    "product_module",
    "product_version",
    "platform",
    "target_audience",
    "doc_category",
    "sensitivity",
)
