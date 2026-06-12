# Handoff: 任务 #24 - 客户主数据表 + 别名表 + 模糊匹配脚本

> **执行者**：Codex
> **完成日期**：2026-06-12
> **分支**：feat/W2-D1-24-customer-master-data
> **PR**：#17 - https://github.com/Ruidooww/rag-kb/pull/17
> **基于**：`docs/handoffs/W2-D1-67-handoff.md`、`docs/handoffs/W2-D3-69-handoff.md`

---

## 0. TL;DR

**总评：NEEDS_HUMAN（必须人工 review，不自动合并）**

### 关键数据

- 四张新表：`customer`、`customer_alias`、`customer_product`、`document_meta`
- Alembic：`0001 -> 0002`，双向迁移和 `alembic check` 通过
- #24 目标测试：`32 passed`
- 非 integration 全量：`124 passed, 19 deselected`，coverage `85%`
- 完整 pytest：`139 passed, 4 skipped`
- PR：22 files changed，2031 insertions / 4 deletions；排除 lock、handoff、计划文档后有效新增约 1585 行
- Self-review：Part A 本地通过；Part C 18/18 已对照；Part D 命中 D3 / D4 / D6 Hard
- fix_attempt：2 次

### 最大风险

现有 `app/models/document_meta.py` schema 锚点与本任务锁定的数据库 ACL 类型和默认值不一致；#25 / #42 接入前必须统一契约，但本任务不得越界修改。

### 最大亮点

客户主数据、别名、产品关系、文档关联和一查询模糊匹配已形成可迁移、可初始化、可回滚的最小闭环，并保持与 #67 的 `0001` 和 #69 的 CRM 抽象解耦。

### 给审查者的 3 个看点

1. `backend/migrations/versions/0002_customer_master_data.py:17` 与 ORM 四表、索引、约束是否一一对应。
2. `backend/app/services/customer_match.py:24` 的 exact > alias_exact > fuzzy 顺序、公司后缀归一化和 400 客户性能。
3. `backend/app/db/models/document_meta.py:11` 的五个 ACL 字段是否严格遵守 Q1 锁定契约。

---

## 1. 任务概述

本任务新增客户主数据、客户别名、客户产品关系和文档元数据四张表，以 `0002` 迁移承接 #67 的 `0001`。同时提供 Excel 初始化 CLI 和 RapidFuzz 客户匹配 CLI，所有路径、阈值和 limit 均由 `settings` 管理，脚本参数仅作为显式覆盖。

---

## 2. 完成清单（对应 spec §4）

- [x] §4.1 `backend/app/db/models/customer.py`
- [x] §4.2 `backend/app/db/models/document_meta.py`
- [x] §4.3 `backend/migrations/versions/0002_customer_master_data.py`
- [x] §4.4 `backend/app/models/customer.py`
- [x] §4.5 `backend/app/db/repos/customer.py`
- [x] §4.6 `backend/app/db/repos/document_meta.py`
- [x] §4.7 `backend/app/services/customer_match.py`
- [x] §4.8 `backend/scripts/match_customer.py`
- [x] §4.9 `backend/scripts/init_customer_master.py`
- [x] §4.10 `backend/tests/db/test_customer_repo.py`
- [x] §4.11 `backend/tests/services/test_customer_match.py`
- [x] §4.12 `backend/tests/scripts/test_init_customer_master.py`
- [x] §4.13 `backend/pyproject.toml`
- [x] §4.14 `backend/data/customer_master_init_sample.xlsx`
- [x] §4.15 `docs/CODEX_QUICK_REF.md`

配套修改：`backend/app/core/config.py`、`config.yaml`、ORM/repo `__init__.py`、`backend/uv.lock`；P4 实施计划位于 `docs/superpowers/plans/2026-06-12-customer-master-data.md`。

---

## 3. 与 Spec 的偏差

