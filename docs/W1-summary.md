# RAG 知识库 Week 1 交付总结

> 面向对象：销售总监、售后经理、产品负责人、项目负责人  
> 总结范围：Week 1，从项目初始化到最小 RAG Pipeline 跑通  
> 数据口径：以本地命令、GitHub PR、Handoff 和 Qdrant 实时查询为准  
> 当前状态：Week 1 主线完成；#21 Ollama 切换演示延后，不阻塞 Week 2 启动

---

## 1. 完成清单

Week 1 完成了从“项目空壳”到“可入库、可检索、可问答”的最小闭环。这里的“最小”不是演示 PPT，而是已经有后端服务、模型抽象、向量库、测试文档和 API 入口的可运行基础版本。

| 任务 | 结果 | 业务意义 | 证据 |
|------|------|----------|------|
| #15 项目初始化 | 已完成 | 建立项目目录、基础文档、环境模板和任务管理基础 | `c13ea72` / `1de4b4f` |
| #16 Docker 服务 | 已完成 | 本地基础设施可运行，包含 Qdrant、Postgres、MinIO、infinity | #20 Handoff 记录 4 个服务 healthy |
| #17 `.env` + `config.yaml` | 已完成 | 配置和业务参数分离，后续切换模型不改业务代码 | `.env.example` / `config.yaml` |
| #18 FastAPI 骨架 | 已合并 | 后端 API、配置、日志、异常、健康检查形成基础框架 | [PR #2](https://github.com/Ruidooww/rag-kb/pull/2), `15a2fe03cdc31eec8b44b863cf11e8999cefca92` |
| #19 LlamaIndex 抽象层 | 已合并 | LLM、Embedding、Rerank 接入统一入口，降低厂商绑定 | [PR #3](https://github.com/Ruidooww/rag-kb/pull/3), `a8d2cdf04a6e5560969337f06eb72adecc4bd574` |
| #20 最小 RAG Pipeline | 已合并 | 5 份测试文档入库，形成“文档 -> 检索 -> 答案”的闭环 | [PR #5](https://github.com/Ruidooww/rag-kb/pull/5), `a7934846b2bef41e69ed2648bd5d0b49820464e8` |
| #57 v2.1 自审查机制 | 已合并 | 建立 Codex 自审查、Handoff、反模式积累机制 | [PR #4](https://github.com/Ruidooww/rag-kb/pull/4), `ce613dc4f16454c3f7f6ccba8b402c591de3e80f` |
| #58 QUICK_REF + CI Python 3.14 | 已合并 | 降低后续任务阅读成本，并让 CI 与本地 Python 版本一致 | [PR #6](https://github.com/Ruidooww/rag-kb/pull/6), `d3c357bf736b3d166d8750d296927a95df02b5f7` |
| #21 Ollama 切换演示 | 延后 | 本地 LLM 切换验证，Phase 1 末补做即可 | spec 已在 `docs/tasks/W1-D5-21-ollama-switch-demo.md` |

另外，Week 1 共有 6 个 PR 合并到 `main`：

