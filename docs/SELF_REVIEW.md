# Codex 自审查规程 v2.1

> **适用范围**：本仓库所有由 Codex / Claude Code 执行的代码任务
> **何时执行**：每个任务在创建 PR 之后、合并请求之前
> **结果产出**：写入对应 `docs/handoffs/W?-D?-N-handoff.md` 的 §8 章节
> **失败处理**：任意 ❌ 必须修复或在 Handoff §3 偏差中明确说明，否则禁止合并
> **版本演进**：本文档随 `ANTIPATTERNS.md` 同步更新，每发现一类新反模式都要回填

---

## 总览

```
┌──────────────────────────────────────────────────────────┐
│  Part A：硬指标（机器判定，必须 100% 通过）              │
│  Part B：软指标（开放问答+证据，必须贴 file:line）       │
│  Part C：陷阱 checklist（18 项 yes/no）                  │
│  Part D：人工介入硬触发（任一命中必须停下）              │
│  Part E：自我反思（强制 3 条改进点）                     │
└──────────────────────────────────────────────────────────┘
            ↓
       全 ✅ 才能合并 PR
            ↓
       任何 ❌ → 修复 → 重审（最多 3 轮）
            ↓
       3 轮未通过 → 升级人工
```

---

## Part A：硬指标（必须 100% 通过）

### A1. 全项目回归测试

```bash
cd backend
uv run pytest -v
uv run pytest --cov=app --cov-report=term-missing
```

判定：
- [ ] pytest 全绿（含 skip 必须有理由）
- [ ] 覆盖率 ≥ 70%（核心 services/agents/workflows ≥ 85%）
- [ ] 覆盖率比 main 不下降超过 2%（用 `git show main:backend/coverage.xml` 对比，无则跳过此项）

### A2. 静态检查

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

判定：
- [ ] ruff check 0 errors
- [ ] ruff format 无变更
- [ ] mypy strict 0 errors

### A3. 七条铁律 grep（含敏感词扩展）

```bash
# 命中即违规（必须无输出）
grep -r "import dashscope" backend/app/
grep -rE "print\(" backend/app/
grep -rE "import logging$" backend/app/

# 仅允许在 backend/app/services/llm.py 出现
grep -rE "from openai|import openai" backend/app/ | grep -v "services/llm.py"

# 仅允许在 config/.env 相关位置
grep -rE "https://dashscope|qwen[0-9]|gte-rerank|text-embedding" backend/app/

# 敏感数据扫描
grep -rE "\b[0-9]{15,18}\b" backend/ docs/                # 身份证/银行卡
grep -rE "\b1[3-9][0-9]{9}\b" backend/ docs/              # 手机号
grep -rE "[¥$][0-9]{6,}|[0-9]{6,}元" backend/ docs/       # 真实金额
grep -rE "sk-[A-Za-z0-9]{20,}" backend/ docs/             # API Key
```

判定：
- [ ] 所有 grep 命令无输出或仅在允许文件中

### A4. Spec §4 文件清单

判定：
- [ ] Spec 中要求的所有文件都存在
- [ ] 没有 spec 之外的多余文件（除 lock / handoff）
- [ ] 文件路径、命名严格匹配 spec

### A5. 依赖安全扫描

```bash
cd backend
uv pip list --outdated      # 列出过期依赖
uv pip check                # 检查兼容性
```

新增依赖时必须：
- [ ] 在 Handoff §5 说明新增依赖及理由
- [ ] 贴 License：`uv pip show <pkg> | grep License`
- [ ] License 是 MIT/Apache/BSD/ISC 之一（否则需人工审查）

### A6. Commit message 规范

```bash
git log origin/main..HEAD --format=%s
```

判定每条 commit：
- [ ] 格式：`<type>: <subject>`（type ∈ feat/fix/refactor/test/docs/chore）
- [ ] body 含 `Refs: #N`（N = 任务 ID）
- [ ] subject 不超过 72 字符

### A7. Handoff 完整性

判定 `docs/handoffs/W?-D?-N-handoff.md`：
- [ ] §0 TL;DR 存在且非空
- [ ] §1-§8 全部章节存在
- [ ] §3 偏差章节有内容（"无" 也算）
- [ ] §6 给审查者提示 ≥ 3 条
- [ ] §7 给下一轮提示 ≥ 2 条
- [ ] §8 自审查报告含 Part A/B/C/D/E 全部结果
- [ ] §8 末尾包含 `last_verified_commit: <hash>` 且与当前 HEAD 一致

