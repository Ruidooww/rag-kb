# Handoff 标准模板 v2.1

> **作用**：定义每个任务 Handoff 文档的标准结构。
> **使用方式**：Codex 完成任务时按本模板创建 `docs/handoffs/W?-D?-N-handoff.md`。
> **关键创新（v2.1）**：新增 §0 TL;DR（审查者 30 秒速读）+ §8 自审查报告。

---

## Handoff 完整模板（复制使用）

```
# Handoff: 任务 #N - [任务标题]

> **执行者**：Codex
> **完成日期**：YYYY-MM-DD
> **分支**：feat/W?-D?-N-xxx
> **PR**：#X
> **基于**：上一个 handoff [W?-D?-M-handoff.md]

---

## 0. TL;DR（审查者 30 秒速读）

🟢 **总评**：PASS（可合并）
⚠️ **总评**：NEEDS_REVIEW（需关注但可合并）
🔴 **总评**：NEEDS_HUMAN（必须人工 review）

### 关键数据
- 新增代码：X 行（实现 Y / 测试 Z）
- 覆盖率：A% (↑/↓ B%)
- 偏差：N 条
- Self-review：A=✅ B=✅ C=18/18 ✅ D=✅ E=✅
- fix_attempt 次数：0 / 1 / 2 / 3

### 最大风险
[1 句话]

### 最大亮点
[1 句话]

### 给审查者的 3 个看点
1. ...
2. ...
3. ...

---

## 1. 任务概述

[2-3 句话说明本任务做了什么、为什么这样设计]

---

## 2. 完成清单（对应 spec §4）

- [x] backend/app/xxx.py
- [x] backend/tests/services/test_xxx.py
- [x] [其他文件]
- [ ] [未完成的项 - 说明原因]

---

## 3. 与 Spec 的偏差

每个偏差：偏离什么、为什么、对应 commit hash、影响。

- **偏差 1**：[描述]
  - Spec 原文：[引用]
  - 实际实现：[说明]
  - 理由：[原因]
  - Commit：[hash]
  - 影响：[对验收/后续的影响]

（无偏差写"无"）

---

## 4. 本地验收结果

| 项目 | 结果 | 备注/原始输出 |
|------|------|--------------|
| uv sync | ✅/❌ | 耗时 X 秒 |
| uv run pytest -v | ✅/❌ | X passed, Y failed, Z skipped |
| 覆盖率 | ✅/❌ | A%（≥70% / ≥85% 核心） |
| ruff check | ✅/❌ | 0 errors / [错误数] |
| ruff format --check | ✅/❌ | 无变更 |
| mypy strict | ✅/❌ | 0 errors / [错误数] |
| Part A3 grep（铁律+敏感词） | ✅/❌ | 各 grep exit code |
| commit message 规范 | ✅/❌ | git log 输出 |
| 依赖安全 | ✅/❌ | 新增依赖列表+license |
| CI workflow | ✅/❌ | Run URL |

### 关键命令原始输出

[贴 pytest / ruff / mypy 实际输出]

---

## 5. 已知问题 / 风险

- 风险 1：[描述]
  - 影响范围：[哪些功能可能受影响]
  - 缓解措施：[已做的 / 待做的]
- 风险 2：...

### 新增第三方依赖（如有）
- `package_name==X.Y.Z`，License: [MIT/Apache/...]，用途：[简述]

---

## 6. 给审查者的提示（至少 3 条）

每条带 file:line 和审查重点：

- **重点 1**：[file:line] [审查者要关注什么]
- **重点 2**：[file:line] [关注点]
- **重点 3**：[file:line] [关注点]

---

## 7. 给下一轮的提示（至少 2 条）

下一轮任务 #N+1 的执行者需要知道的上下文：

- **上下文 1**：本任务在 [file:line] 暴露了 `XXX` 接口，下一轮直接 import 使用
- **上下文 2**：本任务的 [设计决策] 假设 [前提]，下一轮如果需要打破假设需重构
- **上下文 3**（如有）：留了 TODO 在 [file:line]，下一轮可清理

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|----|------|------|
| A1 全项目 pytest | ✅/❌ | [输出摘要] |
| A2 静态检查 | ✅/❌ | [ruff/mypy 输出] |
| A3 铁律+敏感词 grep | ✅/❌ | [各 grep 结果] |
| A4 spec §4 文件 | ✅/❌ | [对照清单] |
| A5 依赖安全 | ✅/❌ | [outdated/新增列表] |
| A6 commit message | ✅/❌ | [git log] |
| A7 Handoff 完整性 | ✅/❌ | [§0-§8 核对] |
| A8 CI 复现 | ✅/❌ | [CI Run URL] |

### Part B 软指标

**B1 错误处理**：
- 所有 except 块位置：
  - app/services/llm.py:95   except (...) -> raise LLMServiceError from exc
- 无 except: pass / except Exception: pass

**B2 偏差**：见 §3

**B3 安全**：
- 敏感数据 grep：[结果]
- 日志泄露检查：grep -rE "logger\..*api_key" backend/ → [无命中]

**B4 性能**：
- 外部 IO 调用位置：
  - app/services/llm.py:90   httpx.Client (rerank)

**B5 可测性**：
- 公共函数→测试映射：
  - get_llm() → test_get_llm_returns_configured_client

**B6 配置合规**：
- os.getenv grep（仅 core/config.py）：[结果]
- 硬编码 URL grep：[结果]

**B7 并发**：
- async 函数列表：[列出]
- sync 阻塞调用：[应无]

**B8 下一轮暗坑**：
1. [file:line] [描述]
2. [file:line] [描述]

### Part C 陷阱核查（18 项）

- C1 ✅ grep print 无命中
- C2 ✅ grep import logging 无命中
- C3 ✅ 无硬编码
- C4 ✅ 无 type: ignore 不带注释
- C5 ✅ 无 except: pass
- C6 ✅ 使用 raise X from e
- C7 ✅ 资源用 with 管理
- C8 ✅ 工厂函数无 @lru_cache
- C9 ✅ 所有 endpoint async def
- C10 ✅ 无 sync 阻塞
- C11 ✅ 配置走 settings
- C12 ✅ .env.example 同步
- C13 ✅ config.yaml 同步
- C14 ✅ 新依赖已说明
- C15 ✅ 无 mock 假阳性
- C16 ✅ 公共函数有测试
- C17 ✅ 无循环依赖
- C18 ✅ API 改动调用方同步

**ANTIPATTERNS.md 对照**：
- 已检查反模式总数：[N]
- 命中数：0（或列出命中+修复）

### Part D 人工触发

- D1-D3 代码量：X 行 → 通过 / Soft / Hard
- D4 修改已有文件数：X → 通过
- D5 新增依赖：[列表或无]
- D6 核心抽象改动：是/否
- D7 公共 API 删改：是/否
- D8 Part A 失败：是/否
- D9 Part C 失败：是/否
- D10 覆盖率下降：X% → 通过
- D11 偏差数：X → 通过

### Part E 自我反思

**E1 三个改进点**：
1. [当前 file:line] [改进方向] [没改原因]
2. ...
3. ...
**E2 忠告**：
- [给后来人的提醒]
**E3 新发现反模式**（如有）：
- [反模式描述]
- 已追加到 ANTIPATTERNS.md [ID]

### 修复轨迹（如有）

- fix_attempt:1 (commit abc1234) - 修复 X → 重审 Part A2 ✅
- fix_attempt:2 (commit def5678) - 修复 Y → 重审 C9 ✅

### 总评

✅ **PASS**（可合并）
或 ⚠️ **NEEDS_REVIEW**（需关注但可合并）
或 🔴 **NEEDS_HUMAN**（必须人工 review）

**last_verified_commit**: `<HEAD commit hash>`
```

---

## Handoff 编写原则

1. **§0 TL;DR 是给审查者的入口**——必须 30 秒能读完
2. **§4 必须填真实数据**——禁止编造，禁止"应该通过"
3. **§8 必须跟代码同步**——`last_verified_commit` 与 HEAD 一致才有效
4. **§6/§7 不能空**——至少 3 条 / 2 条，否则视为未完成
5. **修复后必须重写 §4/§8**——不要追加，要刷新

---

## 与配套文档的关系

- 自审查规程：[SELF_REVIEW.md](./SELF_REVIEW.md)
- 反模式知识库：[ANTIPATTERNS.md](./ANTIPATTERNS.md)
- 审查反馈格式：[REVIEW_FEEDBACK_TEMPLATE.md](./REVIEW_FEEDBACK_TEMPLATE.md)
- 标准任务 prompt：[TASK_PROMPT_TEMPLATE.md](./TASK_PROMPT_TEMPLATE.md)

---

_v2.1 | 最后更新：2026-06-03_
