"""Centralized tool registry for internal/external agent isolation."""

from __future__ import annotations

from app.agents.tools.crm_tools import (
    find_customer_by_name,
    get_customer_basic,
    get_service_history,
    list_contacts,
    list_contracts,
)
from app.agents.tools.search_tools import search_docs, search_external_docs

EXTERNAL_TOOLS = [search_external_docs]

INTERNAL_TOOLS = [
    search_docs,
    get_customer_basic,
    list_contracts,
    list_contacts,
    get_service_history,
    find_customer_by_name,
]

_INTERNAL_ONLY_PREFIXES = (
    "get_customer",
    "list_contract",
    "list_contact",
    "get_service",
    "find_customer",
    "search_docs",
)

for _tool in EXTERNAL_TOOLS:
    assert not any(_tool.name.startswith(prefix) for prefix in _INTERNAL_ONLY_PREFIXES), (
        f"Tool {_tool.name} looks internal but appears in EXTERNAL_TOOLS"
    )
