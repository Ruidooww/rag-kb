from datetime import datetime

import pytest

from app.agents.tools import crm_tools
from app.core.exceptions import PermissionDeniedError
from app.models.crm import Customer
from app.services.auth import User


def _internal_user() -> User:
    return User(
        user_id="local:alice",
        external_provider="local",
        external_user_id="alice",
        display_name="Alice",
        internal_dept_code="sales",
        role="employee",
        is_external=False,
    )


def _external_user() -> User:
    return User(
        user_id="wechat:openid-001",
        external_provider="wechat_mp",
        external_user_id="openid-001",
        display_name="External",
        is_external=True,
    )


class FakeCRM:
    async def get_customer(self, customer_id: str) -> Customer:
        return Customer(id=customer_id, name="示例科技", region="华东")

    async def list_contracts(self, customer_id: str) -> list[object]:
        return []

    async def list_contacts(self, customer_id: str) -> list[object]:
        return []

    async def list_service_history(
        self,
        customer_id: str,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[object]:
        return []

    async def find_customer_by_name(self, name_query: str) -> list[Customer]:
        return [Customer(id="cust-001", name="示例科技")]


@pytest.mark.asyncio
async def test_internal_user_can_call_crm_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crm_tools, "get_crm", lambda: FakeCRM())

    result = await crm_tools.get_customer_basic.ainvoke(
        {"customer_id": "cust-001", "user": _internal_user()}
    )

    assert result["id"] == "cust-001"
    assert result["name"] == "示例科技"


@pytest.mark.asyncio
async def test_external_user_is_rejected_before_crm_call(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def fail_if_called() -> FakeCRM:
        nonlocal called
        called = True
        return FakeCRM()

    monkeypatch.setattr(crm_tools, "get_crm", fail_if_called)

    with pytest.raises(PermissionDeniedError):
        await crm_tools.get_customer_basic.ainvoke(
            {"customer_id": "cust-001", "user": _external_user()}
        )

    assert called is False
