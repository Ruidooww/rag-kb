from pathlib import Path

import pytest

from app.services import crm_mock
from app.services.crm_mock import MockCRM


@pytest.fixture
def mock_crm_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "mock_crm"
    root.mkdir()
    (root / "customers.yaml").write_text(
        """
- id: cust-001
  name: 示例科技
  industry: software
  size: medium
  region: 华东
  metadata:
    tier: A
- id: cust-002
  name: Demo Group
  industry: manufacturing
  size: enterprise
  region: 华北
  metadata: {}
""".strip(),
        encoding="utf-8",
    )
    (root / "contracts.yaml").write_text(
        """
- id: contract-001
  customer_id: cust-001
  start_date: 2026-01-01
  end_date: 2026-12-31
  amount: 120000
  currency: CNY
  status: active
  metadata: {}
""".strip(),
        encoding="utf-8",
    )
    (root / "contacts.yaml").write_text(
        """
- id: contact-001
  customer_id: cust-001
  name: 张三
  role: IT
  phone: "13800000000"
  email: zhangsan@example.test
  metadata: {}
""".strip(),
        encoding="utf-8",
    )
    (root / "service_history.yaml").write_text(
        """
- id: service-001
  customer_id: cust-001
  type: visit
  created_at: 2026-06-01T09:00:00
  summary: 完成上线回访
  metadata: {}
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(crm_mock.settings, "mock_crm_data_path", str(root))
    return root


@pytest.mark.asyncio
async def test_mock_crm_loads_fixture_and_gets_customer(mock_crm_data: Path) -> None:
    crm = MockCRM()

    customer = await crm.get_customer("cust-001")

    assert customer is not None
    assert customer.name == "示例科技"
    assert customer.region == "华东"
    assert await crm.get_customer("missing") is None


@pytest.mark.asyncio
async def test_mock_crm_filters_and_finds_customers(mock_crm_data: Path) -> None:
    crm = MockCRM()

    eastern = await crm.list_customers(region="华东")
    found = await crm.find_customer_by_name("demo")

    assert [customer.id for customer in eastern] == ["cust-001"]
    assert [customer.id for customer in found] == ["cust-002"]


@pytest.mark.asyncio
async def test_mock_crm_lists_related_records(mock_crm_data: Path) -> None:
    crm = MockCRM()

    contracts = await crm.list_contracts("cust-001")
    contacts = await crm.list_contacts("cust-001")
    history = await crm.list_service_history("cust-001")

    assert contracts[0].id == "contract-001"
    assert contacts[0].email == "zhangsan@example.test"
    assert history[0].summary == "完成上线回访"


@pytest.mark.asyncio
async def test_mock_crm_missing_fixture_dir_returns_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(crm_mock.settings, "mock_crm_data_path", str(tmp_path / "missing"))
    crm = MockCRM()

    assert await crm.list_customers() == []
    assert await crm.get_customer("cust-001") is None
