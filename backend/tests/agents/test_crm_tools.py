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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "tool_input"),
    [
        ("get_customer_basic", {"customer_id": "cust-001"}),
        ("list_contracts", {"customer_id": "cust-001"}),
        ("list_contacts", {"customer_id": "cust-001"}),
        ("get_service_history", {"customer_id": "cust-001"}),
        ("find_customer_by_name", {"name_query": "示例"}),
    ],
)
async def test_external_user_error_message_no_tool_leak(
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    tool_input: dict[str, object],
) -> None:
    """PR #15 N1 / PR #14 N1: 错误信息绝不可回显工具名或内部识别符（防枚举攻击）.

    所有 5 个内部 CRM 工具对外部用户必须返回**精确等值**的 "Permission denied"，
    任何 tool_name / customer_id / 工具内部细节出现在 raise message 都视为回归。
    """
    monkeypatch.setattr(crm_tools, "get_crm", lambda: FakeCRM())
    tool = getattr(crm_tools, tool_name)
    payload = {**tool_input, "user": _external_user()}

    with pytest.raises(PermissionDeniedError) as exc_info:
        await tool.ainvoke(payload)

    message = str(exc_info.value)
    # 精确等值：不允许任何前缀 / 后缀 / 调试信息
    assert message == "Permission denied", (
        f"Tool {tool_name} 错误信息泄漏内部细节：{message!r}。"
        f"必须精确等于 'Permission denied'，不允许回显工具名 / customer_id。"
    )
    # 兜底反向断言：不允许出现任何工具名
    forbidden_substrings = (
        "get_customer",
        "list_contract",
        "list_contact",
        "get_service",
        "find_customer",
        "search_docs",
        "customer_id",
        "cust-001",
        "示例",
    )
    for forbidden in forbidden_substrings:
        assert forbidden not in message, (
            f"Tool {tool_name} 错误信息含禁止子串 {forbidden!r}：{message!r}"
        )
