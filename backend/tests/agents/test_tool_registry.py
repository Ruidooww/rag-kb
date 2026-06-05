"""Tool registry assertion tests for CLAUDE.md principle P2."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.tool_registry import EXTERNAL_TOOLS, INTERNAL_TOOLS

pytestmark = pytest.mark.tool_registry

SNAPSHOT_PATH = Path(__file__).parent / "tool_registry_snapshot.json"

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


def _load_snapshot() -> dict[str, list[str]]:
    if not SNAPSHOT_PATH.exists():
        pytest.fail(
            f"Snapshot file missing: {SNAPSHOT_PATH}. "
            "Create it with the reviewed tool lists before merging."
        )
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_no_crm_or_internal_search_tool_in_external_tools() -> None:
    for tool in EXTERNAL_TOOLS:
        assert not any(tool.name.startswith(prefix) for prefix in _INTERNAL_ONLY_PREFIXES), (
            f"Internal tool {tool.name!r} must not appear in EXTERNAL_TOOLS"
        )


def test_tool_registry_snapshot() -> None:
    snapshot = _load_snapshot()

    assert _names(EXTERNAL_TOOLS) == snapshot["external_tools"]
    assert _names(INTERNAL_TOOLS) == snapshot["internal_tools"]


def test_no_tool_in_both_sets() -> None:
    assert not ({tool.name for tool in EXTERNAL_TOOLS} & {tool.name for tool in INTERNAL_TOOLS})
