from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AliasSource(StrEnum):
    MANUAL = "manual"
    CRM_SYNC = "crm_sync"
    OMNI_EXTRACT = "omni_extract"


class CustomerSchema(BaseModel):
    """DB/API view of a local customer master record."""

    id: int
    external_id: str | None = None
    name: str
    region: str | None = None
    industry: str | None = None
    owner_dept: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CustomerAliasSchema(BaseModel):
    id: int
    customer_id: int
    alias: str
    source: AliasSource = AliasSource.MANUAL
    confidence: int = Field(ge=0, le=100, default=100)
    created_at: datetime


class CustomerCreate(BaseModel):
    external_id: str | None = None
    name: str
    region: str | None = None
    industry: str | None = None
    owner_dept: str | None = None
    notes: str | None = None


class AliasCreate(BaseModel):
    alias: str
    source: AliasSource = AliasSource.MANUAL
    confidence: int = Field(ge=0, le=100, default=100)


class MatchResult(BaseModel):
    customer_id: int
    customer_name: str
    matched_alias: str | None = None
    score: int = Field(ge=0, le=100)
    method: str


class DocumentMetaCreate(BaseModel):
    doc_id: str
    customer_id: int | None = None
    doc_type: str
    title: str
    event_date: datetime | None = None
    storage_key: str
    status: str = "uploaded"
    audience: str = "internal_only"
    owner_dept: str | None = None
    visibility: str = "internal"
    sensitivity: int = Field(default=3, ge=1, le=5)
    shared_depts: list[str] = Field(default_factory=list)
    extra: str | None = None
