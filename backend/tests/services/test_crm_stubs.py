from collections.abc import Awaitable, Callable

import pytest

from app.services.crm import FxiaokeCRM, HubspotCRM, SalesforceCRM, XiaoshouyiCRM


@pytest.mark.asyncio
@pytest.mark.parametrize("crm_cls", [XiaoshouyiCRM, FxiaokeCRM, HubspotCRM, SalesforceCRM])
@pytest.mark.parametrize(
    "method_call",
    [
        lambda crm: crm.get_customer("cust-001"),
        lambda crm: crm.list_customers(),
        lambda crm: crm.list_contracts("cust-001"),
        lambda crm: crm.list_contacts("cust-001"),
        lambda crm: crm.list_service_history("cust-001"),
        lambda crm: crm.find_customer_by_name("示例"),
    ],
)
async def test_stub_provider_methods_raise_not_implemented(
    crm_cls: type[object],
    method_call: Callable[[object], Awaitable[object]],
) -> None:
    crm = crm_cls()

    with pytest.raises(NotImplementedError, match="vendor selection"):
        await method_call(crm)
