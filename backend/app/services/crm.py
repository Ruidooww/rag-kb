"""CRM abstraction layer.

Business code must call ``get_crm()`` instead of importing a vendor SDK.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from typing import Final

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.crm import Contact, Contract, Customer, ServiceHistory

__all__ = [
    "CRMError",
    "CRMService",
    "FxiaokeCRM",
    "HubspotCRM",
    "SalesforceCRM",
    "XiaoshouyiCRM",
    "get_crm",
]


class CRMError(AppException):
    error_code = "CRM_ERROR"
    status_code = 502


class CRMService(ABC):
    @abstractmethod
    async def get_customer(self, customer_id: str) -> Customer | None:
        """Return one customer by normalized customer id."""

    @abstractmethod
    async def list_customers(
        self,
        *,
        region: str | None = None,
        industry: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]:
        """List customers with optional filters."""

    @abstractmethod
    async def list_contracts(self, customer_id: str) -> list[Contract]:
        """List contracts for one customer."""

    @abstractmethod
    async def list_contacts(self, customer_id: str) -> list[Contact]:
        """List contacts for one customer."""

    @abstractmethod
    async def list_service_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[ServiceHistory]:
        """List service history for one customer."""

    @abstractmethod
    async def find_customer_by_name(self, name_query: str) -> list[Customer]:
        """Find customers by a case-insensitive name query."""


class _VendorStubCRM(CRMService):
    provider_name = "VendorCRM"

    def _not_ready(self) -> NotImplementedError:
        return NotImplementedError(f"{self.provider_name}: implement after vendor selection")

    async def get_customer(self, customer_id: str) -> Customer | None:
        raise self._not_ready()

    async def list_customers(
        self,
        *,
        region: str | None = None,
        industry: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]:
        raise self._not_ready()

    async def list_contracts(self, customer_id: str) -> list[Contract]:
        raise self._not_ready()

    async def list_contacts(self, customer_id: str) -> list[Contact]:
        raise self._not_ready()

    async def list_service_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[ServiceHistory]:
        raise self._not_ready()

    async def find_customer_by_name(self, name_query: str) -> list[Customer]:
        raise self._not_ready()


class XiaoshouyiCRM(_VendorStubCRM):
    provider_name = "XiaoshouyiCRM"


class FxiaokeCRM(_VendorStubCRM):
    provider_name = "FxiaokeCRM"


class HubspotCRM(_VendorStubCRM):
    provider_name = "HubspotCRM"


class SalesforceCRM(_VendorStubCRM):
    provider_name = "SalesforceCRM"


def _build_mock() -> CRMService:
    from app.services.crm_mock import MockCRM

    return MockCRM()


_PROVIDERS: Final[dict[str, Callable[[], CRMService]]] = {
    "mock": _build_mock,
    "xiaoshouyi": XiaoshouyiCRM,
    "fxiaoke": FxiaokeCRM,
    "hubspot": HubspotCRM,
    "salesforce": SalesforceCRM,
}


def get_crm() -> CRMService:
    builder = _PROVIDERS.get(settings.crm_provider)
    if builder is None:
        raise CRMError(f"Unknown CRM_PROVIDER: {settings.crm_provider}")
    return builder()