### A8. CI 复现

判定：
- [ ] `.github/workflows/self-review.yml` 在 PR 上跑通（绿色 ✅）
- [ ] CI 跑的 Part A 1-7 结果与本地一致

---

## Part B：软指标（强制证据化）

> **铁律**：每个回答必须包含 **代码位置（file:line）+ 代码片段**，不能只写文字结论。

### B1. 错误处理策略

回答（至少 3 句 + 列出所有 except 块）：
- 外部调用（LLM/API/DB/文件）失败时，错误是抛出还是吞掉？
- 列出所有 `except` 块的位置和处理方式：
  ```
  app/services/llm.py:95   except (httpx.HTTPError, ...) -> raise LLMServiceError
  app/api/health.py:N      ...
  ```
- 是否有任何 `except: pass` 或 `except Exception: pass`？必须无。

### B2. 与 Spec 的偏差

每个偏差必须：
- 列出 **偏离什么**（具体引用 spec §X.X）
- **为什么偏离**
- **对应的 commit hash**
- **对验收和后续的影响**

无偏差则明确写"无"。

### B3. 安全风险

回答 + grep 证据：
- 是否有日志/响应/错误信息会泄露 API Key、密码、客户敏感数据？
  - 跑：`grep -rE "logger\..*api_key|print.*api_key" backend/`
  - 结果应无命中
- 是否有 SQL/命令/路径注入风险？
- 是否有未关闭的文件/连接/HTTP client？

### B4. 性能与副作用

列出所有外部 IO 调用位置：
```
app/services/llm.py:90    httpx.Client (rerank API)
app/services/llm.py:55    OpenAILike network call
...
```

回答：
- 有无不必要的重复 IO？
- 工厂函数是否做了不当的单例缓存（如 `@lru_cache` on LLM client）？
- 有无 N+1 查询？

### B5. 可测性

每个公共函数对应测试位置：
```
app/services/llm.py::get_llm       → tests/services/test_llm.py:test_get_llm_returns_configured_client
app/services/llm.py::BailianRerank → tests/services/test_llm.py:test_reranker_*（5 个）
```

回答：
- 公共函数都有对应测试吗？列出未覆盖的（应为空）
- 失败路径（异常分支）测试覆盖了吗？
- 测试是否依赖外部服务的真实状态？（如真依赖，必须有 skip 装饰或 mock）

### B6. 配置合规

```bash
grep -rE "os\.getenv|os\.environ" backend/app/          # 应只在 core/config.py
grep -rE "\"http://|\"https://" backend/app/            # 应无硬编码 URL
```

回答：
- 所有 URL/端口/模型名/路径是否从 `settings` 读？
- 新增的业务参数是否进入 `config.yaml`？
- 新增的环境变量是否同步到 `.env.example`？

### B7. 并发与线程安全

```bash
grep -rE "async def" backend/app/                       # 列出所有 async 函数
grep -rE "time\.sleep|requests\.(get|post)" backend/    # 阻塞调用应无
```

回答：
- 是否有共享可变状态（class attribute / module global）？
- 异步函数中是否有 sync 阻塞操作？
- 是否正确使用 `async with` / `async for`？

### B8. 给下一轮的暗坑提示

至少 2 条，每条带具体代码位置：
- 上下文 1：本任务在 `XXX:line` 留了 TODO/FIXME，下一轮需关注
- 上下文 2：本任务的 `YYY` 函数有隐藏假设（"调用方必须先调 init"），下一轮调用要小心

---

## Part C：陷阱 Checklist（18 项 yes/no，全部 yes 才合格）

### 代码质量
- [ ] **C1**：没有 `print()` 调试残留（`grep "print(" backend/app/` 无命中）
- [ ] **C2**：没有 stdlib `import logging`（全用 loguru）
- [ ] **C3**：没有硬编码 URL/端口/模型名/秘钥
- [ ] **C4**：没有 `# type: ignore` 不带注释说明
- [ ] **C5**：没有 `except: pass` 或 `except Exception: pass` 静默吞错

