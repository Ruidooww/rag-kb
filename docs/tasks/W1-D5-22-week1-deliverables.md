# Task #22: Week 1 交付物整理

> **Phase**: 1 | **Week**: 1 | **Day**: 5
> **预估工时**: 2-3 小时
> **优先级**: 🟢 收尾（Week 1 收官）
> **前置任务**: #15-#20（#21 延后但不阻塞 #22）
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

Week 1 已完成 7 个核心任务（#15-#20 + #57 + #58），从零开始建立了：
- FastAPI 后端骨架 + 配置/日志/异常体系
- LlamaIndex 模型抽象层（铁律 #1 核心）
- 最小 RAG Pipeline（端到端跑通：5 docs → 6 chunks → query 出答案）
- v2.1 自审查机制 + QUICK_REF 优化（节省 ~18K tokens/任务）

本任务**不写新代码**，做两件事：
1. **整理 W1-summary.md**：给业务方看的成果汇总报告
2. **写 W1-demo-script.md**：5 分钟 Demo 演示脚本，给销售/售后看效果

同时为 Week 2（数据治理 + 700 文档入库）做就绪度评估和前置准备。

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| Week 1 主线任务全部合并 | `gh pr list --state merged --limit 10` | 看到 #1-#6 共 6 个 PR merged |
| main 上 RAG Pipeline 可用 | `ls backend/app/services/rag_pipeline.py` | 存在 |
| 5 份测试文档已入库 | `curl http://localhost:6333/collections/rag_chunks` | count >= 5 |
| v2.1 机制 6 文件齐全 | `ls docs/SELF_REVIEW.md docs/CODEX_QUICK_REF.md` | 存在 |
| ANTIPATTERNS 已有 6 条 | `grep -c "^### " docs/ANTIPATTERNS.md` | >= 6 |
| Handoff 文件齐全 | `ls docs/handoffs/W1-D*-handoff.md` | 至少 3 个（#18 #20 #58）|

---

## 3. 任务目标

### 3.1 业务方层面
让销售/售后/产品总监看到 W1 实际产出：
- 哪些任务完成了
- 真实数据（覆盖率、入库 chunks、CI 通过率等）
- 现在能做什么、还不能做什么
- 何时进入下一阶段

### 3.2 技术层面
为 Week 2（关键周——数据治理 + 700 文档入库）打好基础：
- 评估是否就绪
- 列出 Week 2 启动前的硬性前置（如真实 API Key、700 份文档收齐等）
- 给 Week 2 第一个任务 #23 留好上下文

### 3.3 治理层面
盘点 Week 1 暴露的债务（#21 延后 / #59 / #60 backlog）+ 反模式积累。

---

## 4. 输出文件清单

### 4.1 `docs/W1-summary.md`（核心，~250 行）

Week 1 完整总结，按以下 7 章节组织：

#### §1 完成清单
列出 7 个任务 + 6 个 PR 链接 + merge commit hash：
- #15 项目初始化
- #16 Docker 服务（4 个：qdrant/postgres/minio/infinity）
- #17 .env + config.yaml
- #18 FastAPI 骨架（PR #2）
- #19 LlamaIndex 抽象层（PR #3）
- #20 最小 RAG Pipeline（PR #5）
- #57 v2.1 自审查机制（PR #4）
- #58 QUICK_REF 优化（PR #6）
- #21 Ollama 切换演示（**延后，Phase 1 末必补**）

#### §2 关键技术决策
表格列出 6-8 个核心决策 + 理由：
- 混合云架构（数据本地 + LLM 云端）
- LLM 选 Omni-Flash（多模态一站式）
- Embedding 选 bge-m3（本地，迁移友好）
- Rerank 选 gte-rerank-v2（云端，质量优先）
- Python 3.14（用户偏好）
- v2.1 自审查机制（减少人工审查负担）
- QUICK_REF 替代完整规程（节省 18K tokens/任务）

#### §3 实际验收数据
表格列出：
- 6 个 PR 总代码量
- 全项目测试覆盖率（74% from #20 handoff）
- pytest 通过率（20 passed / 4 skipped）
- CI pass 率（最近 6 个 PR：6/6 = 100%）
- ANTIPATTERNS 积累条数（6 条）
- 5 docs 入库后 chunks 数（6）

