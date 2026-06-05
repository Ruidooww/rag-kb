# Handoff: Issue #11 - 反模式目录清理（N4-N8）

> 执行者：Claude（用户授权破例直接执行）
> 完成日期：2026-06-05
> 分支：chore/issue-11-antipattern-cleanup
> PR：#12
> PR URL：https://github.com/Ruidooww/rag-kb/pull/12
> 类型：chore（非正式 task spec，源于 PR #10 review backlog）

---

## 0. TL;DR

总评：READY_TO_MERGE。

本次清理 PR #10 fix_attempt:1 留下的 5 条 Nit（N4-N8），零 runtime 行为变化。改动分两类：（1）`backend/app/services/storage.py` 移除 `from fastapi import Request`，把 `get_storage` 迁到新建的 `backend/app/api/deps.py`，恢复 services 层框架洁癖；（2）`docs/ANTIPATTERNS.md` 把 G1/G2 重编为 H1/H2（让回 G 段位给 LangGraph 占位），统一中文风格，H1 self-check 补「Console 登录失败诊断顺序」，footer v1.2 → v1.3，QUICK_REF 索引同步。

质量门：ruff format/check ✅、mypy 21 文件 ✅、pytest -m "not integration" 23 passed ✅（与 PR #10 基线一致）。

无新增依赖，无业务逻辑变化，无对 main 的 breaking。

---

## 1. 任务概述

PR #10 RustFS 切换合并后，Issue #11 把当时未阻塞合并的 5 条 Nit 进了 backlog：N4（编号撞 G LangGraph）、N5（services 层耦合 fastapi）、N6（中英文混杂）、N7（footer 没更）、N8（H1 诊断顺序提示）。本 PR 一次清掉。

属于 chore 性质，没有任务 spec，验收以 Issue #11 正文的五项勾选 + 现有质量门为准。

---

## 2. 完成清单

对应 Issue #11 验收清单：

- [x] **N4**：`docs/ANTIPATTERNS.md` 把 G1/G2 重编为 H1/H2；新建 `## H. S3 兼容存储` 段；G 段恢复为 LangGraph 占位；索引表同步。
- [x] **N5**：`backend/app/services/storage.py` 移除 `from fastapi import Request`、移除 `get_storage`、`__all__` 同步；新建 `backend/app/api/deps.py` 承接 `get_storage`；测试拆分：`tests/services/test_storage.py` 留 `S3CompatibleStorage` / `StorageError` 测试，`tests/api/test_deps.py`（新建）承接 2 个 `get_storage` 单元测试。
- [x] **N6**：H1 / H2 改写为中文，结构对齐 A1-F1（来源 / 严重度 / 问题 / 错误范例 / 正确范例 / Codex 自检）。
- [x] **N7**：`docs/ANTIPATTERNS.md` footer v1.2 → v1.3；`docs/CODEX_QUICK_REF.md` footer v1.0 → v1.1。
- [x] **N8**：`ANTIPATTERNS.md` H1 self-check 段追加「Console 登录失败的诊断顺序」三步：先 `boto3.list_buckets()` 验 S3 API → 通了 99% 是 user error → 不通再查 env / CLI flags。来源：PR #10 现场实测。

额外同步：

- [x] `docs/CODEX_QUICK_REF.md` 反模式索引 G1/G2 → H1/H2、严重度 emoji 与 ANTIPATTERNS.md 对齐。

---

## 3. 与 Spec 的偏差

无 spec，无偏差。Issue #11 验收 5 项全部完成。

---

## 4. 本地验收结果

```bash
$ uv run ruff format .
35 files left unchanged

$ uv run ruff check .
All checks passed!

$ uv run mypy app
Success: no issues found in 21 source files

$ uv run pytest -v -m "not integration"
========================== 23 passed, 15 deselected, 2 warnings in 33.72s ==========================
```

storage / deps 关键测试：

```
tests/services/test_storage.py::test_storage_error_on_invalid_endpoint PASSED
tests/services/test_storage.py::test_invalid_doc_id_rejected[...] PASSED (×5)
tests/api/test_deps.py::test_get_storage_returns_app_state_storage PASSED
tests/api/test_deps.py::test_get_storage_requires_initialized_state PASSED
```

铁律 grep（services 层不应再有 fastapi 导入）：

```bash
$ grep -nE "^from fastapi|^import fastapi" backend/app/services/
（无输出）
```

