"""Centralized tool registry for internal/external agent isolation.

PR #15 N3: 用白名单反向断言（_ALLOWED_EXTERNAL_TOOL_NAMES）替代原黑名单前缀法。
理由：黑名单只防"已知命名规律"的内部工具误入 EXTERNAL；新工具用未列前缀的
命名（如 `query_xxx` / `crm_lookup_yyy`）就能绕过黑名单。白名单强制每次新增
外部工具都要显式更新清单 + PR 描述说明，把"开放工具"动作必然落到 review。
"""

from __future__ import annotations

from app.agents.tools.crm_tools import (
    find_customer_by_name,
    get_customer_basic,
    get_service_history,
    list_contacts,
    list_contracts,
)
from app.agents.tools.search_tools import search_docs, search_external_docs

EXTERNAL_TOOLS = [search_external_docs]

INTERNAL_TOOLS = [
    search_docs,
    get_customer_basic,
    list_contracts,
    list_contacts,
    get_service_history,
    find_customer_by_name,
]

# 外部允许工具白名单。新增外部工具必须：
#   (1) 在此显式追加工具名
#   (2) PR 描述说明开放原因 + 是否补 prompt injection 测试（#72）
#   (3) 同步更新 backend/tests/agents/tool_registry_snapshot.json
_ALLOWED_EXTERNAL_TOOL_NAMES: frozenset[str] = frozenset({"search_external_docs"})

for _tool in EXTERNAL_TOOLS:
    assert _tool.name in _ALLOWED_EXTERNAL_TOOL_NAMES, (
        f"Tool {_tool.name!r} appears in EXTERNAL_TOOLS but is not in the allowed whitelist. "
        f"Either (a) remove it from EXTERNAL_TOOLS (if it's internal), "
        f"or (b) add it to _ALLOWED_EXTERNAL_TOOL_NAMES + add prompt injection tests in #72. "
        f"See CLAUDE.md 铁律 #10 + 原则 P2 + PR-15.md §2 N3."
    )