#### §4 暴露的反模式
列出 ANTIPATTERNS.md 中 6 条积累的反模式 ID + 标题 + 严重度。

#### §5 已知遗留与债务
- **#21 延后**：Ollama 切换演示（卡在装机），Spec 已就绪
- **#59 backlog**：test_health 测试污染 + main.py CORS 硬编码
- **#60 backlog**：CI A7 检查对 chore PR 太严
- **占位 API Key**：LLM_API_KEY 仍是 placeholder，集成测试 skip 中

#### §6 Week 2 启动就绪度评估
对每项打分（✅ / ⚠️ / ❌）：
- 代码底座：✅ FastAPI + Qdrant + 5 服务全 healthy
- 数据治理 SOP：✅ 已写（docs/RAG知识库_数据治理SOP.docx）
- 客户主数据初始化：⚠️ 尚未导入真实客户清单
- 700 份文档：❌ 未收集
- 业务方审核团队：❌ 尚未对齐
- Omni API Key：❌ 仍是占位

#### §7 给 Week 2 的前置准备清单
列出 Week 2 启动前必须落实的事：
1. 业务方确认 700 份文档的真实位置（产品/销售/售后各自整理）
2. 找出 5-10 份样本，让 Codex 试跑元数据抽取
3. 销售总监导出客户清单（哪怕 Excel 也行），作为客户主数据初始版
4. 拿到真实 LLM_API_KEY（百炼新用户免费额度足够 Week 2 验证）
5. 决定文件命名规范是否强制（W2 Day1 要做的事）

### 4.2 `docs/W1-demo-script.md`（~80 行）

5 分钟 Demo 演示脚本，给业务方看的"现场表演稿"：

```markdown
# RAG 知识库 - Week 1 Demo 脚本

## 演示时长：5 分钟
## 演示对象：销售总监 / 售后经理 / 产品负责人

---

## 准备（开始前 30 秒）

- [ ] backend 服务在跑：`uv run uvicorn app.main:app --reload`
- [ ] 5 份测试文档已入库（如未入：`uv run python scripts/ingest_test_docs.py`）
- [ ] curl 或 Postman 准备好

---

## Step 1（30 秒）：架构介绍

"我们搭好了 RAG 知识库的最小可用版本，架构是混合云：
- 文档、向量数据库全部在公司内网
- 只有 LLM 推理调用阿里云百炼
- 切换到完全本地化只需改一行配置"

## Step 2（90 秒）：入库演示

[show backend/tests/fixtures/sample_docs/ 下 5 个 .md 文件]

"这是 5 份测试文档，覆盖产品手册、FAQ、客户案例、团队手册、发布说明。"

[run] uv run python scripts/ingest_test_docs.py

"看，全部自动切片、向量化、写入 Qdrant。这就是未来 700 份文档入库的流程，只不过批量执行。"

[show] curl http://localhost:6333/collections/rag_chunks

"6 个 chunks 已经躺在向量库里。"

## Step 3（120 秒）：问答演示

[run]
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "产品 X 怎么安装？"}'

"答案有 4 个特征：
1. 来自真实文档（看 sources 数组）
2. 带相关性分数
3. 引用了具体的文档名
4. 整个流程 X 秒以内"

[多问 1-2 个真实业务问题，如：
- '团队的代码 review 流程是什么？'
- '客户 ACME 的合作背景？']

## Step 4（60 秒）：技术承诺

"我们的设计保证了 3 件事：
1. **零厂商绑定**：只改 .env 就能切换 LLM（铁律 #7）
2. **数据不出网**：所有文档和向量在公司内
3. **代码可演进**：每个任务都有审查 + 反模式积累

下周开始进入数据治理 + 真实 700 份文档入库。"

## Step 5（30 秒）：Q&A 锚点

业务方可能问的问题准备好答案：

| 问 | 答 |
|----|----|
| 答案不对怎么办？ | Week 3 调优 + 知识缺口反馈机制（W4-D1）|
| 多久能用？ | Phase 1 末（4 周后）30 人开放测试 |
| 客户文档敏感怎么办？ | Phase 2 客户级权限（W6 实施）|
| 费用？ | 30 人中度使用约 ¥260-350/月 |
```

