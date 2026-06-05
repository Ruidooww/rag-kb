# 任务 #71：Agent 工具集断言测试（落地原则 P2）

> **版本**：v1.0
> **创建日期**：2026-06-05
> **预估工时**：3-4 小时
> **前置任务**：#69（CRM 抽象 + tool_registry.py）
> **优先级**：🟡 中（独立小任务，可与 #69 同 PR 或 follow-up）

---

## §1 任务背景

CLAUDE.md 原则 P2 要求：`EXTERNAL_TOOLS` / `INTERNAL_TOOLS` 必须在单文件集中定义（如 `app/agents/tool_registry.py`），每次变更（加/删/改工具）必须配 1 个断言测试，证明工具集 diff 符合预期。

**反例**：CRM 工具误进 `EXTERNAL_TOOLS` → 单测立刻报错，不允许靠 code review 兜底。

本任务在 #69 落地 `tool_registry.py` 之后，补一个独立的断言测试 + CI gate，把"工具集变更必须经过断言"变成强制流程。

---

## §2 范围

- ✅ 新增 `backend/tests/agents/test_tool_registry.py`
- ✅ 工具集快照：固化 `EXTERNAL_TOOLS` / `INTERNAL_TOOLS` 当前成员清单（按 tool.name 排序）
- ✅ Sanity check 测试：CRM / internal search 类工具名不能出现在 EXTERNAL_TOOLS
- ✅ Diff 检测：工具集变更时测试 fail，提示开发者更新快照 + 在 PR 描述说明
- ✅ CI gate：pytest 跑通才允许 merge
- ❌ 不改 `tool_registry.py` 本体（#69 已交付）
- ❌ 不改业务 Agent 代码

---

## §3 任务目标

实现完成后必须满足：

1. `EXTERNAL_TOOLS` / `INTERNAL_TOOLS` 任何成员增删改，至少 1 个测试 fail
2. CRM 类工具（前缀 `get_customer` / `list_contract` / `list_contact` / `get_service` / `find_customer`）误入 `EXTERNAL_TOOLS` → 测试 fail + 错误信息明确
3. 内部 search 类工具（`search_docs`）误入 `EXTERNAL_TOOLS` → 测试 fail
4. 工具集快照存为可读 JSON，diff review 时清晰可见
5. 测试运行 < 1 秒

---

## §4 文件清单

### 4.1 新增 `backend/tests/agents/test_tool_registry.py`

```python
"""Tool registry assertion tests (原则 P2 落地)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.tool_registry import EXTERNAL_TOOLS, INTERNAL_TOOLS

SNAPSHOT_PATH = Path(__file__).parent / "tool_registry_snapshot.json"

# CRM / 内部 search 类工具前缀，绝不允许出现在 EXTERNAL_TOOLS
_INTERNAL_ONLY_PREFIXES = (
    "get_customer",
    "list_contract",
    "list_contact",
    "get_service",
    "find_customer",
    "search_docs",  # 内部 search（带 ACL 注入）
)


def _names(tools: list) -> list[str]:
    return sorted(t.name for t in tools)


def _load_snapshot() -> dict[str, list[str]]:
    if not SNAPSHOT_PATH.exists():
        pytest.fail(
            f"Snapshot file missing: {SNAPSHOT_PATH}. "
            "Run `pytest --snapshot-update` or create the file manually."
        )
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


class TestExternalToolsIsolation:
    """EXTERNAL_TOOLS 不能含任何内部工具（铁律 #10 layer 1）."""

    def test_no_crm_tool_in_external(self):
        for tool in EXTERNAL_TOOLS:
            for prefix in _INTERNAL_ONLY_PREFIXES:
                assert not tool.name.startswith(prefix), (
                    f"❌ 内部工具 {tool.name!r} 误入 EXTERNAL_TOOLS。"
                    f"违反 CLAUDE.md 铁律 #10 + 原则 P2。"
                    f"必须从 EXTERNAL_TOOLS 移除。"
                )

    def test_external_tools_must_be_explicitly_marked(self):
        """EXTERNAL_TOOLS 成员必须显式以 `_external` / `external_` 命名或在白名单内."""
        allowed_external = {"search_external_docs"}
        for tool in EXTERNAL_TOOLS:
            assert tool.name in allowed_external or "external" in tool.name, (
                f"❌ 工具 {tool.name!r} 没有 external 标记。"
                f"如确认对外可用，请加入 allowed_external 白名单 + 在 PR 描述说明。"
            )


class TestSnapshot:
    """工具集变更必须更新快照（强制 review 工具集 diff）."""

    def test_external_tools_match_snapshot(self):
        snapshot = _load_snapshot()
        actual = _names(EXTERNAL_TOOLS)
        expected = snapshot["external_tools"]
        assert actual == expected, (
            f"❌ EXTERNAL_TOOLS 变更未更新快照。\n"
            f"  当前：{actual}\n"
            f"  快照：{expected}\n"
            f"  如确认要改，更新 {SNAPSHOT_PATH.name} 并在 PR 描述写明变更原因。"
        )

    def test_internal_tools_match_snapshot(self):
        snapshot = _load_snapshot()
        actual = _names(INTERNAL_TOOLS)
        expected = snapshot["internal_tools"]
        assert actual == expected, (
            f"❌ INTERNAL_TOOLS 变更未更新快照。\n"
            f"  当前：{actual}\n"
            f"  快照：{expected}\n"
            f"  如确认要改，更新 {SNAPSHOT_PATH.name} 并在 PR 描述写明变更原因。"
        )


class TestNoOverlap:
    """工具不能同时在 EXTERNAL 和 INTERNAL（避免歧义）."""

    def test_no_tool_in_both_sets(self):
        external_names = {t.name for t in EXTERNAL_TOOLS}
        internal_names = {t.name for t in INTERNAL_TOOLS}
        overlap = external_names & internal_names
        assert not overlap, (
            f"❌ 工具同时出现在 EXTERNAL 和 INTERNAL: {overlap}。"
            f"必须二选一（通常应只在 INTERNAL）。"
        )
```

