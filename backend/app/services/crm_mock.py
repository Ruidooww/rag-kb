"""Mock CRM backed by local YAML fixtures."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from app.core.config import PROJECT_ROOT, settings
from app.models.crm import Contact, Contract, Customer, ServiceHistory
from app.services.crm import CRMService


class MockCRM(CRMService):
    def __init__(self) -> None:
        self._customers: dict[str, Customer] = {}
        self._contracts: dict[str, list[Contract]] = {}
        self._contacts: dict[str, list[Contact]] = {}
        self._history: dict[str, list[ServiceHistory]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        root = Path(settings.mock_crm_data_path)
        if not root.is_absolute():
            root = PROJECT_ROOT / root
        if not root.exists():
            logger.warning("MockCRM data path not found: {}", root)
            self._loaded = True
            return

        for raw_customer in _load_yaml(root / "customers.yaml"):
            customer = Customer.model_validate(raw_customer)
            self._customers[customer.id] = customer
        for raw_contract in _load_yaml(root / "contracts.yaml"):
            contract = Contract.model_validate(raw_contract)
            self._contracts.setdefault(contract.customer_id, []).append(contract)
        for raw_contact in _load_yaml(root / "contacts.yaml"):
            contact = Contact.model_validate(raw_contact)
            self._contacts.setdefault(contact.customer_id, []).append(contact)
        for raw_history in _load_yaml(root / "service_history.yaml"):
            item = ServiceHistory.model_validate(raw_history)
            self._history.setdefault(item.customer_id, []).append(item)

        self._loaded = True
        logger.info(
            "MockCRM loaded: {} customers / {} contracts",
            len(self._customers),
            sum(len(items) for items in self._contracts.values()),
        )

    async def get_customer(self, customer_id: str) -> Customer | None:
        self._ensure_loaded()
        return self._customers.get(customer_id)

    async def list_customers(
        self,
        *,
        region: str | None = None,
        industry: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Customer]:
        self._ensure_loaded()
        items = list(self._customers.values())
        if region:
            items = [customer for customer in items if customer.region == region]
        if industry:
            items = [customer for customer in items if customer.industry == industry]
        return items[offset : offset + limit]

    async def list_contracts(self, customer_id: str) -> list[Contract]:
        self._ensure_loaded()
        return self._contracts.get(customer_id, [])

    async def list_contacts(self, customer_id: str) -> list[Contact]:
        self._ensure_loaded()
        return self._contacts.get(customer_id, [])

    async def list_service_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[ServiceHistory]:
        self._ensure_loaded()
        items = self._history.get(customer_id, [])
        if since is not None:
            items = [item for item in items if item.created_at >= since]
        return items[:limit]

    async def find_customer_by_name(self, name_query: str) -> list[Customer]:
        self._ensure_loaded()
        query = name_query.strip().lower()
        if not query:
            return []
        return [customer for customer in self._customers.values() if query in customer.name.lower()]


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError(f"MockCRM fixture must be a list: {path}")
    return [item for item in raw if isinstance(item, dict)]