### 4.3 `docs/handoffs/W1-D5-22-handoff.md`（按 HANDOFF_TEMPLATE）

Week 1 收尾 Handoff，§7 给 Week 2 留**至少 5 条**详细上下文：
1. RAG Pipeline 入口位置
2. 测试文档位置（5 份 markdown）
3. 客户主数据表 schema（PG）即将在 W2-D1 #24 建立
4. 数据治理 SOP 已在 docs/RAG知识库_数据治理SOP.docx
5. 反模式知识库 6 条，新任务自审必查
6. 占位 API Key 状态（仍是 placeholder）

### 4.4 其他

- 本任务**不修改**任何 `.py` 代码
- 本任务**不修改** CLAUDE.md / SELF_REVIEW.md 等核心规程
- 仅产 3 个 Markdown 文档

---

## 5. 数据收集 SOP（写文档前必跑）

Codex 在写 W1-summary.md 前，必须从真实数据源采集以下指标，**禁止编造**：

### 5.1 PR 列表

```bash
gh pr list --state merged --limit 10 --json number,title,mergedAt,mergeCommit
```

### 5.2 测试覆盖率（从最新 #20 handoff 拿）

```bash
grep -A 2 "覆盖率" docs/handoffs/W1-D4-20-handoff.md | head -5
```

或重新跑：
```bash
cd backend && uv run pytest -v --cov=app --cov-report=term-missing
```

### 5.3 ANTIPATTERNS 条数

```bash
grep -c "^### [A-Z][0-9]" docs/ANTIPATTERNS.md
```

### 5.4 Qdrant 入库 chunks 数（如服务跑着）

```bash
curl -s http://localhost:6333/collections/rag_chunks | jq '.result.points_count'
```

如 Qdrant 没跑，可从 #20 Handoff §4 拿：**6 chunks**。

### 5.5 CI pass 率

```bash
gh run list --limit 10 --json conclusion --jq '[.[] | select(.conclusion=="success")] | length'
```

---

## 6. 验收标准（Definition of Done）

### 6.1 内容完整性
- [ ] W1-summary.md 7 个 §章节齐全，每章非空
- [ ] §1 完成清单 列出 8 个任务（含 #21 延后）+ 6 个 PR 链接
- [ ] §3 实际验收数据全部基于真实采集，非编造
- [ ] §5 已知遗留与债务列全 3 项（#21 #59 #60）
- [ ] §7 Week 2 前置清单至少 5 条
- [ ] W1-demo-script.md 5 个 Step 齐全，总时长合 5 分钟
- [ ] Demo 脚本中"业务方可能问的问题"至少 4 条

### 6.2 v2.1 自审查（精简版，本任务无代码改动）
- [ ] Part A 全 ✅（pytest / ruff / mypy 跟 #20 一致，因为没改代码）
- [ ] Part B 部分项目"不适用"标记（如 B1 错误处理无新代码，可空）
- [ ] Part C 18 项中代码相关多数"不适用"，文档相关必查
- [ ] Part D 应无任何硬触发（仅文档变更）
- [ ] Part E 自反思 3 条改进点必填

### 6.3 Handoff 完整
- [ ] §0-§8 章节齐全
- [ ] §0 TL;DR 总评 PASS
- [ ] §7 给 Week 2 提示 ≥ 5 条详细上下文
- [ ] §8 last_verified_commit 与 HEAD 一致

### 6.4 Git
- [ ] 分支 `feat/W1-D5-22-week1-deliverables`
- [ ] commit message 含 `Refs: #22`
- [ ] PR 标题含 `#22`

### 6.5 业务可读性
- [ ] W1-summary.md 通顺，业务方能看懂
- [ ] 没有未解释的技术术语（如必须用，需括号补充说明）
- [ ] Demo script 不含太多 jargon

---

## 7. 禁止事项

- ❌ 不要修改任何 `.py` 文件（本任务零代码变更）
- ❌ 不要改 CLAUDE.md / SELF_REVIEW.md / ANTIPATTERNS.md / TASK_PROMPT_TEMPLATE.md
- ❌ 不要编造 PR 链接、commit hash、覆盖率数字（必须真实采集）
- ❌ 不要在 W1-summary.md 中泄露 .env 真实值或 API Key
- ❌ 不要让 Demo script 时长 > 5 分钟（业务方注意力有限）
- ❌ 不要写"未来 Phase X 一定会做 Y"的过度承诺（Week 2 还没开始）

