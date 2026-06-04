# Task #21: Ollama 切换演示（迁移铁律 #7 验收）

> **Phase**: 1 | **Week**: 1 | **Day**: 5
> **预估工时**: 2-3 小时
> **优先级**: 🔒 关键（Week 1 灵魂验收点）
> **前置任务**: #15-#20，特别是 #19（LlamaIndex 抽象）+ #20（RAG Pipeline）
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

本任务**唯一目的**：证明铁律 #7（保留 Ollama 兼容性）真的成立——**业务代码零改动，仅修改 `.env` 即可把 LLM 从云端百炼切到本地 Ollama**。

这是 Week 1 设计的灵魂承诺。如果本任务跑不通，前 6 个任务的架构基础就要重做。

**演示范围**（明确定义）：
- ✅ **LLM 层切换**：百炼 `qwen3.5-omni-flash` → 本地 Ollama `qwen2.5:3b`
- ✅ **Embedding 层不变**：本地 bge-m3（一直就是本地，无需切换）
- ⚠️ **Rerank 层不切换**：百炼 `gte-rerank-v2` 保持（Ollama 无原生 Rerank，本任务不上 bge-reranker，留到全私有化阶段）

**核心验收点**：
- `grep -r "import dashscope\|qwen3.5-omni\|qwen2.5" backend/app/` 命中数为 0（所有模型名都在 .env）
- 切换前后 `git diff --stat backend/app/` 无任何业务代码改动
- `/api/v1/query` 在 Ollama 模式下能返回有效答案（质量可能不及云端）

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| Ollama 已安装 | `ollama --version` | 返回版本号 |
| Ollama 服务运行中 | `curl http://localhost:11434/api/tags` | 返回 JSON |
| qwen2.5:3b 已 pull | `ollama list \| grep qwen2.5:3b` | 显示模型 |
| Docker 4 服务 healthy | `docker compose ps` | qdrant / postgres / minio / infinity 都 healthy |
| #20 已合并到 main | `ls backend/app/services/rag_pipeline.py` | 存在 |
| 5 份测试文档已入库 | `curl http://localhost:6333/collections/rag_chunks` | count >= 5 |
| .env 中 LLM 字段当前指向百炼 | `cat .env \| grep LLM_BASE_URL` | 显示 dashscope |

---

## 3. 任务目标

完成后业务方能：
```powershell
# 1. 当前用百炼 LLM 跑通 query（基线）
curl -X POST http://localhost:8000/api/v1/query -d '{"query": "产品X怎么安装"}'
# 期望：返回带引用的答案

# 2. 改 .env 一行（LLM_BASE_URL + LLM_MODEL）
# 3. 重启 backend（不动任何 .py 文件）

# 4. 再跑同样 query
curl -X POST http://localhost:8000/api/v1/query -d '{"query": "产品X怎么安装"}'
# 期望：仍能返回答案（质量可能略差）

# 5. 切回百炼，验证回滚也行
```

**最终产出**：`docs/migration-test.md` 详细记录整个切换过程 + 真实输出。

---

## 4. 输出文件清单

本任务**几乎不产代码**，只产配置和文档。共 3 个产出：

### 4.1 `.env.example`（追加 Ollama 切换示例段）

在 .env.example 末尾追加：

```env
# ====================================================
# 切换到本地 Ollama 示例（铁律 #7 验收用）
# ====================================================
# 取消注释以下行 + 注释掉上面的百炼配置，即可切到 Ollama：
#
# LLM_PROVIDER=ollama
# LLM_BASE_URL=http://localhost:11434/v1
# LLM_MODEL=qwen2.5:3b
# LLM_API_KEY=ollama-no-key-needed
#
# 注：Rerank 保持百炼（Ollama 无原生 Rerank），如需全本地需另装 bge-reranker
```

### 4.2 `docs/migration-test.md`（核心产出，详细文档）

按以下模板填写，每个 Step 必须含**真实命令输出**：