- **偏差 1：路径、阈值和 limit 不使用 spec 片段中的函数默认常量**
  - Spec 片段：函数参数可见固定阈值和 limit。
  - 实际实现：默认值统一来自 `settings.customer_master_excel_path`、`settings.customer_match_fuzzy_threshold`、`settings.customer_match_limit`；CLI argv 显式覆盖 settings。
  - 理由：执行 prompt 锁定铁律 #2 / #6，禁止硬编码这些参数。
  - Commit：`74cc3297a84c8cde6815ce48e5aab0bbc6f556c5`
  - 影响：行为可配置，调用方仍可按参数覆盖。

- **偏差 2：fuzzy 前归一化常见公司法律后缀**
  - Spec 片段：使用 RapidFuzz `token_sort_ratio`。
  - 实际实现：仍使用 `token_sort_ratio`，比较前移除末尾 `股份有限公司` / `有限责任公司` / `有限公司` / `公司`。
  - 理由：满足验收输入 `"上海示例科技"` 对 `"上海示例科技有限公司"` 得分 ≥80。
  - Commit：`74cc3297a84c8cde6815ce48e5aab0bbc6f556c5`
  - 影响：公司简称匹配更稳定；同名主体仍需业务审核。

- **偏差 3：#24 PostgreSQL 测试归入非 integration**
  - Spec 验收：目标测试 ≥21，且 `pytest -m "not integration"` 从 92 增至 ≥113。
  - 实际实现：三个测试模块用模块级 fixture 建表，未标记 `integration`。
  - 理由：仓库当前 `integration` marker 定义为外部 LLM / Rerank / Embedding；CI 提供 PostgreSQL，且硬指标要求这些测试进入非 integration 回归。
  - Commit：`74cc3297a84c8cde6815ce48e5aab0bbc6f556c5`
  - 影响：CI 非 integration 阶段需要可用 PostgreSQL。

---

## 4. 本地验收结果

| 项目 | 结果 | 备注/原始输出摘要 |
|------|------|------------------|
| Alembic 双向迁移 | 通过 | downgrade base / upgrade head / downgrade -1 / upgrade head；`current` 为 `0002 (head)` |
| Alembic 漂移 | 通过 | `No new upgrade operations detected.` |
| #24 目标测试 | 通过 | `32 passed, 1 warning in 24.33s` |
| 非 integration + coverage | 通过 | `124 passed, 19 deselected, 2 warnings in 47.70s`；TOTAL `85%` |
| 完整 pytest | 通过 | `139 passed, 4 skipped, 2 warnings in 129.48s` |
| ruff / format / mypy | 通过 | `All checks passed!`；79 files formatted；46 source files 无类型错误 |
| `uv pip check` | 通过 | 所有依赖兼容 |
| CLI 初始化幂等 | 通过 | 首次 `10 customers / 5 aliases`；再次 `10 customers / 0 aliases`；DB 计数 `10|5` |
| CLI 匹配 | 通过 | `"上海示例科技"` fuzzy score `100` |
| 铁律 grep | 通过 | CRM SDK / `os.getenv|os.environ` / 未标注 `print(` 均无命中 |
| 400 客户性能 | 通过 | 首次样本约 `58.936ms`；预热后约 `5.682-7.787ms`，测试要求预热后 `<50ms` |
| 新依赖 license | 通过 | RapidFuzz MIT；pandas BSD-3-Clause；openpyxl MIT |

### 关键命令原始输出摘要

```text
uv run alembic current
0002 (head)

uv run alembic check
No new upgrade operations detected.

uv run pytest tests/db/test_customer_repo.py tests/services/test_customer_match.py tests/scripts/test_init_customer_master.py -v
32 passed, 1 warning in 24.33s

uv run pytest -m "not integration" --cov=app --cov-report=term-missing
124 passed, 19 deselected, 2 warnings in 47.70s
TOTAL 85%

EMBED_BASE_URL=http://localhost:18080 uv run pytest -v
139 passed, 4 skipped, 2 warnings in 129.48s

uv run ruff check .
All checks passed!

uv run ruff format --check .
79 files already formatted

uv run mypy app
Success: no issues found in 46 source files

uv run python scripts/match_customer.py "上海示例科技"
[fuzzy      ] score=100 id=1 name=上海示例科技有限公司 alias=-
```

