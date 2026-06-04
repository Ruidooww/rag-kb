# 迁移验证：百炼 -> Ollama (qwen2.5:3b) 切换演示

> **执行者**：Codex  
> **完成日期**：2026-06-04  
> **目的**：验证铁律 #7（保留 Ollama 兼容性）-- 业务代码零改动，仅用 `.env` 切换 LLM

---

## 0. TL;DR

✅ **验证通过（带基线限制说明）**

- 业务代码 diff：`git diff --stat backend/app/`、`backend/scripts/`、`backend/tests/` 均为空。
- Ollama 模式 query：HTTP 200，返回 JSON 含 `answer` / `sources` / `latency_ms` / `model_used`。
- Ollama 模型：`qwen2.5:3b`。
- Ollama query 耗时：`24.124022` 秒（curl total），API 内部 `latency_ms=23904`。
- Ollama answer 长度：219 字符。
- Ollama sources 数：5。
- 回滚验证：`.env` 已恢复到百炼配置，health 仍为 200；query 行为与切换前一致，因原 `LLM_API_KEY` 是中文 placeholder 返回 500。
- 切换字段：仅 `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY` 三项。

结论：本任务证明业务代码不需要修改即可切到 Ollama OpenAI-compatible endpoint。百炼模式未返回答案是既有 `.env` placeholder Key 问题，不是本次迁移引入的问题。

---

## 1. 环境快照（切换前）

### 1.1 `.env` 关键配置（API Key 已遮蔽）

命令：

```powershell
Get-Content .env | Where-Object { $_ -match '^LLM_' } | ForEach-Object {
  if ($_ -match '^LLM_API_KEY=') { 'LLM_API_KEY=***REDACTED***' } else { $_ }
}
```

输出：

```text
LLM_PROVIDER=bailian
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-omni-flash
LLM_API_KEY=***REDACTED***
```

### 1.2 Ollama 状态

`ollama` CLI 当前未加入 PowerShell PATH：

```text
ollama : The term 'ollama' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

但 Ollama HTTP API 正常：

```powershell
curl.exe -sS --max-time 5 http://localhost:11434/api/tags
```

输出摘要：

```json
{
  "models": [
    {
      "name": "qwen2.5:3b",
      "model": "qwen2.5:3b",
      "size": 1929912432,
      "details": {
        "family": "qwen2",
        "parameter_size": "3.1B",
        "quantization_level": "Q4_K_M",
        "context_length": 32768
      }
    }
  ]
}
```

本轮按审查者确认使用 `qwen2.5:3b`。

### 1.3 Docker / Qdrant 状态

`docker` CLI 当前未加入 PowerShell PATH：

```text
docker : The term 'docker' is not recognized as the name of a cmdlet, function, script file, or operable program.
```

Qdrant HTTP API 正常：

```powershell
curl.exe -sS --max-time 5 -w "`nstatus=%{http_code}`n" http://localhost:6333/collections/rag_chunks
```

输出摘要：

```text
points_count: 6
vectors.size: 1024
status=200
```

### 1.4 backend 进程

切换前 backend 未运行，启动命令：

```powershell
cd C:\Users\Ruidoww\Desktop\RAG\backend
C:\Users\Ruidoww\.local\bin\uv.exe run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

启动输出：

```text
Started server process [16728]
Starting RAG-KB backend in development mode
Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

### 1.5 基线 health 输出

命令：

```powershell
curl.exe -sS --max-time 10 -w "`nstatus=%{http_code}`n" http://localhost:8000/api/v1/health
```

输出：

```json
{"status":"ok","app_env":"development","version":"0.1.0"}
status=200
```

### 1.6 基线 query 输出（百炼模式）

命令：

```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/query' `
  -Method Post `
  -ContentType 'application/json; charset=utf-8' `
  -Body '{"query":"产品X怎么安装"}' `
  -TimeoutSec 120
```

输出：

```text
error=The remote server returned an error: (500) Internal Server Error.
elapsed_ms=10119
http_status=500
error_body=
```

backend 日志根因：

```text
UnicodeEncodeError: 'ascii' codec can't encode characters in position 10-16
headers_dict: {'Authorization': 'Bearer sk-请填入你的百炼API_Key', ...}
```

判断：百炼基线 query 不可用，原因是原 `.env` 使用中文 placeholder API Key。该问题是切换前既有状态，不是 Ollama 迁移导致。

---

## 2. 切换步骤

### 2.1 备份当前 `.env`

命令：

```powershell
Copy-Item -LiteralPath .env -Destination .env.bailian-backup -Force
```

输出：

```text
backup_created=
True
LLM_PROVIDER=bailian
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-omni-flash
LLM_API_KEY=***REDACTED***
```

说明：验证结束后已用该文件恢复 `.env`。为避免未跟踪 secret 文件残留，最终提交前会删除 `.env.bailian-backup`。

### 2.2 修改 `.env`（仅 3 个字段）