```markdown
# 迁移验证：百炼 → Ollama 切换演示

> **执行者**：Codex
> **完成日期**：2026-06-04
> **目的**：验证铁律 #7（保留 Ollama 兼容性）—— 业务代码零改动，仅 .env 切换

---

## 0. TL;DR

✅ 验证通过 / ❌ 失败原因
- 业务代码 diff：[贴 git diff --stat backend/app/ 输出，应为空]
- 切换前 query 耗时：X 秒，答案长度 Y 字
- 切换后 query 耗时：X 秒，答案长度 Y 字
- 回滚验证：✅ / ❌

---

## 1. 环境快照（切换前）

### 1.1 .env 关键配置
[贴 grep -E "^LLM_" .env 的输出，遮蔽 API_KEY]

### 1.2 Ollama 状态
[贴 ollama list 输出]

### 1.3 backend 进程
[贴 ps / Get-Process python 输出，确认服务在跑]

### 1.4 基线 query 输出
[贴完整 curl /api/v1/query 输出 + jq 美化]

---

## 2. 切换步骤

### 2.1 备份当前 .env
cp .env .env.bailian-backup

### 2.2 修改 .env（仅 3 行）
将：
  LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
  LLM_MODEL=qwen3.5-omni-flash
  LLM_API_KEY=sk-...
改为：
  LLM_BASE_URL=http://localhost:11434/v1
  LLM_MODEL=qwen2.5:3b
  LLM_API_KEY=ollama-no-key-needed

### 2.3 验证业务代码零改动
git diff --stat backend/app/
[贴输出，应为空]

git status
[贴输出，应只有 .env 改动（且 .env 在 gitignore，所以 status 干净）]

### 2.4 重启 backend
（停掉旧进程，重新跑 uv run uvicorn）

---

## 3. 切换后验证

### 3.1 健康检查
curl http://localhost:8000/api/v1/health
[贴输出]

### 3.2 同样 query 跑一次
curl -X POST http://localhost:8000/api/v1/query -d '{"query": "产品X怎么安装"}'
[贴完整输出，记录耗时]

### 3.3 答案对比

| 项 | 百炼 omni-flash | Ollama qwen2.5:3b |
|----|----------------|-------------------|
| 耗时 | X 秒 | Y 秒 |
| 答案长度 | A 字 | B 字 |
| 引用准确性 | ✅ / ❌ | ✅ / ❌ |
| 主观质量 | 高 / 中 / 低 | 高 / 中 / 低 |

### 3.4 答案内容对比（贴双方实际答案文本）

**百炼答案**：
> [完整答案]

**Ollama 答案**：
> [完整答案]

---

## 4. 回滚验证

### 4.1 恢复 .env
cp .env.bailian-backup .env

### 4.2 重启 backend

### 4.3 再跑 query
[贴输出，确认百炼模式恢复正常]

---

## 5. 铁律 #7 验收结论

- [ ] 业务代码 0 改动（git diff 为空）
- [ ] 切换仅修改 .env 中 3 个字段（LLM_BASE_URL / LLM_MODEL / LLM_API_KEY）
- [ ] Ollama 模式下 /api/v1/query 仍返回有效答案
- [ ] 回滚到百炼模式正常工作
- [ ] 切换时间 < 1 分钟（不含 backend 重启）

✅ 全部通过 → 铁律 #7 验证通过

---

## 6. 已知限制（不在本验证范围）

- Rerank 仍走百炼 `gte-rerank-v2`（Ollama 无原生 Rerank）
- Embedding 一直是本地 bge-m3（无需切换）
- 答案质量：Ollama qwen2.5:3b（小模型）< 百炼 omni-flash（旗舰），属正常

### 全私有化路径（未来任务）

如需 100% 本地：
1. 装 bge-reranker-v2-m3 通过 infinity 服务
2. 修改 .env 的 RERANK_BASE_URL
3. 业务代码同样零改动

留到 Phase 2 末或 Phase 4 启动私有化时实施。

---

## 7. 给后续任务的提示

- 任何模型相关测试如需切到 Ollama 验证，用本文记录的命令即可
- .env 改动模板已写入 .env.example，未来新成员能照抄
- migration-test.md 是迁移友好性的"凭证"，未来 Phase 2 评审会看
```

