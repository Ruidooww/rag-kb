"""LangGraph CRM tools.

Every CRM tool performs an internal-user check before calling ``get_crm()``.
"""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool
from loguru import logger

from app.core.audit import AuditEventType, audit
from app.core.exceptions import PermissionDeniedError
from app.services.auth import User
from app.services.crm import get_crm


def _check_internal(user: User, tool_name: str) -> None:
    if user.is_external:
        # 详细信息只走 audit log，不进 raise message（防枚举攻击 — PR #14 N1 / PR #15 N1）
        logger.warning(
            "External user {} attempted to call internal CRM tool {}",
            user.user_id,
            tool_name,
        )
        # 对外统一错误：不回显 tool_name / customer_id / 任何内部识别符
        raise PermissionDeniedError("Permission denied")


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda customer_id, user, **_: f"customer:{customer_id}",
)
async def get_customer_basic(customer_id: str, user: User) -> dict[str, object]:
    """Get basic customer information."""
    _check_internal(user, "get_customer_basic")
    customer = await get_crm().get_customer(customer_id)
    return customer.model_dump() if customer else {}


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda customer_id, user, **_: f"customer:{customer_id}:contracts",
)
async def list_contracts(customer_id: str, user: User) -> list[dict[str, object]]:
    """List customer contracts."""
    _check_internal(user, "list_contracts")
    contracts = await get_crm().list_contracts(customer_id)
    return [contract.model_dump() for contract in contracts]


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda customer_id, user, **_: f"customer:{customer_id}:contacts",
)
async def list_contacts(customer_id: str, user: User) -> list[dict[str, object]]:
    """List customer contacts."""
    _check_internal(user, "list_contacts")
    contacts = await get_crm().list_contacts(customer_id)
    return [contact.model_dump() for contact in contacts]


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda customer_id, since, user, **_: f"customer:{customer_id}:history",
)
async def get_service_history(
    customer_id: str,
    since: datetime | None = None,
    user: User | None = None,
) -> list[dict[str, object]]:
    """List customer service history."""
    if user is None:
        raise PermissionDeniedError("CRM tool requires user context")
    _check_internal(user, "get_service_history")
    history = await get_crm().list_service_history(customer_id, since=since)
    return [item.model_dump() for item in history]


@tool
@audit(
    event_type=AuditEventType.CRM_QUERY,
    target=lambda name_query, user, **_: f"search:{name_query[:64]}",
)
async def find_customer_by_name(name_query: str, user: User) -> list[dict[str, object]]:
    """Find customers by name."""
    _check_internal(user, "find_customer_by_name")
    customers = await get_crm().find_customer_by_name(name_query)
    return [customer.model_dump() for customer in customers]