### 异常与资源
- [ ] **C6**：异常链使用 `raise X from e` 保留 stacktrace
- [ ] **C7**：所有文件/连接/HTTP client 用 `with` / `async with` 管理
- [ ] **C8**：没有给会产生副作用的工厂函数加 `@lru_cache`（如 LLM client）

### 异步与并发
- [ ] **C9**：所有 API endpoint 是 `async def`
- [ ] **C10**：async 函数中没有 sync 阻塞调用（`time.sleep` / `requests.get` 等）

### 配置与依赖
- [ ] **C11**：配置全部走 `settings` 单例，没有散落的 `os.getenv()`
- [ ] **C12**：新增环境变量已加入 `.env.example`
- [ ] **C13**：新增业务参数已加入 `config.yaml`
- [ ] **C14**：新增第三方依赖已在 PR 描述和 Handoff §5 中说明

### 测试
- [ ] **C15**：测试没用 mock 假装通过应该真实调用的逻辑
- [ ] **C16**：所有公共函数都有对应测试

### 结构与文档
- [ ] **C17**：无循环依赖（`uv run python -c "import app.main"` 通过）
- [ ] **C18**：公共 API 改动有调用方同步更新（向后兼容或同 PR 改调用方）

### 引用反模式知识库

**执行 Part C 时必须打开 [`docs/ANTIPATTERNS.md`](./ANTIPATTERNS.md) 对照检查。**
该文档积累了历次审查中发现的具体反模式（如"httpx.Client 重复创建"），每条都有错误/正确范例。
Codex 必须逐条对照本任务代码，发现命中的反模式必须修复或在 §3 偏差中说明。

---

## Part D：人工介入硬触发（任一命中必须停下）

### 代码量分级
- [ ] **D1**：新增代码 ≤ 600 行 → ✅ 通过
- [ ] **D2**：新增代码 600-1000 行 → ⚠️ Soft：Handoff §3 必须说明"为什么这么大、能否拆分"
- [ ] **D3**：新增代码 > 1000 行 → 🔴 Hard 阻断，必须人工 review，禁止自动合并

行数计算（排除自动生成）：
```bash
git diff origin/main..HEAD --numstat | \
  grep -vE "(lock$|^docs/handoffs/|^docs/tasks/|^docs/reviews/)" | \
  awk '{sum += $1} END {print sum}'
```

### 影响范围
- [ ] **D4**：修改 > 5 个 main 上已有文件 → 人工 review
- [ ] **D5**：新增第三方 Python/JS 依赖 → 人工 review（除非 license 是 MIT/Apache/BSD/ISC）
- [ ] **D6**：改动了核心抽象层（`backend/app/core/*` 或 `backend/app/services/llm.py`）→ 人工 review
- [ ] **D7**：删除/重命名任何公共 API（函数/类/endpoint）→ 人工 review

### 质量退化
- [ ] **D8**：Part A 任意 ❌ → 修复或人工 review
- [ ] **D9**：Part C 任意 no → 修复或人工 review
- [ ] **D10**：测试覆盖率比上次 commit 下降 > 2% → 人工 review
- [ ] **D11**：Handoff §3 列出的偏差超过 3 条 → 人工 review

### 修复状态机

```
self_review:PASS              → 等待审查者 approve → merge
self_review:FAIL (Part A/C)   → fix_attempt:N (N ≤ 3)
fix_attempt:3 still FAIL      → 升级人工
self_review:NEEDS_HUMAN       → 直接升级（不允许 Codex 单方面 approve）
```

每次 fix attempt 必须在 Handoff §8 追加 entry：
```
- fix_attempt:1 (commit abc1234) - 修复 mypy 错误 X → 重审 Part A2 ✅
- fix_attempt:2 (commit def5678) - 补 test case Y → 重审 A1 覆盖率 ✅
```

3 次还不过，Handoff §8 末尾写：
```
总评：NEEDS_HUMAN_REVIEW
原因：自审查 3 轮未能全部通过 Part A/C
当前阻塞项：[列表]
```

---

## Part E：自我反思（强制 3 条改进点）

> **作用**：防止 Codex 给"完美自评"。强制思考"哪里可以更好"。

回答以下问题，每条至少 2 句：

### E1. 如果重做，会改进的 3 个地方

每条必须包含：
- 当前实现：`file:line`
- 改进方向：具体怎么改
- 没改的原因：时间/范围/优先级

