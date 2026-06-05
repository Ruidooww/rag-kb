# 标准任务 Prompt 模板 v1.1 

> 每个代码任务的 prompt 都按本模板组织。
> 模板中 `[占位]` 部分由 Claude 在生成具体任务 prompt 时填写。
> 适用范围：W1-D3-19 之后的所有任务（含 Phase 2-5）

---

## 模板说明

### 为什么需要标准模板
1. **降低 Codex 误判风险**：固定结构让 Codex 知道每步该做什么
2. **强制走完自审查**：每轮 prompt 都包含 Step 7 自审查，避免遗漏
3. **统一 Handoff 输出**：每轮产出格式一致，方便审查者快速上手
4. **支持长期演进**：模板变化追踪在 git 历史，可回溯

### 何时偏离模板
- 极少数特殊任务（如纯文档、紧急 hotfix）可省略部分 Step
- 偏离必须在 Handoff §3 说明

---

## 子 agent 协作规范（每个任务 prompt 都引用）

> 落地 CLAUDE.md 原则 P4。Codex 接到任务后按需调度 sub-agent；本段是默认纪律，违反任一项 → 偏差计入 Handoff §3。

- **范围**：严格按已有计划执行，**不扩大范围**。看到顺手能修的也先记到 Handoff §3 偏差，不要顺手做。
- **计划先行**：非简单修改（满足以下任一）必须先制定实施计划再改代码：
  - 涉及 > 1 个文件
  - 涉及核心抽象（services/ 抽象层 / Agent 工厂 / ABC）
  - 涉及任何铁律或原则相关层
- **三关边界检查**：
  - **实施前**：spec §3 任务目标 / §7 禁止事项 / CLAUDE.md 相关铁律已理解
  - **实施中**：每改完一个文件，对照 spec §4 输出清单 + 相关铁律自查
  - **合并前**：自审查 Part D 硬触发 / coverage / 路由分流 / 工具集隔离断言全过
- **并行派发条件**（必须同时满足才并行 sub-agent）：
  - ≥ 2 个互不依赖的子任务
  - 文件冲突风险低（不同目录 / 不同模块 / 不同 layer）
  - 每个 sub-agent 分工边界清晰（文件清单 + 修改范围 + 不可触碰清单）
- **禁止**：
  - 多个 sub-agent 同时改同一批文件（除非主 agent 显式协调切片）
  - sub-agent 自行扩大范围 / 自行决定派生新 sub-agent
  - sub-agent 跳过 spec §7 禁止事项检查
- **主 agent 职责**（Codex 自身扮演主，不可委托）：
  - 派发任务（含明确文件清单 + 边界描述）
  - 集成 sub-agent 产出
  - 冲突处理（同名变量 / import 顺序 / migration 编号 / 接口签名）
  - 一致性检查（命名 / 类型 / 错误类 / 日志风格）
  - 跑最终集成测试
- **测试纪律**：
  - sub-agent 自报完成不代表通过
  - 最终验证必须在**集成后的分支**上跑完 SELF_REVIEW Part A
  - 任何 sub-agent 单独跑过的测试在集成后必须重跑一遍

---

## 标准 Prompt 结构（10 步）

