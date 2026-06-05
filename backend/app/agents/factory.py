"""Agent construction factory."""

from __future__ import annotations

from typing import Any

from langgraph.prebuilt import create_react_agent

from app.agents.tool_registry import EXTERNAL_TOOLS, INTERNAL_TOOLS
from app.services.auth import User
from app.services.llm import get_llm


def build_agent(user: User) -> Any:
    """Build an agent with a physically separated tool set."""
    tools = EXTERNAL_TOOLS if user.is_external else INTERNAL_TOOLS
    return create_react_agent(get_llm(), tools)