| PR | 标题 | 合并时间 | Merge commit |
|----|------|----------|--------------|
| [#1](https://github.com/Ruidooww/rag-kb/pull/1) | #18 spec + qdrant healthcheck | 2026-06-03 13:25 UTC | `a8da704d63208107273f19dc82c1f5752d8c1717` |
| [#2](https://github.com/Ruidooww/rag-kb/pull/2) | #18 FastAPI skeleton | 2026-06-03 13:53 UTC | `15a2fe03cdc31eec8b44b863cf11e8999cefca92` |
| [#3](https://github.com/Ruidooww/rag-kb/pull/3) | #19 LlamaIndex abstraction | 2026-06-03 14:30 UTC | `a8d2cdf04a6e5560969337f06eb72adecc4bd574` |
| [#4](https://github.com/Ruidooww/rag-kb/pull/4) | #57 self-review v2.1 | 2026-06-04 01:43 UTC | `ce613dc4f16454c3f7f6ccba8b402c591de3e80f` |
| [#5](https://github.com/Ruidooww/rag-kb/pull/5) | #20 minimal RAG pipeline | 2026-06-04 04:11 UTC | `a7934846b2bef41e69ed2648bd5d0b49820464e8` |
| [#6](https://github.com/Ruidooww/rag-kb/pull/6) | #58 QUICK_REF + Python 3.14 | 2026-06-04 07:29 UTC | `d3c357bf736b3d166d8750d296927a95df02b5f7` |

---

## 2. 关键技术决策

这些决策的目标是让系统先跑通，再逐步扩大到真实业务文档和权限治理。

| 决策 | 选择 | 原因 | 当前影响 |
|------|------|------|----------|
| 部署形态 | 本地数据层 + 云端 LLM | 公司文档、向量库、对象存储留在本地；生成模型可先用云端降低部署门槛 | 适合无本地 GPU 资源的现状 |
| LLM | `qwen3.5-omni-flash` 兼容 OpenAI 协议 | 多模态扩展空间大，接入方式统一 | 当前 API Key 仍是 placeholder，真实生成测试暂未跑通 |
| Embedding | 本地 `BAAI/bge-m3` + infinity | 中文效果好，向量维度 1024，文档向量不出本地 | 已用于 5 docs -> 6 chunks 入库 |
| Rerank | 百炼 `gte-rerank-v2` | 质量优先，用于检索结果二次排序 | 没有真实 Key 时会跳过或 fallback |
| 向量库 | Qdrant | 轻量、Docker 易启动、适合 MVP | 当前 `rag_chunks` collection 已有 6 个 points |
| 后端 | FastAPI + Python 3.14 | 适合 AI 服务和快速迭代 | CI 已在 #58 对齐 Python 3.14 |
| 配置机制 | `.env` + `config.yaml` | 环境变量放部署配置，业务参数单独调优 | 后续切换模型主要改配置，不改业务代码 |
| 治理机制 | v2.1 自审查 + QUICK_REF | 每个任务自带验收、反模式和 Handoff | 减少人工审查成本，保留复盘链路 |

---

## 3. 实际验收数据

以下数字都来自真实命令或已合并的 Handoff，不使用估算值。

| 指标 | 当前数据 | 来源 |
|------|----------|------|
| 已合并 PR 数 | 6 个 | `gh pr list --state merged --limit 10` |
| 6 个 PR 合计变更 | 新增 7,271 行，删除 21 行 | `git show --numstat` 汇总，含 docs/tests/lock |
| 后端测试覆盖率 | 74% | `docs/handoffs/W1-D4-20-handoff.md` |
| #20 非 integration 测试 | `13 passed, 11 deselected, 2 warnings` | #20 Handoff §4 |
| #20 全量本地测试 | `20 passed, 4 skipped, 2 warnings` | #20 Handoff §4 |
| 最终合并 PR CI | 6/6 最终绿色 | `gh run list` + merged PR 状态 |
| 最近 workflow 原始结果 | 4 success / 5 failure | 最近 9 次 `gh run list`；失败均在对应 PR 内修复后重跑 |
| 反模式知识库 | 6 条 | `grep -c "^### [A-Z][0-9]" docs/ANTIPATTERNS.md` |
| 测试文档数量 | 5 份 Markdown | `backend/tests/fixtures/sample_docs/` |
| 入库 chunks 数 | 6 个 | Qdrant `rag_chunks.points_count=6`, HTTP 200 |
| 向量维度 | 1024 | Qdrant collection config `vectors.size=1024` |
| Week 2 SOP | 已存在 | `docs/RAG知识库_数据治理SOP.docx` |

最重要的业务结论：

- 文档入库链路已经跑通：5 份测试文档被切成 6 个 chunks，并写入本地 Qdrant。
- 检索链路已经跑通：#20 验证过安装类问题能命中 `product_x_manual`，最高分 `0.55940914`。
- 生成链路有 API 结构和 prompt，但真实云端生成仍依赖正式 `LLM_API_KEY`。

---

## 4. 暴露的反模式

Week 1 没有只做“功能堆叠”，也把过程中暴露出的工程问题写进了 `docs/ANTIPATTERNS.md`。后续任务会在自审查时逐条对照。

| ID | 反模式 | 严重度 | Week 1 处理方式 |
|----|--------|--------|----------------|
| A1 | 业务代码直接依赖具体模型 SDK | 高 | #19 建立 `get_llm()` / `get_embedding()` / `get_reranker()` 抽象 |
| B1 | API Key、模型名、URL 硬编码 | 高 | 配置统一走 `.env` / `settings` |
| C1 | 静默吞掉外部调用异常 | 高 | 异常包装为项目异常，并保留异常链 |
| D1 | 测试污染全局 `app` router | 中 | 已发现 #18 遗留，进入 #59 backlog |
| E1 | 缓存有副作用的外部 client | 中 | #20 未引入 `@lru_cache` 缓存外部 client |
| F1 | spec 依赖列表和实现描述不一致 | 中 | #20 删除误列依赖，保留 Python 3.14 |

当前还不是“完美代码库”，但反模式已经有记录、有规避入口，后续修复不会丢上下文。

---

## 5. 已知遗留与债务

| 项 | 状态 | 影响 | 建议处理 |
|----|------|------|----------|
| #21 Ollama 切换演示 | 延后 | 本地 LLM 切换还未现场验证 | Phase 1 末补做，不阻塞 Week 2 数据治理 |
| #59 `test_health` 测试污染 | 待建 backlog | `backend/tests/api/test_health.py:20` 会向共享 `app.router` 注入测试路由 | 独立 app fixture 或局部路由测试 |
| #59 `main.py` CORS 硬编码 | 待建 backlog | `backend/app/main.py:31` 仍有 `"http://localhost:3000"` | 移到 `settings.cors_origins` |
| #60 CI A7 对 chore PR 过严 | 待建 backlog | #58 暴露基础设施 PR 也被要求 Handoff | 调整 workflow 豁免规则或明确要求 |
| placeholder API Key | 未解决 | 真实 LLM/rerank integration test 仍 skip | Week 2 前拿到正式 Key 或明确继续 skip |
| 真实 700 文档 | 未收集 | 无法进入批量入库和质量评估 | Week 2 Day 1 前业务方给出样本和目录 |

#21 延后说明：Ollama 切换演示是“模型切换能力”的验证，不是 Week 1 最小 RAG Pipeline 的前置条件。当前系统已经具备模型抽象层，后续只需要按 spec 补做切换演示。

---

## 6. Week 2 启动就绪度评估

| 项 | 就绪度 | 说明 |
|----|--------|------|
| 代码底座 | ✅ | FastAPI、配置、异常、模型抽象、RAG Pipeline 已在 `main` |
| 本地基础设施 | ✅ | Docker Compose 定义了 Qdrant、Postgres、MinIO、infinity |
| 向量入库链路 | ✅ | 5 docs -> 6 chunks 已实际写入 Qdrant |
| 查询 API | ✅ | `POST /api/v1/query` 已存在，可作为 Demo 和集成入口 |
| 数据治理 SOP | ✅ | `docs/RAG知识库_数据治理SOP.docx` 已存在 |
| 任务治理机制 | ✅ | SELF_REVIEW、ANTIPATTERNS、QUICK_REF、Handoff 模板就位 |
| 客户主数据 | ⚠️ | 还没有真实客户清单，需要销售侧提供 |
| 真实业务文档 | ❌ | 700 份文档尚未收集、分类、命名 |
| 真实 LLM Key | ⚠️ | `.env.example` 有字段，实际 `.env` 仍需填真实值 |
| 业务审查团队 | ⚠️ | 需要明确谁负责确认答案质量和知识缺口 |

结论：Week 2 可以启动，但第一天应先做数据治理和样本试跑，不建议直接全量导入 700 份文档。

---

## 7. 给 Week 2 的前置准备清单

1. 产品、销售、售后三方各指定 1 个接口人，负责确认文档范围和答案质量。
2. 业务方先提供 5-10 份真实样本文档，用来验证元数据抽取、切片质量和检索效果。
3. 销售侧导出客户主数据初版，即使只是 Excel，也要包含客户名、别名、产品线、负责人、状态。
4. 明确 700 份文档的来源目录、类型、负责人和更新时间，避免导入重复或过期资料。
5. Week 2 Day 1 先制定文档命名规范和文档类型枚举，再批量入库。
6. 拿到真实 `LLM_API_KEY`，或明确 Week 2 继续使用 skip 策略，只验证本地 embedding + retrieval。
7. 决定 #21 Ollama 切换演示的执行时间，建议放在真实 Key 验证后，避免同时排查两类变量。
8. 建立一个“答案是否可用”的业务评分表，至少覆盖准确性、引用来源、是否遗漏关键信息。
9. 将 #59 和 #60 建成 backlog，避免遗留问题在后续任务中反复出现。
10. Demo 前确认 Docker 服务、后端服务、Qdrant 数据和 `.env` 状态，避免现场演示被环境问题打断。

---

## 数据源记录

- PR 列表：`gh pr list --state merged --limit 10 --json number,title,mergedAt,mergeCommit,url`
- CI 列表：`gh run list --limit 10 --json conclusion,displayTitle,headBranch,createdAt,url`
- 反模式条数：`grep -c "^### [A-Z][0-9]" docs/ANTIPATTERNS.md`
- Qdrant 入库数：`curl.exe http://localhost:6333/collections/rag_chunks`
- 覆盖率和测试结果：`docs/handoffs/W1-D4-20-handoff.md`
- Week 2 SOP：`docs/RAG知识库_数据治理SOP.docx`