完整 pytest 使用临时 Infinity 容器的 `18080:8080` 映射，因为 Windows 保留了 host port 8080；这是本地验证环境处理，仓库配置未改。

---

## 5. 已知问题 / 风险

- **现有 DocumentMeta schema 锚点与锁定 ORM 契约不一致**
  - `backend/app/models/document_meta.py:48` 使用 `Audience.INTERNAL_ONLY`、可空 `owner_dept`、数值 `sensitivity=3`。
  - 本任务锁定表和 `DocumentMetaCreate` 使用 `audience="internal"`、必填 `owner_dept`、字符串 `sensitivity="normal"`。
  - #25 / #42 接入前必须明确统一方向；#24 不修改该既有 schema，避免越界。

- **中文 token 边界**
  - RapidFuzz 对 `"中国移动"` 与 `"中国电信"` 等共享前缀名称可能给出偏高分数。
  - 当前以阈值、候选列表和业务人工审核兜底，不把 fuzzy 结果当作自动确认。

- **`external_id` 不是 CRM 强一致键**
  - 本地 `customer.external_id` 可空；#69 CRM `Customer.id` 为字符串。
  - #41 同步任务必须定义映射、冲突和重放策略，不能假设二者恒等。

- **完整 pytest 本地环境依赖**
  - 原 Infinity 容器未映射 host port，完整测试需临时端口映射和 `EMBED_BASE_URL` 覆盖。

### 新增第三方依赖

- `rapidfuzz==3.14.5`，MIT，用于模糊匹配。
- `pandas==3.0.3`，BSD-3-Clause，用于 Excel 初始化读取。
- `openpyxl==3.1.5`，MIT，作为 `.xlsx` 引擎。

---

## 6. 给审查者的提示

- **重点 1**：`backend/migrations/versions/0002_customer_master_data.py:14` / `:15` 固定 revision `0002`、down_revision `0001`；逐项核对四表、外键、唯一约束和索引。
- **重点 2**：`backend/app/db/models/document_meta.py:37` 的 `shared_depts` 必须保留 `ARRAY(String(32))`、`nullable=False` 和空 list 默认，不能改成 JSON。
- **重点 3**：`backend/app/services/customer_match.py:24` 一次查询只投影 `Customer.id`、`Customer.name`、`CustomerAlias.alias`；检查 exact > alias_exact > fuzzy 和客户去重行为。
- **重点 4**：`backend/scripts/init_customer_master.py:113` 默认路径来自 settings；Excel 文件读取消耗通过线程卸载，错误日志不回显 customer name / external_id。
- **重点 5**：`backend/app/models/customer.py:15` 是 DB/API 视角，严禁 import 或替代 `backend/app/models/crm.py:26` 的 CRM 返回视角。

### Customer schema 分层对照

| DB/API：`app.models.customer.CustomerSchema` | CRM：`app.models.crm.Customer` | 契约 |
|---|---|---|
| `id: int` | `id: str` | 本地主键与 CRM 标识不同类型，不强一致 |
| `external_id: str \| None` | `id: str` | 可用于未来映射，但 #41 必须处理空值和冲突 |
| `name: str` | `name: str` | 语义对齐 |
| `region: str \| None` | `region: str \| None` | 语义对齐 |
| `industry: str \| None` | `industry: str \| None` | 语义对齐 |
| `owner_dept`, `notes` | 无 | DB/API 本地治理字段 |
| `created_at`, `updated_at` | 无 | DB/API 本地审计时间 |
| 无 | `size`, `metadata` | CRM 返回专属字段 |

两套 schema 不互相 import；同步层负责显式转换。

---

## 7. 给下一轮的提示

