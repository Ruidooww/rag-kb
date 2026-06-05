from app.agents.tool_registry import EXTERNAL_TOOLS, INTERNAL_TOOLS

_INTERNAL_ONLY_PREFIXES = (
    "get_customer",
    "list_contract",
    "list_contact",
    "get_service",
    "find_customer",
    "search_docs",
)


def _names(tools: list[object]) -> list[str]:
    return sorted(str(tool.name) for tool in tools)


def test_no_crm_or_internal_search_tool_in_external_tools() -> None:
    for tool in EXTERNAL_TOOLS:
        assert not any(tool.name.startswith(prefix) for prefix in _INTERNAL_ONLY_PREFIXES), (
            f"Internal tool {tool.name!r} must not appear in EXTERNAL_TOOLS"
        )


def test_tool_registry_snapshot() -> None:
    assert _names(EXTERNAL_TOOLS) == ["search_external_docs"]
    assert _names(INTERNAL_TOOLS) == [
        "find_customer_by_name",
        "get_customer_basic",
        "get_service_history",
        "list_contacts",
        "list_contracts",
        "search_docs",
    ]


def test_no_tool_in_both_sets() -> None:
    assert not ({tool.name for tool in EXTERNAL_TOOLS} & {tool.name for tool in INTERNAL_TOOLS})