例：
```
1. 当前 BailianRerank 每次请求新建 httpx.Client（llm.py:90），
   重做时会复用 client 节省 TCP 握手。
   本次没改是因为 spec 没要求且对当前并发量影响 < 10ms。

2. ...

3. ...
```

### E2. 给下一个写类似功能的人的忠告（至少 1 条）

例：
```
- 写 LlamaIndex 自定义 NodePostprocessor 时，注意 _postprocess_nodes 是 sync 接口，
  不要用 async httpx，会触发 SyncAsyncError。我踩了这个坑（fix_attempt:1）。
```

### E3. 本次发现的潜在反模式（至少 0 条，发现就要写）

如果在实现/审查中发现某种"看起来 OK 但其实不好"的模式，写出来：
- 反模式描述
- 错误范例
- 正确范例

**发现反模式必须同步追加到 [`docs/ANTIPATTERNS.md`](./ANTIPATTERNS.md)**，让下一轮 Codex 能自动规避。

---

## 自审查报告产出（写入 Handoff §8）

```markdown
## 8. 自审查报告（CODEX_SELF_REVIEW v2.1）

### Part A 硬指标
| 项 | 结果 | 证据 |
|----|------|------|
| A1 全项目 pytest | ✅/❌ | X passed, Y skipped, coverage Z% |
| A2 静态检查 | ✅/❌ | ruff/mypy 输出 |
| A3 七条铁律 + 敏感词 grep | ✅/❌ | 各 grep exit code |
| A4 spec §4 文件 | ✅/❌ | 文件清单核对 |
| A5 依赖安全扫描 | ✅/❌ | outdated 列表 + 新增 license |
| A6 commit message | ✅/❌ | git log 输出 |
| A7 Handoff 完整性 | ✅/❌ | §0-§8 核对 |
| A8 CI 复现 | ✅/❌ | CI run URL |

### Part B 软指标
**B1 错误处理**：[3 句+except 列表]
**B2 偏差**：[列表或"无"]
**B3 安全**：[3 句+grep 证据]
**B4 性能**：[列表+IO 位置]
**B5 可测性**：[函数→测试映射]
**B6 配置合规**：[grep 输出+回答]
**B7 并发**：[async 列表+回答]
**B8 下一轮暗坑**：[≥2 条带 file:line]

### Part C 陷阱核查（18 项）
- C1 ✅ 证据：grep print 无命中
- C2 ✅ 证据：...
- ...
- C18 ✅ 证据：...

ANTIPATTERNS 对照结果：
- 已检查反模式总数：N
- 命中数：0（或列出命中项+修复方式）

### Part D 人工触发
- D1-D3 代码量：X 行 → 通过/Soft/Hard
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
1. ...
2. ...
3. ...
**E2 忠告**：...
**E3 新发现反模式**：[列表或无]

### 修复轨迹（如有）
- fix_attempt:1 (commit hash) - ...
- ...

### 总评
✅ PASS（可合并）
⚠️ NEEDS_REVIEW（需审查者关注但可合并）
🔴 NEEDS_HUMAN（必须人工 review）

last_verified_commit: <HEAD commit hash>
```

---

## 何时升级到审查者

任一以下情况，Codex 必须停下，把 Handoff §8 链接发给审查者：

1. Part A 任意 ❌（修了 3 次还不过）
2. Part C 任意 no（修了仍不过）
3. Part D 任一硬触发（D3/D4/D5/D6/D7）
4. 总评不是 "PASS"
5. 不确定如何处理时（宁可上报，不要瞎决策）

升级时格式：
```
@审查者
PR #N 自审查未通过 / 需关注
阻塞项：[具体列表]
Handoff: docs/handoffs/W?-D?-N-handoff.md §8
PR: <URL>
请按 docs/REVIEW_FEEDBACK_TEMPLATE.md 反馈。
```

---

## 规程演进

本文档随项目持续演进。每次发现新问题或新反模式：

1. 反模式 → 追加到 `docs/ANTIPATTERNS.md`
2. 通用规则缺失 → 修改本文档（提 PR 走 review 流程）
3. CI 检查项 → 更新 `.github/workflows/self-review.yml`

**每个 Phase 结束时回顾本文档**，看哪些规则失效或新增。

---

_v2.1 | 最后更新：2026-06-03 | 维护者：项目负责人_
（Part C/D/E 在下一条消息）