### 4.3 `backend/scripts/verify_migration.py`（可选自动化脚本）

如果时间允许，做一个验证脚本，自动跑完上述步骤并生成对比报告：

```python
"""自动化迁移验证。

用法：
    cd backend
    uv run python scripts/verify_migration.py --mode bailian
    uv run python scripts/verify_migration.py --mode ollama

输出：将结果写入 docs/migration-test-auto.md（与手动版互补）。
"""
import asyncio
import httpx
import time
from pathlib import Path

# 简单 query + 记录耗时 + 答案
async def run_query(query: str) -> dict:
    start = time.time()
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "http://localhost:8000/api/v1/query",
            json={"query": query},
        )
    return {
        "elapsed_seconds": round(time.time() - start, 2),
        "status": resp.status_code,
        "body": resp.json() if resp.status_code == 200 else resp.text,
    }


# ... 主流程（可选实现，spec 不强制）
```

**注**：此脚本可选，时间不够可跳过。手动验证 + migration-test.md 足够。

---

## 5. 执行步骤详细命令

### Step 1：基线快照（百炼模式）

```powershell
cd C:\Users\Ruidoww\Desktop\RAG\backend

# 1.1 确认当前 .env 指向百炼
Select-String "^LLM_BASE_URL" ..\.env
# 应显示 https://dashscope.aliyuncs.com/compatible-mode/v1

# 1.2 backend 服务跑起来
uv run uvicorn app.main:app --reload

# 1.3 另开终端跑 query
curl -X POST http://localhost:8000/api/v1/query `
  -H "Content-Type: application/json" `
  -d '{\"query\": \"产品X怎么安装\"}'

# 1.4 记录耗时 + 答案（写进 migration-test.md §1.4）
```

### Step 2：切换到 Ollama

```powershell
# 2.1 备份 .env
cd C:\Users\Ruidoww\Desktop\RAG
cp .env .env.bailian-backup

# 2.2 编辑 .env（用记事本或 VSCode）
# 注释原 LLM_* 三行，启用 Ollama 三行
notepad .env

# 2.3 验证业务代码零改动
git diff --stat backend/app/
# 应输出空（无任何代码改动）

# 2.4 杀掉旧 uvicorn 进程并重启
# Ctrl+C 终端，然后：
cd backend
uv run uvicorn app.main:app --reload
```

### Step 3：Ollama 模式验证

```powershell
# 3.1 健康检查
curl http://localhost:8000/api/v1/health

# 3.2 同样 query
curl -X POST http://localhost:8000/api/v1/query `
  -H "Content-Type: application/json" `
  -d '{\"query\": \"产品X怎么安装\"}'

# 3.3 对比答案 + 耗时
```

### Step 4：回滚验证

```powershell
cd C:\Users\Ruidoww\Desktop\RAG
cp .env.bailian-backup .env

# 重启 backend，再跑同样 query
# 确认回到百炼模式
```

---

## 6. 验收标准（Definition of Done）

### 6.1 切换可行性
- [ ] Ollama 模式下 `/api/v1/query` 返回 200
- [ ] 返回 JSON 含 `answer`、`sources`、`latency_ms`、`model_used`
- [ ] `model_used` 字段反映当前用的模型（验证模型名走 settings）

### 6.2 业务代码零改动（铁律 #7 核心）
- [ ] `git diff --stat backend/app/` 输出为空
- [ ] `git diff --stat backend/scripts/` 输出为空
- [ ] `git diff --stat backend/tests/` 输出为空
- [ ] 整个切换过程没有任何 .py 文件被修改