---

## 8. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| 写成"周报体"过于流水账 | 业务方读不下去 | 用表格 + 关键数据 + 1-2 句结论 |
| Demo 脚本只贴命令不写讲解词 | 演示时不知道说什么 | 每个 Step 含"讲什么 + 跑什么"双轨 |
| §3 实际验收数据编造 | 失信于业务方 | 必须每个数字配命令源头 |
| §7 Week 2 前置清单太抽象 | 业务方不知道要做什么 | 每条要 actionable（谁/什么时候/产出什么）|
| Handoff §7 过短 | 下一轮（#23）丢上下文 | 至少 5 条详细 |
| 没标注 #21 延后状态 | 后续遗忘 | §5 必须明确写"#21 延后到 Phase 1 末" |

---

## 9. 参考资料

- `docs/CODEX_QUICK_REF.md`（必读）
- `docs/handoffs/W1-D3-18-handoff.md`（#18 上下文）
- `docs/handoffs/W1-D3-19-handoff.md`（#19 上下文）
- `docs/handoffs/W1-D4-20-handoff.md`（#20 上下文 + 验收数据）
- `docs/handoffs/W1-D4-58-handoff.md`（#58 setup handoff）
- `docs/RAG知识库_完整任务书_V2.0.docx`（业务背景）
- `docs/RAG知识库_数据治理SOP.docx`（Week 2 启动需要的 SOP）

---

## 10. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 QUICK_REF + 本 spec + 上一轮 handoffs | 20 分钟 |
| §5 数据采集（PR 列表 / 覆盖率 / chunks 数等）| 20 分钟 |
| 写 W1-summary.md（7 章节）| 60 分钟 |
| 写 W1-demo-script.md（5 Step + Q&A）| 30 分钟 |
| Self-Review Part A-E + Handoff | 30 分钟 |
| 提交 / PR | 10 分钟 |
| **合计** | **~2.5 小时** |

---

## 11. 与下一轮的衔接

完成本任务即 **Week 1 正式收官**。

下一轮 #23（W2-D1 制定文件命名规范与文档类型枚举）是 Week 2 的开局任务。

Handoff §7 应该写清楚（至少 5 条）：

1. **RAG Pipeline 入口**：`backend/app/services/rag_pipeline.py` 三个函数（ingest_file / retrieve / generate_answer）
2. **测试文档位置**：`backend/tests/fixtures/sample_docs/` 5 份 markdown
3. **客户主数据待建**：W2-D1 #24 会建 customer / customer_alias / customer_product / document_meta 四张 PG 表
4. **数据治理 SOP**：`docs/RAG知识库_数据治理SOP.docx` 已就绪
5. **反模式知识库**：6 条，#23 自审 Part C 必查
6. **占位 API Key**：仍 placeholder，集成测试 skip 中（Week 2 必须拿到真实 Key 或决定继续 skip）
7. **#21 延后**：Ollama 切换演示 spec 已在 `docs/tasks/W1-D5-21-ollama-switch-demo.md`，Phase 1 末必须补做

---

## 12. 写作风格指引（重点）

W1-summary.md 是给**业务方**看的，不是给开发看的。注意：

- **避免**：commit hash、文件路径、技术术语堆砌
- **使用**：数字 + 类比 + 业务价值描述
- **多用**：表格、bullet list、清晰小标题
- **少用**：长段文字描述

例如：

❌ 不推荐：
> "我们使用 LlamaIndex 0.10.x 的 OpenAILike 客户端实现了 LLM 抽象层，
> 通过 BaseSettings 加载配置，并在 rag_pipeline.py 中调用 retrieve 函数..."

✅ 推荐：
> "完成了 LLM 接入：
> - 切换模型只改 1 行配置（不动代码）
> - 已验证：5 份测试文档入库 + 答出第一个问题
> - 响应时间：< 5 秒（含 Embedding + 检索 + LLM 生成）"

---

_v1.0 | 任务 ID：#22 | 最后更新：2026-06-04_
