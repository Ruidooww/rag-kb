"""Search tools placeholders used by the tool registry."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
async def search_docs(query: str) -> str:
    """Search internal documents. ACL-aware implementation lands after #68/#42."""
    return f"internal search placeholder: {query}"


@tool
async def search_external_docs(query: str) -> str:
    """Search public documents exposed to external users."""
    return f"external search placeholder: {query}"