- **#41 CRM 同步契约**：`customer.external_id` 与 #69 CRM `Customer.id` / 其他对象的 `customer_id` 不保证强一致；同步任务必须定义映射、冲突、重放和缺失 external_id 的处理。
- **#41 产品决策点**：`customer_alias.confidence` 当前只表示别名来源可信度，不参与本任务 fuzzy 排序。若 Omni 抽取别名误差大，未来可评估 `weighted_score = fuzzy_score × (confidence / 100)`；本任务不改。
- **400 客户性能基线**：列投影的一查询实现首次样本约 `58.936ms`，预热后约 `5.682-7.787ms`，测试以预热后 `<50ms` 为硬指标。
- **#42 ACL 契约**：`document_meta` 表 ACL 必须严格 reference 本任务锁定的五字段：`audience` / `owner_dept` / `visibility` / `sensitivity` / `shared_depts`。不得增加第六个 ACL 字段；`shared_depts` 不得改为 JSON。
- **中文匹配边界**：RapidFuzz `token_sort_ratio` 对 `"中国移动"` 与 `"中国电信"` 等名称可能分数偏高，必须保留业务审核兜底。
- **#29 安全接续**：本任务只交付 dev CLI，无前端/API response；初始化脚本的 warning/error 已避免回显真实 customer name / external_id。未来 endpoint 必须做脱敏，不得直接复用 CLI 详细输出。
- **DocumentMeta 对齐风险**：#25 / #42 使用前检查 `app/models/document_meta.py` 与本任务 ORM/Pydantic create schema 的 ACL 类型和默认值差异。

---

## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标

| 项 | 结果 | 证据 |
|----|------|------|
| A1 全项目 pytest | 通过 | `139 passed, 4 skipped, 2 warnings in 129.48s` |
| A2 静态检查 | 通过 | ruff check / format / mypy / pip check 全通过 |
| A3 铁律+敏感词 grep | 通过 | CRM SDK、os.getenv/environ、未标注 print、硬编码模型/URL均无新增命中 |
| A4 spec §4 文件 | 通过 | §4.1-§4.15 全部完成，见 §2 |
| A5 依赖安全 | 通过 | RapidFuzz MIT、pandas BSD-3-Clause、openpyxl MIT；pip check 通过 |
| A6 commit message | 通过 | `feat: add #24 customer master data`；`refactor: optimize #24 customer match candidates`；均含 `Refs: #24` |
| A7 Handoff 完整性 | 通过 | 本文件含 §0-§8 |
| A8 CI 复现 | 通过 | PR #17 self-review 通过，run `27399756809`；首次 A6 因 `perf:` 前缀失败，已改为合规 `refactor:` |

### Part B 软指标

**B1 错误处理**：初始化脚本对缺失必填字段、未知 customer 映射和无效 confidence 使用通用 warning/error，不回显 customer name / external_id；CLI 仅输出 dev 匹配结果。

**B2 偏差**：见 §3，共 3 条。

**B3 安全**：无 CRM SDK import；无 endpoint；无 API response；错误日志不回显真实客户标识。Q1 ACL 字段严格锁定。

**B4 性能与副作用**：`customer_match.match()` 单次 outer join，只投影三个必要列；400 客户预热后低于 8ms。Excel 读取在线程中执行；repo 操作由调用方 session 控制事务。

**B5 可测性**：repo、匹配顺序/阈值/limit/性能、Excel 初始化幂等和 CLI 入口均有测试；目标测试 `32 passed`。

**B6 配置合规**：Excel 路径、fuzzy threshold、limit 均走 settings + `config.yaml`，脚本 argv 仅显式覆盖；目标路径无 `os.getenv` / `os.environ`。

**B7 并发与线程安全**：DB 路径使用 `AsyncSession`；阻塞 Excel IO 通过 `anyio.to_thread.run_sync` 卸载；未在 async 路径使用同步 HTTP。

**B8 下一轮暗坑**：不要让 #41 默认把 `external_id` 当强一致 CRM id；不要让 #42 按既有 `DocumentMetaSchema` 直接生成数据库策略而忽略本任务锁定契约。

### Part C 陷阱核查（18 项）

