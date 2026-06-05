# Codex 速查卡 v1.0

> **每个代码任务前只需读本卡 + 任务 spec + 上一轮 Handoff**。
> 需要细节时再打开"何时打开完整文档"中列出的源文档。
> 节省 ~18K tokens/任务（vs 读完整规程文档）。

---

## 🔒 十条迁移友好铁律（必查，违反即重做）

| # | 铁律 | ❌ 禁止 | ✅ 允许 |
|---|------|--------|--------|
| 1 | 模型调用走 app.services.llm | `import dashscope` / `from openai import OpenAI` | `from app.services.llm import get_llm` |
| 2 | 配置走环境变量 | `MODEL = "qwen3.5-omni-flash"` | `settings.llm_model` |
| 3 | OpenAI-Compatible 协议 | 用 dashscope 原生 SDK | OpenAILike / OpenAIEmbedding |
| 4 | Embedding 用 bge-m3（本地）| 换 text-embedding-v4 | bge-m3 维度 1024 |
| 5 | Prompt 放 prompts/ 目录 | inline > 3 行 | prompts/*.txt |
| 6 | 关键参数走 config.yaml | 硬编码 chunk_size=800 | settings.chunk_size |
| 7 | 保留 Ollama 兼容性 | 改业务代码切模型 | 只改 .env |
| 8 | Agent 编排走 LangGraph | LlamaIndex Workflows 写 Agent | `StateGraph` + 节点函数 |
| 9 | CRM 调用走 app.services.crm | `import xiaoshouyi` / `import hubspot` | `from app.services.crm import get_crm` |
| 10 | Agent 工具集物理隔离 | "一个 Agent 装所有工具靠 prompt 限制" | `tools = EXTERNAL_TOOLS if user.is_external else INTERNAL_TOOLS` |

**违反任一 = 重做**。详情：`CLAUDE.md §铁律` 或 `SELF_REVIEW.md Part A3`。

## 🧭 横切原则（每个任务都要遵守）

| # | 原则 | 关键点 |
|---|------|--------|
| P1 | API 响应脱敏 | 敏感字段经 `sanitize(payload, user)` 后返回，外部用户拿掩码版 |
| P2 | 工具集版本化 | `EXTERNAL_TOOLS` / `INTERNAL_TOOLS` 集中定义 + 断言测试防误改 |
| P3 | 内外路由树严格分流 | `internal_router` / `public_router` 物理拆分；admin / CRM 只挂 internal |
| P4 | Codex 子 agent 协作纪律 | 范围不扩 / 计划先行 / 三关边界 / 并行需互不依赖 / 主 agent 集成 |

详情：`CLAUDE.md §横切原则` / `TASK_PROMPT_TEMPLATE.md §子 agent 协作规范`。

---

## 🔍 CodeGraph 用法（优先于 grep）

| 场景 | 工具 |
|------|------|
| 找符号定义 | `codegraph_search "name"` |
| 理解架构/某区域 | `codegraph_explore "question or symbols"` |
| 谁调用了它 | `codegraph_callers "name"` |
| 它调用了谁 | `codegraph_callees "name"` |
| 改它会影响什么 | `codegraph_impact "name"` |
| 拿一个符号完整源码 | `codegraph_node "name" includeCode=true` |

**仍用 grep 的场景**：.env / docs/ 文本 / 铁律 Part A3 grep。

---

## 🧠 Agent 编排（LangGraph）

| 模式 | 用法 |
|------|------|
| 简单 pipeline（BaseQA）| `StateGraph` + 线性节点 |
| 条件分发（Router）| `add_conditional_edges` |
| 并发抽取（ServicePath）| `Send` API fan-out / fan-in |
| 工具调用（FreeQA）| `create_react_agent(llm, tools)` |
| 状态持久化 | `langgraph-checkpoint-sqlite` |

详情：[STACK_UPDATE_V2.2.md](./STACK_UPDATE_V2.2.md)

---

## 📋 任务执行 10 步（标准流程）

```
1. git checkout main && git pull → git checkout -b feat/W?-D?-N-xxx
2. 阅读 spec + 上一轮 Handoff → 5 句话复述 → 等用户 confirm
3. 实现代码
4. 本地验收（SELF_REVIEW Part A 第一轮）
5. git commit + push
6. gh pr create
7. 跑完整 SELF_REVIEW Part A-E
8. 写 Handoff §0-§8
9. git commit Handoff + push（自动更新 PR）
10. 返回结果给用户
```

任何一步遇阻 / Part D 硬触发 → 停下问用户，**绝不自动决策**。
详情：`TASK_PROMPT_TEMPLATE.md`。

---

## 🧑‍🤝‍🧑 子 agent 调度速查（落地原则 P4）

| 时机 | 动作 |
|------|------|
| 任务非简单修改（>1 文件 / 改抽象 / 改铁律层）| 先出实施计划再改 |
| ≥ 2 个互不依赖任务 + 文件冲突低 + 边界清晰 | 派 sub-agent 并行 |
| sub-agent 边界 | 明确文件清单 + 不重叠 + 不可触碰清单 |
| sub-agent 完成 | 主 agent 跑集成 + 一致性检查 |
| 最终验证 | 必须在集成后的分支上跑完 SELF_REVIEW Part A |

**禁止**：sub-agent 自行扩范围 / 多个 sub-agent 改同一批文件 / 跳过集成测试。
详情：`TASK_PROMPT_TEMPLATE.md` 的「子 agent 协作规范」段。

---

## ✅ Self-Review Part A-E（PR 创建后必跑）

| Part | 内容 | 失败处理 |
|------|------|---------|
| **A 硬指标** | 8 项：pytest / coverage / ruff / mypy / 铁律 grep / spec 文件 / 依赖 / commit / Handoff | 必须全 ✅，fix 后重跑（≤ 3 轮）|
| **B 软指标** | 8 题：每题贴 file:line + 代码片段（错误处理/偏差/安全/性能/可测/配置/并发/暗坑）| 不能纯文字答 |
| **C 陷阱** | 18 项 yes/no + ANTIPATTERNS.md 对照 | 任一 no → 修复或人工 |
| **D 人工触发** | 11 条（代码量 >1000 hard / 改核心 / 删 API / 新依赖 / 偏差>3 等）| 任一命中 → 停下问用户 |
| **E 自反思** | 3 条改进 + 1 条忠告 + 0+ 新反模式 | 强制写，防自满 |

详情：`SELF_REVIEW.md`。

---

## 📦 Handoff §0-§8（写入 docs/handoffs/W?-D?-N-handoff.md）

```
§0 TL;DR（30 秒速读）：总评 + 关键数据 + 风险 + 亮点 + 看点
§1 任务概述（2-3 句）
§2 完成清单（对应 spec §4）
§3 偏差（每条带 commit hash + 影响）
§4 验收结果（真实命令输出，不能编造）
§5 已知问题/风险 + 新增依赖说明
§6 给审查者的提示（≥ 3 条带 file:line）
§7 给下一轮的提示（≥ 2 条）
§8 自审报告 + last_verified_commit
```

**§0 TL;DR 是审查者入口**，必须 30 秒能读完。详情：`HANDOFF_TEMPLATE.md`。

---

## 🚫 ANTIPATTERNS 速查（每次对照，详情查 ANTIPATTERNS.md）

| ID | 标题 | 严重度 |
|----|------|--------|
| A1 | httpx.Client 循环新建 | 🟡 中 |
| B1 | raise X 不加 from e | 🟡 中 |
| C1 | os.getenv 散落各处 | 🔴 高 |
| D1 | 测试共享 app router | 🟡 中 |
| E1 | 工厂函数加 @lru_cache | 🔴 高 |
| F1 | spec 依赖列表与实现描述不一致 | 🟡 中 |
| H1 | S3 兼容存储 env var 误用（产品私有） | 🔴 高 |
| H2 | S3 兼容存储私有 health endpoint 跨产品复用 | 🟡 中 |

新发现的反模式必须在 Handoff §8 E3 追加到 ANTIPATTERNS.md。

---

## 💾 对象存储（RustFS）

| 操作 | 方法 |
|------|------|
| 保存文件 | `await get_storage().save(doc_id, bytes)` |
| 读文件 | `await get_storage().load(doc_id) -> bytes` |
| 预签名下载 URL | `await get_storage().get_presigned_download_url(doc_id, expires_in=3600)` |
| 删除 | `await get_storage().delete(doc_id)` |
| Web Console | http://localhost:9001/rustfs/console/access-keys (account/password from `.env.example` `STORAGE_*`) |

**业务代码禁止直接 import boto3** —— 走 `services/storage.py` 抽象。

---

## 🛠 常用命令

```bash
# 后端（在 backend/ 目录下）：
uv sync                                              # 装依赖
uv run pytest -v -m "not integration"                # 跑非 integration 测试
uv run pytest -v --cov=app                           # 跑全部 + 覆盖率
uv run ruff check . && uv run ruff format --check .  # 格式 / lint
uv run mypy app                                      # 类型检查
uv run uvicorn app.main:app --reload                 # 起服务
uv add <package>                                     # 加依赖

# Self-review 铁律 grep（在仓库根）：
grep -rE "import dashscope" backend/app/
grep -rE "print\(" backend/app/
grep -rE "^import logging$|^from logging import" backend/app/
grep -rE "from openai|^import openai" backend/app/ | grep -v "services/llm.py"
grep -rE "https://dashscope|qwen[0-9]|gte-rerank" backend/app/
```

---

## 🌿 Git 规范

```
分支命名：feat/W?-D?-N-xxx | fix/... | docs/... | chore/...
Commit：<type>: <subject>\n\nRefs: #N
Squash merge + 删 feature 分支
```

---

## 🆘 何时打开完整文档（fallback 指引）

| 情况 | 打开 |
|------|------|
| 不确定 Self-Review 某 Part 怎么填 | `docs/SELF_REVIEW.md` |
| 不确定某反模式细节 | `docs/ANTIPATTERNS.md` |
| 不确定 Handoff §N 怎么写 | `docs/HANDOFF_TEMPLATE.md` |
| 不确定 10 步某步具体做什么 | `docs/TASK_PROMPT_TEMPLATE.md` |
| 不确定铁律边界 | `CLAUDE.md` |
| 其他场景 | **本卡片够用** |

---

_v1.2 | 与 `SELF_REVIEW.md v2.1` / `ANTIPATTERNS.md v1.3` / `CLAUDE.md v1.2` 配套 | 最后更新：2026-06-05_

变更（v1.2）：
- 铁律 8 条同步到 10 条（+ #9 CRM 抽象 / #10 Agent 工具集物理隔离）
- 新增「横切原则」速查表（P1-P4）
- 新增「子 agent 调度速查」段（落地原则 P4）
