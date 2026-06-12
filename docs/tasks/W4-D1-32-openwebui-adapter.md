# 任务 #32：OpenWebUI 套壳对接（lean MVP UI）

> **版本**：v1.0
> **创建日期**：2026-06-12
> **预估工时**：2-3 工作日
> **前置任务**：#31 ConfigQA Agent + `/api/v1/internal/qa` SSE 已落地
> **后续任务**：W4 D3 内部 5 人试用 → W4 D5 全员 30 人开放
> **优先级**：🔴 高（lean MVP W4 交付物，决定能不能让 30 人真用起来）

---

## §1 任务背景

lean MVP UI 不自写 Next.js（节省 1-2 周），改用 [OpenWebUI](https://github.com/open-webui/open-webui)（70K+ stars / MIT / 自带聊天 UI + 引用 + Markdown + 流式 + 用户管理）。

后端 `/api/v1/internal/qa` 已经是 SSE 流式，本任务建一个 OpenAI 兼容适配层：

```
OpenWebUI（http://localhost:3001）
   ↓ POST /v1/chat/completions （OpenAI 兼容格式）
适配层 /api/v1/openai/chat/completions（本任务新建）
   ↓ 转译 + 鉴权
ConfigQA /api/v1/internal/qa（已存在）
```

设计思想：**OpenWebUI 看到的是"一个 OpenAI 兼容模型"**，模型名叫 `ipguard-kb`。OpenWebUI 不感知 RAG，背后实际跑 ConfigQA Agent。

---

## §2 范围

- ✅ docker-compose 加 OpenWebUI 容器（端口 3001）
- ✅ `backend/app/api/openai_adapter.py`：`POST /api/v1/openai/chat/completions` + `GET /api/v1/openai/models`
- ✅ ConfigQA SSE → OpenAI chat completions chunk 格式转译
- ✅ 引用 `[1] [2]` 注入到答案 markdown + 引用源列表附加在末尾
- ✅ OpenWebUI ↔ 适配层鉴权（API Key 模式，先简化）
- ✅ feedback 回流（OpenWebUI 👍/👎 → 适配层 → `/api/v1/internal/qa/feedback`）
- ✅ docker 镜像首次启动 init 脚本（建管理员 + 配模型）
- ✅ docs/sop/openwebui-quickstart.md（30 人内部使用文档）

- ❌ 不改 OpenWebUI 源码（fork 风险大；通过 OpenAI 兼容协议解耦）
- ❌ 不做飞书 / 企微 SSO 集成（OpenWebUI 内置账号系统 lean MVP 够用）
- ❌ 不做多模型切换（lean MVP 只暴露 `ipguard-kb` 一个）

---

## §3 任务目标

1. `docker compose up -d openwebui` 启动 OpenWebUI，浏览器访问 `http://localhost:3001` 能看到登录页
2. OpenWebUI 后台配「OpenAI 兼容」provider，base_url `http://host.docker.internal:8000/api/v1/openai`，输入 API key
3. 在 OpenWebUI 选模型 `ipguard-kb` → 输入"自动加解密多目录怎么配" → 流式输出答案 + 末尾引用源列表
4. 答案中 `[1] [2]` 渲染为可点击 link，点击展开引用源（OpenWebUI 自带 markdown 渲染）
5. 👍/👎 按钮回流到 PG `feedback` 表（端到端验证 1 条 feedback 落库）
6. 30 人通过浏览器访问内网域名（如 `kb.huayijunan.local`）即可使用，无需安装客户端
7. 测试覆盖：适配层单元测试 ≥ 8 项 + docker compose health check + 端到端手动验收

---

## §4 文件清单

### 4.1 `docker-compose.yml`（追加 openwebui 服务段）

```yaml
  openwebui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: rag-openwebui
    ports:
      - "${OPENWEBUI_PORT:-3001}:8080"
    environment:
      OPENAI_API_BASE_URL: http://host.docker.internal:8000/api/v1/openai
      OPENAI_API_KEY: ${OPENWEBUI_BACKEND_KEY}
      WEBUI_NAME: IP-Guard 产品 KB
      WEBUI_AUTH: "true"
      DEFAULT_USER_ROLE: "user"        # 新注册默认 user 不是 admin
      ENABLE_SIGNUP: "false"            # 关闭注册，30 人手动建账号
      DEFAULT_MODELS: "ipguard-kb"
    extra_hosts:
      - "host.docker.internal:host-gateway"   # Linux 需要
    volumes:
      - ./data/openwebui:/app/backend/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -fs http://localhost:8080/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
```

### 4.2 `.env.example`（追加）

```bash
# OpenWebUI（lean MVP UI）
OPENWEBUI_PORT=3001
# OpenWebUI 调适配层时用的内部 key，跟外部用户 token 不同
OPENWEBUI_BACKEND_KEY=please-change-me-strong-random-string
```

### 4.3 `backend/app/api/openai_adapter.py`（新建核心）

```python
"""OpenAI Chat Completions 兼容适配层。

让 OpenWebUI（或任何 OpenAI 兼容客户端）能用 ConfigQA Agent，
对客户端屏蔽 RAG 细节。
"""
internal_router = APIRouter(prefix="/openai", tags=["openai-compat"])

MODEL_NAME = "ipguard-kb"


@internal_router.get("/models")
async def list_models(_auth: None = Depends(_verify_backend_key)) -> dict:
    """OpenWebUI 启动时拉取模型列表。"""
    return {
        "object": "list",
        "data": [{
            "id": MODEL_NAME,
            "object": "model",
            "created": int(time.time()),
            "owned_by": "huayijunan",
        }],
    }


@internal_router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionsRequest,
    _auth: None = Depends(_verify_backend_key),
) -> StreamingResponse | dict:
    """OpenAI Chat Completions 入口。

    - request.messages 取最后一条 user message 作 query
    - 跑 ConfigQA graph
    - 转译为 OpenAI streaming chunk 格式 / 非流式 dict 格式
    """
    query = _extract_user_query(request.messages)
    user = _synthesize_internal_user_from_backend_key()  # OpenWebUI 已自己鉴权过

    graph = build_configqa_graph()
    state = {"query": query, "user_id": user.user_id, ...}

    if request.stream:
        return StreamingResponse(
            _to_openai_chunks(graph.astream(state), model=MODEL_NAME),
            media_type="text/event-stream",
        )
    final_state = await graph.ainvoke(state)
    return _to_openai_completion(final_state, model=MODEL_NAME)


def _verify_backend_key(authorization: str = Header(...)) -> None:
    """简化版鉴权：OpenWebUI 用 OPENWEBUI_BACKEND_KEY 调本层。"""
    expected = settings.openwebui_backend_key.get_secret_value()
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing Bearer token")
    if not secrets.compare_digest(authorization[7:], expected):
        raise HTTPException(401, "Invalid backend key")
```

### 4.4 `backend/app/services/openai_translator.py`（流式转译）

```python
async def _to_openai_chunks(
    state_stream: AsyncIterator[QAState],
    *,
    model: str,
) -> AsyncIterator[bytes]:
    """LangGraph state stream → OpenAI chat.completion.chunk SSE."""
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())
    citations_buffer: list[Citation] = []

    async for state in state_stream:
        # 节点完成时 state 含部分字段；取 answer / citations 增量推
        if "citations" in state and state["citations"] and not citations_buffer:
            citations_buffer = state["citations"]
        if "answer" in state and state["answer"]:
            yield _make_chunk(chunk_id, model, created, delta=state["answer"])

    # 答案末尾追加引用源
    if citations_buffer:
        footer = "\n\n---\n**引用来源**\n" + "\n".join(
            f"[{c.n}] {c.title}（p.{c.page or '-'}）— 相关度 {int(c.score * 100)}%"
            for c in citations_buffer
        )
        yield _make_chunk(chunk_id, model, created, delta=footer)

    # finish reason
    yield _make_chunk(chunk_id, model, created, finish_reason="stop")
    yield b"data: [DONE]\n\n"


def _make_chunk(chunk_id, model, created, delta=None, finish_reason=None) -> bytes:
    payload = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {} if delta is None else {"content": delta}, "finish_reason": finish_reason}],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()
```

### 4.5 `backend/app/models/openai_compat.py`（Pydantic）

```python
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionsRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
```

### 4.6 `backend/app/core/config.py`（追加）

```python
openwebui_backend_key: SecretStr
```

### 4.7 `backend/tests/api/test_openai_adapter.py`（≥ 8 项）

mock build_configqa_graph：

- `test_list_models_returns_ipguard_kb`
- `test_chat_completions_extracts_last_user_message`
- `test_chat_completions_streaming_returns_sse_chunks`
- `test_chat_completions_non_streaming_returns_full_response`
- `test_citations_appended_to_answer_footer`
- `test_unauthorized_request_returns_401`
- `test_bad_backend_key_returns_401`
- `test_refused_state_returns_canned_text_via_openai_format`

### 4.8 `scripts/init_openwebui.sh`（首次启动初始化）

```bash
#!/usr/bin/env bash
# 首次启动后用：
#   1. 建管理员账号
#   2. 在 OpenWebUI 后台填 OPENWEBUI_BACKEND_KEY 作为 OpenAI API Key
# 文档化操作，不自动跑
echo "OpenWebUI 已启动 → http://localhost:${OPENWEBUI_PORT:-3001}"
echo "首次访问会让你设管理员密码"
echo "登录后：Settings → Connections → OpenAI API"
echo "  API Base URL: http://host.docker.internal:8000/api/v1/openai"
echo "  API Key: $(grep OPENWEBUI_BACKEND_KEY .env | cut -d= -f2)"
echo "然后 Settings → Models → 应该自动发现 ipguard-kb"
```

### 4.9 `docs/sop/openwebui-quickstart.md`（30 人内部使用文档）

短文档（≤ 50 行）：
- 浏览器访问 `http://kb.huayijunan.local`（管理员准备 DNS）
- 用工号 + 邮箱注册（管理员预建账号；ENABLE_SIGNUP=false）
- 选 `ipguard-kb` 模型
- 提问示例：「Mac 客户端怎么装」/「V4 升级步骤」/「忘记控制台密码」
- 答案末尾会带引用源 PDF 名字 + 页码，点击 [N] 跳到引用
- 不满意点 👎 + 写一句话原因（喂回 feedback 表）

### 4.10 `backend/app/api/router.py`（修改）

`internal_router.include_router(openai_adapter.internal_router)` — 挂 internal_router 下（原则 P3，OpenAI 适配层不对外）。

---

## §5 验收

```powershell
Set-Location 'C:\Users\Ruidoww\Desktop\RAG\backend'

# 1. 单测
& uv run pytest tests/api/test_openai_adapter.py -v   # ≥ 8 passed

# 2. 全量回归
& uv run pytest -m "not integration" --cov=app

# 3. docker 启动
Set-Location '..'
docker compose up -d openwebui
docker compose ps openwebui     # health: healthy

# 4. OpenAI 兼容验证
curl http://localhost:8000/api/v1/openai/models \
  -H "Authorization: Bearer $env:OPENWEBUI_BACKEND_KEY"
# 应返回 {"object":"list","data":[{"id":"ipguard-kb",...}]}

curl http://localhost:8000/api/v1/openai/chat/completions \
  -H "Authorization: Bearer $env:OPENWEBUI_BACKEND_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"ipguard-kb","messages":[{"role":"user","content":"Mac 客户端怎么装"}],"stream":false}'
# 应返回带 content 的完整 chat.completion 结构

# 5. UI 验证
# 浏览器 http://localhost:3001 → 登录 → 选 ipguard-kb → 提问 → 看流式答案 + 引用
```

---

## §6 风险

| 风险 | 缓解 |
|------|------|
| OpenWebUI 升级 break OpenAI 协议兼容 | pinned 镜像 tag（避免 `:main` 浮动，改用 `:0.x.y`）|
| host.docker.internal 在某些 Linux 不解析 | docker-compose `extra_hosts: host-gateway` 已加；Linux 用户验证 |
| OpenWebUI 自带账号系统跟 #67 LocalIdP 重复 | lean MVP 接受；Phase 2 接飞书 SSO 时改 OpenWebUI 走 OAuth Proxy |
| feedback 回流路径长 | OpenWebUI 把 👍/👎 当模型反馈存自己 DB；本任务 webhook 转发到我方 feedback 表（可选，复杂度↑）。简化：先看 OpenWebUI 内置统计，Phase 2 再做端到端回流 |
| Markdown 引用 `[1]` 渲染 | OpenWebUI 原生 markdown 支持 footnote 语法；如不行用普通链接降级 |
| 30 人并发流式压力 | uvicorn 默认 4 worker；超出再加；MVP 阶段 30 人不会并发突发 |

### 新增依赖

无（OpenWebUI 容器自带；适配层只用 stdlib + 已装的 FastAPI / pydantic）

---

## §7 禁止事项

- ❌ `/api/v1/openai/*` 挂 public_router 或顶层（违反原则 P3）
- ❌ `OPENWEBUI_BACKEND_KEY` 写死代码 / commit 到 git（必须走 .env）
- ❌ fork OpenWebUI 源码改业务逻辑（fork 维护成本高；走 OpenAI 兼容协议解耦）
- ❌ 在适配层用 `import openai`（铁律 #1，业务调 `get_llm`；适配层只是协议转译，不调 LLM）
- ❌ 错误信息回显 query / user_id（PR #15 N1）
- ❌ 不验 backend key 就让请求进 graph（layer 2）
- ❌ docker-compose 用 `:main` tag（升级不可控；用具体版本号）

---

## §8 参考

- OpenWebUI 文档：https://docs.openwebui.com/
- OpenAI Chat Completions API：https://platform.openai.com/docs/api-reference/chat
- `docs/tasks/W3-D1-31-configqa-agent.md`（被适配的 Agent）
- `CLAUDE.md` v1.2 § 铁律 #1 / § 原则 P3
- `docs/reviews/PR-15.md` § N1 错误信息脱敏

---

_v1.0 | 2026-06-12 | lean MVP W4 UI 套壳_

