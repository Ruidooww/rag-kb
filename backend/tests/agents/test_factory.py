from types import SimpleNamespace

import pytest

from app.agents import factory
from app.services.auth import User


def _user(*, is_external: bool) -> User:
    return User(
        user_id="user-001",
        external_provider="local",
        external_user_id="user-001",
        display_name="User",
        is_external=is_external,
    )


def _tool_names(tools: list[object]) -> list[str]:
    return sorted(str(tool.name) for tool in tools)


def test_build_agent_uses_external_tools_for_external_user(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_create_react_agent(_llm: object, tools: list[object]) -> SimpleNamespace:
        captured["tools"] = _tool_names(tools)
        return SimpleNamespace(tools=tools)

    monkeypatch.setattr(factory, "get_llm", lambda: object())
    monkeypatch.setattr(factory, "create_react_agent", fake_create_react_agent)

    agent = factory.build_agent(_user(is_external=True))

    assert agent is not None
    assert captured["tools"] == ["search_external_docs"]


def test_build_agent_uses_internal_tools_for_internal_user(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_create_react_agent(_llm: object, tools: list[object]) -> SimpleNamespace:
        captured["tools"] = _tool_names(tools)
        return SimpleNamespace(tools=tools)

    monkeypatch.setattr(factory, "get_llm", lambda: object())
    monkeypatch.setattr(factory, "create_react_agent", fake_create_react_agent)

    factory.build_agent(_user(is_external=False))

    assert "get_customer_basic" in captured["tools"]
    assert "search_docs" in captured["tools"]