```text
# 任务 #N：[任务标题]

请按以下规格执行：

## 项目位置
C:\Users\Ruidoww\Desktop\RAG

## 必读文档（按顺序）
1. CLAUDE.md（项目级规则）
2. docs/CODEX_QUICK_REF.md（速查卡——七条铁律 / 10 步 / Part A-E / 反模式 / 命令）
3. docs/tasks/W?-D?-N-xxx.md（本任务详细 spec）
4. docs/handoffs/[上一轮 handoff].md（上一轮上下文）
5. [其他相关文件，如 settings、依赖文件]

需要细节时再按需打开：SELF_REVIEW.md / ANTIPATTERNS.md / HANDOFF_TEMPLATE.md / REVIEW_FEEDBACK_TEMPLATE.md

## 分支名（本轮强制使用）
feat/W?-D?-N-[kebab-case-描述]

## 执行原则
1. 严格遵守 CLAUDE.md 十条铁律 + 横切原则 P1-P4
2. 严格按 spec §4 输出文件清单
3. Step 7 自审查任一 ❌ 必须停下修复，最多 3 轮
4. Step 7 任一 Part D 硬触发 → 直接上报，不要自动合并
5. 遇到 spec 不清的地方，停下来问，不要自己猜
6. 推 PR 前必须本地全验收通过
7. Handoff §4 必须填真实数据，不能编造
8. 子 agent 调度遵循本模板「子 agent 协作规范」段（落地原则 P4）

## 完整工作流（10 步，必须按顺序）

### Step 1：同步 main + 创建分支
git checkout main
git pull origin main
git checkout -b feat/W?-D?-N-xxx

### Step 2：阅读所有必读文档并复述任务

完成阅读后，用 5 句话以内复述任务大纲，包括：
1. 要创建/修改的核心文件有哪几个
2. 七条铁律中本任务覆盖了哪几条
3. 验收的硬指标是什么
4. 关键技术决策点（如有）
5. ANTIPATTERNS.md 中需要规避的相关模式

等用户确认无误后再进入 Step 3。

### Step 3：实现代码

按 spec §4 输出文件清单实现。
实现过程中遇到 spec 模糊的地方必须停下问用户。

### Step 4：本地验收（SELF_REVIEW Part A 第一轮）

按 docs/SELF_REVIEW.md Part A 全部 8 项执行：
cd backend
uv run pytest -v
uv run pytest --cov=app --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
uv run mypy app
（+ A3 grep / A5 依赖 / A6 commit / A7 handoff / A8 CI 后置）

任何失败必须修复后重跑，不能强推。

### Step 5：提交代码 + 推送

git add .
git commit -m "feat: [实现描述]

Refs: #N"
git push -u origin feat/W?-D?-N-xxx

### Step 6：创建 PR

gh pr create \
  --base main \
  --head feat/W?-D?-N-xxx \
  --title "feat: #N [任务标题]" \
  --body "$(cat <<'EOF'
## Summary

[1-2 段实现描述]

## 变更内容

详见 docs/handoffs/W?-D?-N-handoff.md（即将提交）

## 本地验收

详见 Handoff §4 和 §8 自审查报告。

Refs: #N
EOF
)"

记录 PR 编号和 URL，进入 Step 7。

### Step 7：执行完整 SELF_REVIEW（Part A/B/C/D/E）

按 docs/SELF_REVIEW.md 全部 5 个 Part 执行：
- Part A：重新跑一遍硬指标命令（保留输出供 Handoff 用）
- Part B：8 题软指标，每题贴 file:line 和代码片段
- Part C：18 项陷阱 checklist + 对照 ANTIPATTERNS.md
- Part D：人工介入硬触发检查
- Part E：3 条改进点 + 忠告 + 新反模式（如有）

如有任何 ❌：
- Part A/C 修复 → 重跑 Part A/C → fix_attempt:N（N ≤ 3）
- Part D 硬触发 → 直接上报用户，不要继续
- 3 次还不过 → 升级人工

### Step 8：写完整 Handoff

按 docs/HANDOFF_TEMPLATE.md 创建 docs/handoffs/W?-D?-N-handoff.md，包含 §0-§8：
- §0 TL;DR
- §1 任务概述
- §2 完成清单
- §3 偏差
- §4 验收结果（Step 4 真实输出）
- §5 风险（含新增依赖说明）
- §6 给审查者提示（至少 3 条）
- §7 给下一轮提示（至少 2 条）
- §8 自审查报告（Step 7 完整结果 + last_verified_commit）

PR 编号、URL、mergeable 状态全部填入实际值，无占位。

### Step 9：提交 Handoff + 推送（自动更新 PR）

git add docs/handoffs/W?-D?-N-handoff.md
git commit -m "docs: handoff for #N with self-review v2.1 report

Refs: #N"
git push origin feat/W?-D?-N-xxx

PR 会自动包含这个新提交，无需新建分支或新 PR。

### Step 10：返回结果给用户

按以下格式回报：
1. PR 编号 + URL
2. mergeable / mergeStateStatus（gh pr view --json）
3. SELF_REVIEW 总评：PASS / NEEDS_REVIEW / NEEDS_HUMAN
4. 关键数据：新增 X 行 / 覆盖率 Y% / 偏差 Z 条
5. Handoff 文件路径
6. 如有 fix_attempt 轨迹，列出
```

---

## 占位符替换指南（Claude 填写时）

| 占位 | 替换示例 |
|------|---------|
| `#N` | `#19` |
| `[任务标题]` | `LlamaIndex 抽象层封装` |
| `W?-D?-N-xxx` | `W1-D3-19-llamaindex-abstract` |
| `[上一轮 handoff]` | `W1-D3-18-handoff.md` |
| `[其他相关文件]` | `backend/app/core/config.py、.env.example` |
| `[1-2 段实现描述]` | 来自 spec §1 任务背景 |
| `[实现描述]` | git commit message subject |

---

## 模板演进

发现模板不足时：
1. 创建 issue 描述问题
2. 提 PR 改本模板
3. 同步更新已有 task spec（如果模板字段变了）

每 Phase 结束时检查模板有效性。

---

_v1.2 | 最后更新：2026-06-05_

变更（v1.2）：
- 新增「子 agent 协作规范」段（落地 CLAUDE.md 原则 P4）
- 执行原则第 1 条同步十条铁律 + 原则 P1-P4
- 执行原则追加第 8 条引用子 agent 协作规范
