from types import SimpleNamespace

import pytest

from app.services import crm as crm_module
from app.services.crm import CRMError, FxiaokeCRM, HubspotCRM, SalesforceCRM, XiaoshouyiCRM
from app.services.crm_mock import MockCRM


@pytest.mark.parametrize(
    ("provider", "expected_type"),
    [
        ("mock", MockCRM),
        ("xiaoshouyi", XiaoshouyiCRM),
        ("fxiaoke", FxiaokeCRM),
        ("hubspot", HubspotCRM),
        ("salesforce", SalesforceCRM),
    ],
)
def test_get_crm_returns_configured_provider(
    provider: str,
    expected_type: type[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(crm_module, "settings", SimpleNamespace(crm_provider=provider))

    assert isinstance(crm_module.get_crm(), expected_type)


def test_get_crm_rejects_unknown_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crm_module, "settings", SimpleNamespace(crm_provider="unknown"))

    with pytest.raises(CRMError):
        crm_module.get_crm()