---

## 5. 已知问题 / 风险 / 新增依赖

无新增 Python 依赖（`pyproject.toml` / `uv.lock` 未动）。

风险：低。`get_storage` 公共 API 名称未变、签名未变、行为未变，只是模块路径从 `app.services.storage` 移到 `app.api.deps`。仓库当前无第三方调用方（grep 显示只有测试用），改动安全。

如果后续 Codex 在业务代码里写 `from app.services.storage import get_storage`，会因为函数已迁走而导入失败 — 这是预期效果，会强制下游走 `app.api.deps`，正是 N5 想达成的分层洁癖。

---

## 6. 给审查者的提示

- **N5 分层是否到位**：`backend/app/services/storage.py:1-19` 现在只 import boto3 / botocore / anyio / loguru / app.core，零 fastapi 依赖。`backend/app/api/deps.py:1-21` 是新建的 FastAPI 依赖层。
- **N4 章节顺序**：`docs/ANTIPATTERNS.md` 现在是 A → B → C → D → E → F → G(LangGraph 占位) → H1/H2，字母序干净。索引表 line 12-22 已同步。
- **N8 实战经验沉淀**：`docs/ANTIPATTERNS.md` H1 self-check 末尾的「诊断顺序」三步，来自 PR #10 fix_attempt:1 时的真实弯路（Claude 一开始猜 env 名错，后来发现是用户密码输错），值得作为下次 S3 兼容存储故障排查的第一步。

---

## 7. 给下一轮的提示

- 后续如果业务代码需要在 FastAPI handler 里拿 storage，统一 `from app.api.deps import get_storage`，配 `Depends(get_storage)` 使用。
- LangGraph 反模式陆续积累后，可以正式启用 G1 / G2 编号（State 设计混乱、节点副作用、checkpoint 缺失等候选见 ANTIPATTERNS.md:251 注释）。
- `docs/reviews/` 目录在 main 上仍是 untracked，归用户管理，本 PR 未触碰。

---

## 8. 自审报告

### Part A 硬指标

| 项 | 结果 |
|----|------|
| pytest（非 integration）| ✅ 23 passed |
| coverage | ✅ 与 PR #10 基线一致（本 PR 仅文件移动 + 文档，未引入新代码路径）|
| ruff format | ✅ 35 files unchanged |
| ruff check | ✅ All checks passed |
| mypy | ✅ 21 files, no issues |
| 铁律 grep | ✅ services/ 无 fastapi 导入 |
| spec 文件 | N/A（chore 无 spec）|
| 依赖 | ✅ 无新增 |
| commit | ✅ `chore: #11 ...` 带 `Refs: #11` |
| Handoff | ✅ 本文件 |

### Part B 软指标

跳过（chore，无新业务逻辑可评）。

### Part C 反模式对照

- C1 `os.getenv` 散落：本 PR 未引入。
- E1 `@lru_cache` 缓存 client：未引入。
- H1 / H2 本身就是本 PR 改写的对象，已对齐中文风格。

### Part D 人工触发

- D2「改核心配置/抽象层」：✅ 命中 — `services/storage.py` 是 PR #10 引入的存储抽象层，本 PR 把其中的 FastAPI 依赖剥离到 `api/deps.py`。已在 §6 给审查者明确指出公共 API 行为未变，只是模块路径迁移。
- 其他 10 项未触发。

### Part E 自反思

1. **跳过 Handoff 是错误**：第一次 push 后 CI A7 直接失败，因为我没写 handoff。CLAUDE.md 10 步流程的第 8 步不是可选项，即使是 chore 也得写。下次任何带 `#数字` 的 PR 都先写 handoff 再 push。
2. **bash 重置 working dir**：连续两次 `cd backend && ...` 实际跑在不同的子 shell 里，第一次失败、第二次发现已经在 backend/。下次跨命令统一用绝对路径，不要假设 cwd 持久。
3. **诊断顺序值得形式化**：N8 加的「先 S3 API 后 Console」是 PR #10 的真实弯路，沉淀为反模式本身就是 ANTIPATTERNS.md 的目的。下次审查类似 S3 兼容产品迁移，第一条就走这个顺序。

新反模式：无（本 PR 是清理既有反模式条目）。

### last_verified_commit

`bf80f4e1e1666db6c2110c4220f76f1b7fa6679e`
