# Codex 派单 prompt — 任务 #25 v2

> **生成日期**：2026-06-12
> **用途**：lean MVP 路径 W2-D2 派单，#24 已 merge 后下一步
> **使用方法**：复制下方代码块整段（从 `# 任务 #25 v2` 到结尾）发给 Codex
> **配套阅读**：`docs/STATUS-2026-06-12.md`（项目全景）+ `CLAUDE.md`（自动加载）
> **派单 prompt 设计要点**：
> - 3 道防漂移锁（任务编号 + spec 路径 + 分支名硬锁，避免上次 Codex 跑错任务到 #68）
> - Task 0 优先级硬约束（必须先修 DocumentMetaSchema 契约再做抽取主体）
> - lean MVP 边界（不抽客户名 / 不入库 / 不并发 / 不接 CRM）

---

## 派单 prompt 全文（直接复制给 Codex）

```text
# 任务 #25 v2：产品 KB 元数据抽取 + Task 0 修 DocumentMetaSchema 契约（L2 重大）

请按以下规格执行。

## 🔒 任务锁定（避免上次走错任务）

- 本轮**只做** #25 v2，**禁止**任何 #26 #27 #28 #29 #30 #31 #32 #25b 范围工作
- 本轮 spec 唯一路径：`docs/tasks/W2-D2-25-product-kb-metadata-extract.md`
- 本轮分支名唯一：`feat/W2-D2-25-product-kb-extract`
- Step 1 创建分支前必须 assert 分支名跟以上完全一致；不一致直接停下问用户
- spec 顶部明确：**v2.0 lean MVP 重写**，跟 git history 里的 v1（已移到 phase2/W5-25b-customer-doc-extract.md）是不同任务，不要混淆

## 项目位置
C:\Users\Ruidoww\Desktop\RAG

## 必读文档（按顺序）
1. CLAUDE.md（v1.2，重点：铁律 #1 #2 #5 #6 + 原则 P4）
2. docs/CODEX_QUICK_REF.md（v1.2 速查卡）
3. docs/STATUS-2026-06-12.md（**必读 — lean MVP 路径全景**）
4. docs/tasks/W2-D2-25-product-kb-metadata-extract.md（本任务唯一 spec）
5. docs/handoffs/W2-D1-24-handoff.md（上一轮 #24 + 重点 §3 §6 §7 DocumentMetaSchema 差异警告）
6. docs/reviews/PR-15.md（N1 token 安全暗坑）
7. backend/app/models/document_meta.py（PR #13 Pydantic 锚定，**不许动**）
8. backend/app/db/models/document_meta.py（#24 新建 ORM，Task 0 修对齐）
9. backend/app/db/models/customer.py（#24 已落地，参考模式）
10. backend/migrations/versions/0002_customer_master_data.py（参考 alembic 写法）

## 分支名（本轮强制使用）
feat/W2-D2-25-product-kb-extract

## 🔴 Task 0 优先级硬约束

**实施顺序锁定**：必须先完成 Task 0（spec §2）再进 §3 主体。
- 不允许跳过 Task 0 直接写抽取逻辑
- Task 0 验收（alembic 0003 双向迁移 + ≥ 5 个契约测试）全过后才能开始 §3
- Task 0 失败 → 停下问用户，不要绕过

## 本轮关键边界

### 铁律 #1（LLM 抽象）
- ❌ 禁止 `import dashscope` / `from openai import OpenAI`
- ✅ 走 `from app.services.llm import get_llm`
- VLM 多模态调用也走 `get_llm()`（百炼 OpenAI 兼容支持 image_url）

### 铁律 #5（Prompt 进文件）
- ❌ 禁止 Python 字符串里写超过 3 行的 prompt
- ✅ `backend/prompts/extract_product_kb.txt`（jinja2，spec §4.1 已给）

### 铁律 #2 + #6（配置走 settings）
- `extract_confidence_threshold` / `prompts_dir` / `vision_dpi` / `vision_max_pages` 进 settings
- ❌ 硬编码任一阈值

### 原则 P4（子 agent 协作纪律）
- 本任务 ≥ 8 文件 + 改抽象层 + 含 alembic migration → 先出实施计划再改代码
- 不派 sub-agent（Task 0 + 主体高度耦合，主 agent 集中维护）

### PR #15 N1 暗坑（错误信息脱敏）
- `MetadataExtractError` raise 不许回显 doc_path 完整路径（防文件枚举）
- 详细信息走 logger.warning；raise message 用 "Failed to extract metadata"

### DocumentMetaSchema 锚点（PR #13 锁死）
- ❌ 禁止改 `app/models/document_meta.py`（这是 PR #13 锚点）
- ✅ Task 0 改的是 `app/db/models/document_meta.py` ORM 对齐到 Pydantic（不是反向）
- 5 字段差异表见 spec §2.1，**实施前对照表读一遍**

### lean MVP 范围（不要扩散）
- ❌ 不抽客户名（本批 199 份没有，customer_match 不调用）
- ❌ 不写入 PG / Qdrant（入库是 #28，本任务只抽取）
- ❌ 不并发批量（#26）
- ❌ 不接 #69 CRM / #67 IdP（本任务零依赖）

## 执行原则

1. 严格遵守 CLAUDE.md 十条铁律 + 横切原则 P1-P4
2. 严格按 spec §4.1-§4.7 文件清单
3. 本任务级别：**L2 重大** → Step 2 必须 5 句话复述 + 等用户 confirm
4. Step 7 任一 ❌ 必须停下修复（≤ 3 轮）
5. Step 7 任一 Part D 硬触发 → 直接上报，不要自动合并（除非用户明示授权）
6. 遇到 spec 模糊（特别是 doc_category → ACL 字段映射规则 / 视觉路径 PDF 文本提取退化 / pdf2image poppler 跨平台）必须停下问
7. 推 PR 前必须本地全验收通过；Handoff §4 真实输出不能编造

## 完整工作流（10 步）

按 TASK_PROMPT_TEMPLATE.md v1.2 Step 1-10 完整执行。重点：

- **Step 2 复述必须答**（5 句话以内）：
  1. 本任务 spec 路径 + Task 0 含义 + 主体抽取目标
  2. 覆盖了铁律 #1 #5 + 原则 P4 + 落地 PR #14 N1
  3. 与 #24 / PR #13 的契约关系（ORM 改、Pydantic 不动、alembic 0003 ALTER）
  4. 验收硬指标（Task 0 alembic 双向 + 5 契约测试 + 主体 ≥ 9 抽取测试 + 全量 ≥ 138 passed + coverage ≥ 80%）
  5. lean MVP 不扩范围声明（不抽客户名 / 不入库 / 不并发 / 不接 CRM）

- **Step 7 Part C18 项必须显式对照 ANTIPATTERN I1 / J1 / K1**：本任务无 API 故 J1 / K1 N/A 写明；I1 按"不派 sub-agent"答

- **Step 8 Handoff §7 必须含**：
  (a) Task 0 ALTER 在干净 PG（空表）跑 OK，但若未来有数据时迁移注意事项
  (b) 5 字段 ACL 映射规则（doc_category → audience/visibility/owner_dept）后续 #26 #28 必须遵守
  (c) IP-Guard 产品模块枚举可能不全（W2 抽样 5 份后调），enum 扩展时如何更新 prompt
  (d) 视觉路径 poppler 跨平台部署（Windows dev 装 conda-forge poppler；CI / docker 装 poppler-utils）

## 验收硬指标

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'

# Task 0
& uv run alembic upgrade head
& uv run alembic downgrade -1
& uv run alembic upgrade head
& uv run alembic current   # 必须输出 0003 (head)
& uv run pytest tests/db/test_document_meta_acl_contract.py -v   # ≥ 5 passed

# 主体
& uv run pytest tests/services/test_product_kb_extract.py -v     # ≥ 9 passed
& uv run pytest -m "not integration" --cov=app                   # ≥ 138 passed; coverage ≥ 80%
& uv run ruff check . ; & uv run ruff format --check . ; & uv run mypy app

# 铁律 grep（必须无命中）
grep -rE "import dashscope|from openai" backend/app/services/product_kb_extract.py
grep -rE "qwen|gte-rerank|https://dashscope" backend/app/services/product_kb_extract.py
grep -rE "os\.(getenv|environ)" backend/app/services/product_kb_extract.py backend/app/models/product_kb_metadata.py

# Pydantic 锚点未被修改
git diff main -- backend/app/models/document_meta.py   # 必须无输出
```

