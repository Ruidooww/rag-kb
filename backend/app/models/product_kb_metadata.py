from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.document_meta import Audience, Visibility


class ProductModule(StrEnum):
    CLIENT = "client"
    SERVER = "server"
    ENCRYPTION = "encryption"
    GATEWAY = "gateway"
    APPROVAL = "approval"
    DATA_ANALYSIS = "data_analysis"
    LICENSE = "license"
    BACKUP = "backup"
    SENSITIVE_DETECTION = "sensitive_detection"
    OTHER = "other"


class Platform(StrEnum):
    WINDOWS = "windows"
    MAC = "mac"
    LINUX = "linux"
    WEB = "web"
    MULTI = "multi"


class TargetAudience(StrEnum):
    ADMIN = "admin"
    IMPLEMENTATION = "implementation"
    AFTERSALES = "aftersales"
    SALES = "sales"
    CUSTOMER = "customer"


class DocCategory(StrEnum):
    USER_MANUAL = "user_manual"
    DEPLOYMENT = "deployment"
    FAQ = "faq"
    TEST_CASE = "test_case"
    RELEASE_NOTE = "release_note"
    TROUBLESHOOT = "troubleshoot"
    OTHER = "other"


class ExtractMethod(StrEnum):
    TEXT = "text"
    VISION = "vision"


class FieldConfidence(BaseModel):
    value: str | int | None = None
    confidence: int = Field(ge=0, le=100, default=0)


class ProductKBMetadata(BaseModel):
    doc_path: str
    extract_method: ExtractMethod
    product_module: FieldConfidence
    product_version: FieldConfidence
    platform: FieldConfidence
    target_audience: FieldConfidence
    doc_category: FieldConfidence
    sensitivity: FieldConfidence

    audience: Audience = Audience.INTERNAL_ONLY
    visibility: Visibility = Visibility.INTERNAL
    owner_dept: str | None = None
    shared_depts: list[str] = Field(default_factory=list)

    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