### 6.3 配置最小化
- [ ] 仅修改 `.env` 中 3 个字段（LLM_BASE_URL / LLM_MODEL / LLM_API_KEY）
- [ ] `config.yaml` 不需要改

### 6.4 回滚成功
- [ ] 恢复 .env 后 backend 重启正常
- [ ] 百炼模式下 query 行为与切换前一致

### 6.5 文档完整
- [ ] `docs/migration-test.md` 7 个章节齐全
- [ ] 每个 Step 含真实命令输出（不能编造）
- [ ] 答案对比表填实际数据

### 6.6 v2.1 自审查
- [ ] 跑 Part A（pytest / ruff / mypy）应仍全绿（本任务不改代码）
- [ ] Handoff §0-§8 完整
- [ ] Handoff §0 TL;DR 总评 PASS

### 6.7 Git
- [ ] 在分支 `feat/W1-D5-21-ollama-switch-demo`
- [ ] commit 含 `Refs: #21`
- [ ] PR 标题含 `#21`

---

## 7. 禁止事项

- ❌ **不要改任何 .py 文件**（这是本任务的核心约束）
- ❌ **不要改 config.yaml**（业务参数不该因切换模型而变）
- ❌ **不要装 bge-reranker**（本任务不切 Rerank，留到全私有化阶段）
- ❌ **不要重新跑 ingest**（向量库还是 bge-m3 算的，LLM 切换不影响 Embedding）
- ❌ **不要在 .env 中 commit 真实 API Key**（.env 本来就在 gitignore，但 migration-test.md 里贴输出时要遮蔽 API Key）
- ❌ **不要为了让答案"更好看"重跑多次 query 挑最好的**（必须真实记录）

---

## 8. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| Ollama 服务没启动 | LLM 连接失败 | 跑 `ollama serve` 或确保 Ollama Desktop 启动 |
| qwen2.5:3b 没 pull | API 报 model not found | `ollama pull qwen2.5:3b` |
| Ollama 端口被占 | 切换后连不上 | `netstat -ano \| findstr 11434` |
| .env 改完忘了重启 backend | 还在用旧配置 | 必须 Ctrl+C + 重新 uv run |
| 答案变差就以为切换失败 | 误判 | 小模型答案弱属正常，只要返回结构正确就算通过 |
| Rerank 没改但担心混乱 | 错误等待 | 本任务不切 Rerank，仍走百炼（已说明）|
| 切换前没存基线 | 无法对比 | Step 1 必须先跑一次百炼模式 query |
| Ollama 首次响应慢 | 误判超时 | 首次加载模型需 10-30 秒，后续会快 |

---

## 9. 参考资料

- 本项目：`CLAUDE.md §铁律 #7` / `docs/CODEX_QUICK_REF.md`
- Ollama 文档：https://github.com/ollama/ollama/blob/main/docs/api.md
- Ollama OpenAI 兼容：https://github.com/ollama/ollama/blob/main/docs/openai.md

---

## 10. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 QUICK_REF + spec | 15 分钟 |
| Step 1 基线快照 + 记录 | 20 分钟 |
| Step 2 切换 + 验证业务代码零改动 | 15 分钟 |
| Step 3 Ollama 模式验证 | 15 分钟 |
| Step 4 回滚验证 | 10 分钟 |
| 写 migration-test.md（7 章节，真实输出）| 45 分钟 |
| Self-Review + Handoff | 30 分钟 |
| 提交 / PR | 10 分钟 |
| **合计** | **~2.5 小时** |

---

## 11. 与下一轮的衔接

#22 (W1-D5 Week 1 交付物整理) 会引用本任务的 `migration-test.md` 作为 W1 关键交付物之一。

Handoff §7（给下一轮提示）应至少写：
- migration-test.md 的位置
- 切换 SOP 的关键 3 行 .env 改动
- 任何切换中遇到的"非阻断但需注意"的小问题

---

_v1.0 | 任务 ID：#21 | 最后更新：2026-06-04_