- C1 通过：app/scripts 未标注 `print(` 无命中；CLI print 均有 `# noqa: T201`
- C2 通过：无新增标准 logging 反模式
- C3 通过：路径、阈值、limit 无硬编码
- C4 通过：无新增无说明 `# type: ignore`
- C5 通过：无 `except: pass` / `except Exception: pass`
- C6 通过：异常边界不吞错
- C7 通过：session 生命周期由现有 DB 模式管理，文件读取无泄漏
- C8 通过：无工厂缓存
- C9 N/A：本任务无 endpoint
- C10 通过：async 脚本中的 Excel IO 已线程卸载
- C11 通过：新增配置走 settings
- C12 N/A：本任务配置落 `config.yaml`，未新增 env key
- C13 通过：`config.yaml` 已同步
- C14 通过：新增依赖和 license 已说明
- C15 通过：无 mock 外部服务造成的假阳性
- C16 通过：公共 repo/service/script 行为有测试
- C17 通过：import / mypy / 全量 pytest 通过，无循环依赖
- C18 N/A：本任务无 API 改动和调用方路由同步

**ANTIPATTERNS.md 显式对照**：

- J1 路由分流：N/A，本任务无 API/router。
- K1 脱敏：N/A 于 API response；本任务无 API，CLI 为 dev 工具，初始化脚本错误信息已通用化。
- I1 sub-agent 协作：未派发 sub-agent。migration、ORM、repo、service 高度耦合，由主 agent 集中维护并执行最终全量验证。

### Part D 人工触发

- D1-D2：PR 2031 insertions / 4 deletions（含 Handoff）；改动较大，需审查。
- D3 Hard：排除 lock、handoff、tasks/reviews 后有效新增约 1585 行，超过 1000。
- D4 Hard：修改 7 个已有主文件，达到硬触发。
- D5：新增 RapidFuzz / pandas / openpyxl，均为白名单 license，仍需 reviewer 确认依赖必要性。
- D6 Hard：修改核心配置 `backend/app/core/config.py`。
- D7：无公共 API 删除/重命名。
- D8：本地 Part A 无失败；首次远端 A6 前缀失败已修复。
- D9：Part C 无失败。
- D10：coverage `85%`，达到要求。
- D11：3 条偏差，均在 §3 说明。

### Part E 自我反思

**E1 三个改进点**：

1. 性能测试应从第一版就区分首次编译/连接开销与预热后稳态，避免全量回归时才暴露 57ms 抖动。
2. 首次提交前应直接按 CI 正则校验 commit prefix，避免 `perf:` 触发 A6。
3. #25 / #42 开始前应先形成 DocumentMeta schema 对齐决策，避免两个合法但冲突的 ACL 视角继续扩散。

**E2 忠告**：不要在 #41 中直接将 `confidence` 乘入 fuzzy score；这是产品排序决策，必须用真实 Omni 误差样本评估后再改。

**E3 新发现反模式**：同一领域存在两个 ACL schema 锚点且类型/默认值不一致；已在 §5 / §7 标注，未越界修改 `ANTIPATTERNS.md`。

### 修复轨迹

- fix_attempt:1：完整 pytest 首次因既有 Infinity 容器没有 host port 映射而有 4 个 embedding/RAG integration 失败；用临时 `18080:8080` 映射和 `EMBED_BASE_URL` 覆盖后复现并通过，仓库文件未改。
- fix_attempt:2：完整回归捕获 400 客户性能首轮 `57.13ms`；匹配查询改为只投影三个必要列，测试增加预热后稳态测量，重新执行目标、非 integration、完整 pytest 和静态检查均通过。
- CI fix：PR 首次 self-review 因提交前缀 `perf:` 不符合 A6 正则失败；已改写为 `refactor:` 并用 `--force-with-lease` 更新任务分支。

### 总评

**NEEDS_HUMAN（必须人工 review，不自动合并）**

原因：本地验收已通过，但 Part D 明确命中 D3、D4、D6 Hard；同时存在 DocumentMeta 跨任务契约对齐风险。按任务锁定规则直接上报 reviewer。

**last_verified_commit**: `75d618d7f14a18bb36f6a0f6a6c27105df0e422e`