将：

```env
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-omni-flash
LLM_API_KEY=sk-请填入你的百炼API_Key
```

改为：

```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
LLM_API_KEY=ollama-no-key-needed
```

说明：`LLM_PROVIDER` 按本任务“三字段切换”约束未修改；当前业务代码实际读取的是 `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`。

### 2.3 验证业务代码零改动

命令：

```powershell
git diff --stat backend/app/
git diff --stat backend/scripts/
git diff --stat backend/tests/
```

输出：

```text
=== business code diff app ===
=== business code diff scripts ===
=== business code diff tests ===
```

三项均为空。

### 2.4 切换后的 `.env` 快照（API Key 已遮蔽）

输出：

```text
LLM_PROVIDER=bailian
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
LLM_API_KEY=***REDACTED***
```

### 2.5 重启 backend

关闭旧进程后重启：

```powershell
cd C:\Users\Ruidoww\Desktop\RAG\backend
C:\Users\Ruidoww\.local\bin\uv.exe run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

输出：

```text
Started server process [31028]
Starting RAG-KB backend in development mode
Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

---

## 3. 切换后验证（Ollama 模式）

### 3.1 健康检查

命令：

```powershell
curl.exe -sS --max-time 10 -w "`nstatus=%{http_code}`n" http://localhost:8000/api/v1/health
```

输出：

```json
{"status":"ok","app_env":"development","version":"0.1.0"}
status=200
```

### 3.2 同样 query 跑一次

第一次使用 `Invoke-WebRequest` 调用时，backend 日志显示服务端实际返回 HTTP 200，但 PowerShell 客户端解析失败：

```text
backend log: "POST /api/v1/query HTTP/1.1" 200
client error=Object reference not set to an instance of an object.
elapsed_ms=46970
```

为拿到真实 JSON 响应，改用 `curl.exe` + UTF-8 临时请求文件重跑同一问题：

```powershell
curl.exe -sS --max-time 180 `
  -H "Content-Type: application/json; charset=utf-8" `
  --data-binary "@$env:TEMP\rag-query-request.json" `
  http://localhost:8000/api/v1/query
```

curl 元数据：

```text
http_status=200
elapsed_total=24.124022
elapsed_ms_stopwatch=24152
```

响应指标：

```text
model_used=qwen2.5:3b
answer_length=219
sources_count=5
latency_ms=23904
```

响应 JSON：

```json
{
  "answer": "产品 X 的安装步骤如下：\n\n1. 准备一台已安装 Docker Desktop 的工作站，确认本地端口没有被其他服务占用。\n2. 将产品 X 的安装包解压到固定目录，复制 `.env.example` 为 `.env`，并填写数据库、对象存储和模型服务地址。\n3. 在项目目录执行 `docker compose up -d` 启动基础设施，再启动后端服务并访问健康检查接口确认状态正常。\n\n[来源: product_x_manual]",
  "sources": [
    {
      "doc_id": "product_x_manual",
      "chunk_id": "product_x_manual:0",
      "score": 0.7903037,
      "metadata": {
        "chunk_id": "product_x_manual:0",
        "doc_id": "product_x_manual",
        "file_path": "C:\\Users\\Ruidoww\\Desktop\\RAG\\backend\\tests\\fixtures\\sample_docs\\product_x_manual.md",
        "chunk_index": 0
      }
    },
    {
      "doc_id": "product_x_manual",
      "chunk_id": "product_x_manual:1",
      "score": 0.6168251,
      "metadata": {
        "chunk_id": "product_x_manual:1",
        "doc_id": "product_x_manual",
        "file_path": "C:\\Users\\Ruidoww\\Desktop\\RAG\\backend\\tests\\fixtures\\sample_docs\\product_x_manual.md",
        "chunk_index": 1
      }
    },
    {
      "doc_id": "faq_general",
      "chunk_id": "faq_general:0",
      "score": 0.5785043
    },
    {
      "doc_id": "release_notes_v2",
      "chunk_id": "release_notes_v2:0",
      "score": 0.55619395
    },
    {
      "doc_id": "customer_case_acme",
      "chunk_id": "customer_case_acme:0",
      "score": 0.55294704
    }
  ],
  "latency_ms": 23904,
  "model_used": "qwen2.5:3b"
}
```

说明：上方 JSON 为可读性省略了部分较长 `text` 字段，但保留了实际 answer、source identity、score、latency 和 model 字段。完整原始响应已在本地验证命令输出中读取。

### 3.3 答案对比

| 项 | 百炼 omni-flash | Ollama qwen2.5:3b |
|----|----------------|-------------------|
| HTTP 状态 | 500 | 200 |
| 耗时 | 10.119 秒后返回 500 | 24.124 秒 |
| 答案长度 | N/A | 219 字符 |
| sources | N/A | 5 |
| `model_used` | N/A | `qwen2.5:3b` |
| 引用准确性 | N/A | 命中 `product_x_manual` |
| 主观质量 | N/A（Key placeholder 导致失败） | 可用，质量符合小模型预期 |

### 3.4 答案内容对比

**百炼答案**：

> 无。当前 `.env` 使用中文 placeholder API Key，导致 header 编码错误并返回 500。

**Ollama 答案**：

> 产品 X 的安装步骤如下：
>
> 1. 准备一台已安装 Docker Desktop 的工作站，确认本地端口没有被其他服务占用。
> 2. 将产品 X 的安装包解压到固定目录，复制 `.env.example` 为 `.env`，并填写数据库、对象存储和模型服务地址。
> 3. 在项目目录执行 `docker compose up -d` 启动基础设施，再启动后端服务并访问健康检查接口确认状态正常。
>
> [来源: product_x_manual]

---

## 4. 回滚验证

### 4.1 恢复 `.env`

命令：

```powershell
Copy-Item -LiteralPath .env.bailian-backup -Destination .env -Force
```

恢复后输出：

```text
LLM_PROVIDER=bailian
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-omni-flash
LLM_API_KEY=***REDACTED***
```

### 4.2 重启 backend

输出：

```text
Started server process [16128]
Starting RAG-KB backend in development mode
Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

