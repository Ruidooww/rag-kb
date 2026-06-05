"""CRM data models independent from any specific vendor."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CustomerSize(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ENTERPRISE = "enterprise"


class ContractStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    PENDING = "pending"


class Customer(BaseModel):
    id: str
    name: str
    industry: str | None = None
    size: CustomerSize | None = None
    region: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Contract(BaseModel):
    id: str
    customer_id: str
    start_date: date
    end_date: date | None = None
    amount: float
    currency: str = "CNY"
    status: ContractStatus
    metadata: dict[str, Any] = Field(default_factory=dict)


class Contact(BaseModel):
    id: str
    customer_id: str
    name: str
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServiceHistory(BaseModel):
    id: str
    customer_id: str
    type: str
    created_at: datetime
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
