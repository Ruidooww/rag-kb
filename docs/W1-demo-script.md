# RAG 知识库 - Week 1 Demo 脚本

## 演示时长

5 分钟

## 演示对象

销售总监 / 售后经理 / 产品负责人

## 演示目标

让业务方看到：Week 1 已经不是“概念方案”，而是有文档入库、向量检索、问答 API 和可复用工程机制的最小可用底座。

---

## 准备：开始前 30 秒

- [ ] Docker 服务在线：Qdrant、Postgres、MinIO、infinity。
- [ ] 后端服务在线：`cd backend && uv run uvicorn app.main:app --reload`
- [ ] 测试文档已入库：`cd backend && uv run python scripts/ingest_test_docs.py`
- [ ] 准备一个终端窗口展示 `curl`，一个窗口展示 `backend/tests/fixtures/sample_docs/`。
- [ ] 如果没有真实 `LLM_API_KEY`，提前说明本次重点展示入库和检索闭环，真实生成依赖正式 Key。

---

## Step 1：架构说明，30 秒

讲解词：

“Week 1 我们搭好了 RAG 知识库的最小可用底座。文档、向量库、对象存储和数据库都在公司本地；LLM 生成能力先接云端，后续可以按配置切换。”

“这套设计的重点不是一次性追求大而全，而是先保证三件事：数据尽量留在本地、模型供应商可以切换、每次改动都有审查和记录。”

展示：

```powershell
docker compose ps
```

预期说明：

“这里可以看到本地基础设施服务已经起来。真正的客户文档后续也会走这条链路。”

---

## Step 2：入库演示，60 秒

讲解词：

“现在先用 5 份测试文档模拟真实业务资料，包括产品手册、FAQ、客户案例、团队手册和发布说明。系统会自动读取文档、切片、生成向量，再写入 Qdrant。”

展示文件：

```powershell
Get-ChildItem backend\tests\fixtures\sample_docs
```

运行入库：

```powershell
cd backend
uv run python scripts/ingest_test_docs.py
```

讲解词：

“当前测试集最终生成 6 个 chunks。Week 2 的 700 份文档也是同一个流程，只是要先补数据治理、命名规范和元数据。”

验证 Qdrant：

```powershell
curl.exe http://localhost:6333/collections/rag_chunks
```

预期说明：

“看 `points_count`，现在是 6，说明测试文档已经进入向量库。”

---

## Step 3：问答演示，120 秒

讲解词：

“接下来演示查询入口。业务系统以后不需要知道后面有多少模型和数据库，只需要调用一个 API。”

请求示例：

```powershell
curl.exe -X POST http://localhost:8000/api/v1/query `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"产品 X 怎么安装？\"}"
```

讲解词：

“一个合格的 RAG 答案要看 4 件事：有没有引用来源、来源是不是具体文档、相关性分数是否合理、回答是否围绕问题本身。”

可追加问题：

```powershell
curl.exe -X POST http://localhost:8000/api/v1/query `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"客户 ACME 的合作背景是什么？\"}"
```

```powershell
curl.exe -X POST http://localhost:8000/api/v1/query `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"团队的代码 review 流程是什么？\"}"
```

如果没有真实 Key：

“如果现场 `.env` 里还是 placeholder Key，真实 LLM 生成会被跳过或失败。这个不是架构问题，而是外部模型凭证还没填。当前已经验证的是本地 embedding、Qdrant 入库和检索链路。”

---

## Step 4：技术承诺，60 秒

讲解词：

“这套系统现在有 3 个承诺。”

“第一，低厂商绑定。后续切换模型主要改 `.env`，业务代码不直接写死某个模型厂商。”

“第二，数据边界清楚。文档、向量和对象存储在本地，云端只负责模型推理；敏感信息是否送出，会在后续数据治理里明确规则。”

“第三，可持续演进。每个代码任务都有 Handoff、自审查和反模式记录，避免做完一轮没人知道系统为什么这么写。”

展示：

```powershell
Get-ChildItem docs\handoffs
Get-Content docs\CODEX_QUICK_REF.md -TotalCount 20
```

---

## Step 5：Q&A 锚点，90 秒

| 业务问题 | 建议回答 |
|----------|----------|
| 现在能不能直接导入 700 份文档？ | 技术链路可以，但不建议直接全量导入。Week 2 先做命名规范、文档类型、客户主数据和样本试跑，避免把脏数据放进知识库。 |
| 回答不准怎么办？ | RAG 不是一次调好。Week 2 先看检索命中率和引用来源，Week 3 再做质量调优、知识缺口反馈和召回策略优化。 |
| 敏感客户资料会不会被云端模型收集？ | 当前设计是文档和向量留在本地；是否把片段送给云端 LLM，要由数据分级规则决定。高敏内容可以先禁用云端生成或走本地模型。 |
| 多久能给业务试用？ | 按当前节奏，Phase 1 末可以开放小范围试用，但前提是 Week 2 拿到真实文档、真实 Key 和业务审查人。 |
| 费用怎么控制？ | 先用小样本测调用量，再按 30 人试用规模估算。当前阶段不承诺固定月费，避免在没有真实调用数据前误导。 |
| 为什么 #21 Ollama 切换延后？ | #21 验证的是本地 LLM 切换能力，不影响 Week 1 的 RAG 主链路。等真实 Key 和基础链路稳定后再补做，排查变量更少。 |

---

## 结束语，20 秒

“Week 1 的目标是证明底座可行，现在已经完成。Week 2 的重点会从写代码转到数据治理：真实文档在哪里、如何命名、如何分类、哪些内容能送模型、哪些必须留在本地。”
