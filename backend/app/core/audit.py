"""Temporary audit compatibility layer until #70 lands real audit logging."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from functools import wraps
from typing import Any, TypeVar, cast


class AuditEventType(StrEnum):
    CRM_QUERY = "crm_query"
    CRM_WRITE = "crm_write"


class AuditSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


_T = TypeVar("_T", bound=Callable[..., Any])


def audit(
    *,
    event_type: AuditEventType,
    severity: AuditSeverity = AuditSeverity.INFO,
    target: Callable[..., str] | None = None,
    action: str | None = None,
) -> Callable[[_T], _T]:
    """No-op decorator preserving function behavior for #69 before #70."""

    def decorator(fn: _T) -> _T:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await fn(*args, **kwargs)

        return cast(_T, wrapper)

    return decorator
