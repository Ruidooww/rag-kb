# 审查反馈标准模板

> **作用**：审查者（Claude / 人工）给 Codex 的反馈必须按本模板组织，避免反馈丢失或误解。
> **使用方式**：审查者在 PR comment 或 `docs/reviews/PR-N.md` 写反馈；Codex 必须逐项回应。
> **替代方案**：本模板用于结构化反馈；简单审查（仅 LGTM）可直接 approve 不用模板。

---

## 标准反馈结构

```
# Review Feedback for PR #N

> **审查者**：[Claude / 用户姓名]
> **审查日期**：YYYY-MM-DD
> **审查依据**：spec [docs/tasks/W?-D?-N-xxx.md] + Handoff [docs/handoffs/W?-D?-N-handoff.md]
> **总评**：APPROVE / APPROVE_WITH_NITS / REQUEST_CHANGES

---

## 1. 必须修复（Blocker）

> 不修不能合并。Codex 必须逐条回应（参见"Codex 响应模板"）。

### B1. [一句话标题]
- **位置**：`file:line`
- **问题**：[2-3 句描述为什么不行]
- **期望修法**：[具体修改方案，最好带代码片段]
- **依据**：[引用 spec / 铁律 / 反模式 ID]

### B2. ...

（无 Blocker 写"无"）

---

## 2. 建议改进（Nice to have）

> 不修也能合并，但建议改。Codex 可选回应。

### N1. [标题]
- **位置**：`file:line`
- **当前**：[现状描述]
- **建议**：[改进方向]
- **理由**：[为什么这样更好]

### N2. ...

（无建议写"无"）

---

## 3. 提问（Codex 必须回答）

> Codex 不修代码也得回答，澄清设计意图。

### Q1. [问题]
[1-2 句描述]

### Q2. ...

（无问题写"无"）

---

## 4. 表扬（鼓励性反馈）

> 做得好的地方，让 Codex 知道哪些模式可以保留。

- 👍 [位置] [做得好的具体点]
- ...

---

## 5. 总评说明

[1-2 段，说明为什么给这个总评]

**下一步**：
- APPROVE → Codex 可直接合并
- APPROVE_WITH_NITS → Codex 可合并，建议项进 backlog
- REQUEST_CHANGES → Codex 按上述 Blocker 修复后重新提审
```

---

## Codex 响应模板

收到 Review Feedback 后，Codex 在 PR comment 或新 commit 中按以下格式响应：

```
# Response to Review Feedback

> **回应日期**：YYYY-MM-DD
> **修复 commit**：[hash 列表]
> **fix_attempt**：N (≤ 3)

## Blocker 响应（逐条）

### B1. [原标题]
- **状态**：✅ Fixed / ⚠️ Disagreed / ❓ Need clarification
- **修复方式**：[做了什么]
- **修复 commit**：[hash]
- **验证**：[如何确认修好了，测试输出/grep 等]

### B2. ...

## 建议改进响应（可选）

### N1. [原标题]
- **状态**：✅ Adopted / ⏸️ Deferred to backlog / ❌ Rejected
- **理由**：...

## 提问响应（必答）

### Q1. [原问题]
[答复]

### Q2. ...

## 自审查重跑结果

修复后必须重跑 SELF_REVIEW Part A/C，结果追加到 Handoff §8 修复轨迹：
- fix_attempt:N (commit XYZ) - 修复 B1 → Part A2 重跑 ✅

## 请求复审
@审查者 请重新 review。
```

---

## Disagreement 处理流程

如果 Codex 不同意某项 Blocker（**⚠️ Disagreed**），按以下流程：

```
1. Codex 在响应中说明不同意的理由（≥ 3 句）
   ↓
2. 审查者评估：
   - 接受 Codex 论点 → 撤销该 Blocker，改为 Nit 或表扬
   - 坚持 Blocker → 升级讨论（用户/团队介入）
   ↓
3. 任何时候 Codex 都不能单方面无视 Blocker
```

---

## 总评判定标准

### APPROVE
- 所有 Blocker = 无
- 自审查 Part A/C 全 ✅
- 实现完全符合 spec

### APPROVE_WITH_NITS
- 无 Blocker
- 有 < 5 条 Nice to have
- 不影响合并

### REQUEST_CHANGES
- ≥ 1 条 Blocker
- 或 Part A/C 有 ❌
- 或与 spec 重大偏差未说明

---

## 何时跳过模板（直接简短反馈）

以下场景可不写完整模板：
- 纯文档 PR（typo 修复等）
- 紧急 hotfix
- 单文件单行改动

直接在 PR comment 写：`LGTM ✅` 或一句话指出问题。

---

## 历史反馈归档

每个 PR 的 review 反馈建议存档到 `docs/reviews/PR-N.md`，方便后续查阅。
归档时机：PR 合并后。

```bash
mkdir -p docs/reviews
# 把 PR comment 复制成 docs/reviews/PR-N.md
git add docs/reviews/PR-N.md
git commit -m "docs: archive review feedback for PR #N"
```

---

_v1.0 | 最后更新：2026-06-03_