## 提交规范

- 单 squash commit subject：`feat: #25 product KB metadata extract + acl contract fix`
- Body 含：覆盖铁律（#1 + #5 + #2 + #6）+ Task 0 修复 5 字段差异 + 主体抽取 6 字段 + 验收数据 + 「为 #26 / #28 / #31 留稳定 ProductKBMetadata schema 路径」声明
- `Refs: #25`
- Co-Authored-By: Codex

按 Step 1 开始执行。Step 2 复述完等用户 confirm 才能进 Step 3。
```

---

## 派单后预期流程

1. Codex 收到 prompt → Step 1 创建分支 `feat/W2-D2-25-product-kb-extract`
2. Step 2 读完必读文档 → 给出 5 句话复述
3. **你转给 Claude（新会话或当前）→ Claude 核对**：
   - Task 0 优先级理解对不对
   - 5 字段差异（audience / owner_dept / sensitivity 三处红）有没有点到
   - lean MVP 边界（不抽客户名 / 不入库 / 不接 CRM）有没有强调
4. 没问题 → 你回 Codex「confirm，进 Step 3」
5. Codex 自跑 Step 3-9（实现 + 验收 + Handoff）
6. PR 上来 → Claude 写 review → 你 squash merge

## 故障 / 偏差处理

| 情况 | 处理 |
|------|------|
| Codex 复述漏了 Task 0 | 让它重新复述，强调 §2 是前置必做 |
| Codex 复述说要抽客户名 | 立刻打断，引用本派单 prompt §lean MVP 范围段 |
| Codex 想动 `app/models/document_meta.py` | 立刻打断，引用 §DocumentMetaSchema 锚点段 |
| Codex 用 `import dashscope` | 立刻打断，引用铁律 #1 |
| Codex 跳过 Task 0 直接写抽取 | 立刻打断，要求回到 §2 完成 Task 0 |
| Codex 自合并 PR | 检查 Part D 是否硬触发；触发了应该 NEEDS_HUMAN 不自合 |

---

_文件版本：v1.0 | 2026-06-12_