### 4.3 回滚后 health

输出：

```json
{"status":"ok","app_env":"development","version":"0.1.0"}
status=200
```

### 4.4 回滚后 query

输出：

```text
error=The remote server returned an error: (500) Internal Server Error.
elapsed_ms=8516
http_status=500
error_body=
```

backend 日志根因仍为：

```text
UnicodeEncodeError: 'ascii' codec can't encode characters in position 10-16
headers_dict: {'Authorization': 'Bearer sk-请填入你的百炼API_Key', ...}
```

判断：回滚已恢复到切换前配置和行为；百炼 query 不可用是 placeholder Key 的既有问题，不是 Ollama 切换造成。

---

## 5. 铁律 #7 验收结论

- [x] 业务代码 0 改动：`backend/app/`、`backend/scripts/`、`backend/tests/` diff 均为空。
- [x] 切换仅修改 `.env` 中 3 个字段：`LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`。
- [x] Ollama 模式下 `/api/v1/query` 返回 200。
- [x] Ollama 模式返回 JSON 含 `answer` / `sources` / `latency_ms` / `model_used`。
- [x] `answer` 字段非空。
- [x] `model_used=qwen2.5:3b`，证明模型名来自配置。
- [x] 回滚到百炼配置成功，health 正常；query 行为与切换前一致。
- [x] 切换过程没有修改任何 `.py` 文件。

✅ 全部核心项通过，铁律 #7 验证通过。

---

## 6. 已知限制（不在本验证范围）

- 百炼模式使用的是 placeholder API Key，且 placeholder 包含中文，导致 OpenAI/httpx header 构造时报 `UnicodeEncodeError`。这需要后续填入真实 Key 或把 placeholder 改成 ASCII，占位问题不属于本任务业务代码改动范围。
- Rerank 仍走百炼 `gte-rerank-v2`。在 Ollama 模式下，rerank 会失败并 fallback 到向量顺序，这是 #20 已有逻辑。
- Embedding 一直是本地 `BAAI/bge-m3`，本任务不切换 embedding，也不需要重跑 ingest。
- `ollama` CLI 和 `docker` CLI 当前不在 PowerShell PATH，但 Ollama HTTP API 与 Qdrant HTTP API 均可用。
- `LLM_PROVIDER` 本轮未修改，因为任务明确要求 `.env` 切换只改 3 个字段；当前代码的实际调用路径不依赖该字段。

### 全私有化路径（未来任务）

如果后续要 100% 本地化：

1. 引入本地 rerank 服务，例如 bge-reranker。
2. 将 `RERANK_BASE_URL` / `RERANK_MODEL` 迁移到本地实现。
3. 明确 `.env` 中 `LLM_PROVIDER` 的语义是否要同步参与展示和验收。
4. 修复或替换中文 placeholder API Key，避免百炼基线在未填真实 Key 时出现 header 编码错误。

---

## 7. 给后续任务的提示

- 本迁移报告位置：`docs/migration-test.md`。
- 切换 SOP 的 3 个关键字段是：
  - `LLM_BASE_URL=http://localhost:11434/v1`
  - `LLM_MODEL=qwen2.5:3b`
  - `LLM_API_KEY=ollama-no-key-needed`
- 本轮未修改业务代码，说明 #19 的模型抽象和 #20 的 RAG Pipeline 对 Ollama 兼容。
- 后续如果要求演示“百炼 vs Ollama 质量对比”，必须先填入真实百炼 API Key；当前只能对比“placeholder 失败 vs Ollama 成功”。
- 后续如果要让 `.env` 展示更语义一致，可单独评估是否把 `LLM_PROVIDER` 也纳入切换字段；本任务没有这么做，以保持“三字段切换”验收口径。