### 4.2 新增 `backend/tests/agents/tool_registry_snapshot.json`

```json
{
  "_comment": "工具集快照。任何变更必须同步更新此文件 + 在 PR 描述说明变更原因。",
  "_updated": "2026-06-05",
  "external_tools": [
    "search_external_docs"
  ],
  "internal_tools": [
    "find_customer_by_name",
    "get_customer_basic",
    "get_service_history",
    "list_contacts",
    "list_contracts",
    "search_docs"
  ]
}
```

### 4.3 修改 `backend/tests/agents/__init__.py`

若不存在则创建空文件。

### 4.4 修改 `backend/pyproject.toml`（可选）

在 `[tool.pytest.ini_options]` 加 marker 说明：

```toml
markers = [
  "tool_registry: 工具集断言测试（原则 P2 强制 gate）",
]
```

### 4.5 修改 `.github/workflows/ci.yml`（可选，如已有 CI）

确保 `pytest backend/tests/agents/test_tool_registry.py` 在 CI 中独立 step 运行，fail 时打印明显标记。

---

## §5 验收标准

### 硬指标

```bash
cd backend
uv run pytest tests/agents/test_tool_registry.py -v
# 7 个测试全过

uv run pytest tests/agents/test_tool_registry.py --cov=app.agents.tool_registry --cov-report=term-missing
# tool_registry.py 覆盖率 100%
```

### 反向验证（手动模拟攻击）

1. 临时在 `tool_registry.py` 把 `get_customer_basic` 加进 `EXTERNAL_TOOLS` → `test_no_crm_tool_in_external` 必须 fail，错误信息明确指向铁律 #10
2. 临时从 `INTERNAL_TOOLS` 删一个工具 → `test_internal_tools_match_snapshot` 必须 fail，提示更新快照
3. 临时把 `search_docs` 同时加到两个集合 → `test_no_tool_in_both_sets` 必须 fail

### CI gate

PR 上 `test_tool_registry.py` 失败必须阻断 merge（不允许 admin override）。

---

## §6 风险 & 已知问题

- **快照漂移**：若开发者直接 `--snapshot-update` 而不在 PR 描述说明变更原因，等于绕过 gate。缓解：PR review 模板加一条"工具集变更说明"checklist。
- **白名单滥用**：`allowed_external` 白名单可能被滥用（加新工具时图方便加白名单）。缓解：白名单变更需要架构师 review。
- **测试与实现耦合**：`_INTERNAL_ONLY_PREFIXES` 写死在测试里，新增 CRM 工具命名不符合前缀时测试漏检。缓解：#69 spec §4 列出标准命名前缀，新工具必须遵循。

---

## §7 禁止事项

- ❌ 在测试里 hardcoded `pytest.skip()`（绕过 gate）
- ❌ 把 `allowed_external` 白名单做成可由环境变量配置（必须 code review）
- ❌ 用 `os.environ` 关闭某个断言（必须改 spec + 代码 review）
- ❌ 在 `tool_registry.py` 里写动态导入工具（必须静态可读，便于 grep + diff）
- ❌ 测试断言只 `assert overlap` 不带错误信息（错误信息必须指向铁律 #10 / 原则 P2 + 修复指引）

---

## §8 参考

- `CLAUDE.md` v1.2 § 铁律 #10 / § 原则 P2
- `docs/tasks/W2-D3-69-crm-abstraction.md` § tool_registry.py 实现
- `docs/ANTIPATTERNS.md` J1（路由分流）/ K1（脱敏）作为相关防御层
- pytest snapshot 模式参考：https://github.com/syrupy-project/syrupy（本任务不引入额外依赖，手写 JSON 快照已足够）

---

_v1.0 | 2026-06-05_
