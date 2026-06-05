# 反模式知识库

> **作用**：积累历次审查中发现的"看起来 OK 但其实不好"的代码模式。
> **使用方式**：Codex 在执行 SELF_REVIEW Part C 时必须打开本文档逐条对照。
> **更新机制**：每次审查发现新反模式 → 追加到本文档 → 下一轮 Codex 自动规避。
> **维护原则**：每条都要有 ❌ 错误范例 + ✅ 正确范例 + 来源 PR。

---

## 索引

| ID | 类别 | 标题 | 严重度 |
|----|------|------|--------|
| A1 | 资源管理 | httpx.Client 重复创建 | 中 |
| B1 | 错误处理 | raise X 而非 raise X from e | 中 |
| C1 | 配置 | os.getenv 散落各处 | 高 |
| D1 | 测试 | 测试相互污染（共享 app router）| 中 |
| E1 | 性能 | 工厂函数加 @lru_cache 缓存 client | 高 |
| F1 | Spec | 依赖列表与实现描述不一致 | 中 |
| G | LangGraph | 占位，待积累 | - |
| H1 | S3 兼容存储 | env var 不是 S3 标准（产品私有） | 高 |
| H2 | S3 兼容存储 | 私有 health endpoint 跨产品复用 | 中 |
| I1 | 子 agent 协作 | sub-agent 自行扩范围 / 跳过集成测试 | 高 |
| J1 | 路由分流 | admin / CRM / 内部 search endpoint 挂错路由树 | 高 |
| K1 | 数据脱敏 | Pydantic response 明文返回敏感字段给外部用户 | 高 |

---

## A. 资源管理

### A1. httpx.Client 重复创建

**来源**：PR #3 review (W1-D3-19)
**严重度**：🟡 中

**问题**：每次重试 / 每次请求新建 httpx.Client，TCP 握手开销大。

**❌ 错误范例**：

```python
def _request_rerank(self, *, query, documents):
    for _ in range(3):
        with httpx.Client(timeout=30) as client:  # 每次新建
            response = client.post(url, ...)
```

**✅ 正确范例**：

```python
class BailianRerank:
    def __init__(self):
        self._client = httpx.Client(timeout=30)  # 复用

    def _request_rerank(self, *, query, documents):
        for _ in range(3):
            response = self._client.post(url, ...)

    def close(self):
        self._client.close()
```

**Codex 自检方法**：

```bash
grep -rB2 "httpx\.Client" backend/app/ | grep -B2 "for.*range\|while"
```

如果命中说明在循环里新建 client。

---

## B. 错误处理

### B1. raise X 而非 raise X from e

**来源**：通用最佳实践
**严重度**：🟡 中

**问题**：丢失原异常的 stacktrace，debug 困难。

**❌ 错误范例**：

```python
try:
    data = json.loads(response.text)
except json.JSONDecodeError:
    raise LLMServiceError("Failed to parse response")  # 丢失原因
```

**✅ 正确范例**：

```python
try:
    data = json.loads(response.text)
except json.JSONDecodeError as exc:
    raise LLMServiceError("Failed to parse response") from exc  # 保留 stacktrace
```

**Codex 自检方法**：

```bash
grep -rE "except.*:\s*$" backend/app/ -A 3 | grep "raise" | grep -v "from"
```

---

## C. 配置

### C1. os.getenv 散落各处

**来源**：CLAUDE.md 铁律 #2
**严重度**：🔴 高

**问题**：配置散落，迁移时改不全；绕过 pydantic 校验。

**❌ 错误范例**：

```python
# app/services/some.py
import os
api_key = os.getenv("LLM_API_KEY", "default-key")
```

**✅ 正确范例**：

```python
# app/services/some.py
from app.core.config import settings
api_key = settings.llm_api_key.get_secret_value()
```

**Codex 自检方法**：

```bash
grep -rE "os\.(getenv|environ)" backend/app/ | grep -v "core/config.py"
```

仅允许 `core/config.py` 出现，其他文件命中即违规。

---

## D. 测试

### D1. 测试相互污染（共享 app router）

**来源**：PR #2 review (W1-D3-18)
**严重度**：🟡 中

**问题**：用 `app.router.add_api_route` 动态加测试端点，后续测试会看到该端点，扩展到几十个测试时会爆炸。

**❌ 错误范例**：

```python
def test_app_exception_handler(client):
    async def raise_app_exception():
        raise ValidationError("test")
    app.router.add_api_route("/test/raise", raise_app_exception)  # 污染 app
    response = client.get("/test/raise")
```

**✅ 正确范例**：

```python
@pytest.fixture
def test_app():
    from fastapi import FastAPI
    test_app = FastAPI()
    # 注册 exception handler
    # 加测试 endpoint
    return test_app

def test_app_exception_handler(test_app):
    client = TestClient(test_app)
    response = client.get("/test/raise")
```

**Codex 自检方法**：

```bash
grep -rE "app\.router\.add_api_route|app\.add_api_route" backend/tests/
```

命中即违规。

---

## E. 性能

### E1. 工厂函数加 @lru_cache 缓存 client

**来源**：SELF_REVIEW Part C8
**严重度**：🔴 高

**问题**：LLM client 可能持有过时配置（如 .env 改了但 client 缓存了旧值），且测试间不隔离。

**❌ 错误范例**：

```python
@lru_cache
def get_llm() -> OpenAILike:  # 不要缓存外部 IO 对象
    return OpenAILike(api_key=settings.llm_api_key.get_secret_value(), ...)
```

**✅ 正确范例**：

```python
def get_llm() -> OpenAILike:  # 每次新建，OpenAILike 本身轻量
    return OpenAILike(api_key=settings.llm_api_key.get_secret_value(), ...)
```

**Codex 自检方法**：

```bash
grep -rB1 "def get_(llm|embedding|reranker|client)" backend/app/services/ | grep "@lru_cache"
```

命中即违规。

---

## F. Spec 与依赖

### F1. 依赖列表与实现描述不一致

**来源**：任务 #20 自审
**严重度**：🟡 中

**问题**：Spec 的依赖清单要求安装某个高级抽象库，但实现章节实际要求直接使用底层 SDK。这样会引入不必要依赖，甚至触发 Python 版本兼容问题。

**❌ 错误范例**：

```text
§4.3 用 qdrant-client SDK 实现 store
§4.11 同时要求安装 llama-index-vector-stores-qdrant
```

**✅ 正确范例**：

```text
如果实现只调用 qdrant-client.upsert/query_points，
依赖清单只保留 qdrant-client。
```

**Codex 自检方法**：

```bash
grep -n "uv add\\|dependencies" docs/tasks/*.md
```

发现依赖清单和实现章节不一致时，先停下向审查者确认，不要自行安装多余依赖。

---

## G. LangGraph

（暂无反模式 - 待积累。常见候选：State 设计混乱、节点内调用副作用、checkpoint 缺失等。）

---

## H. S3 兼容存储

### H1. S3 API 兼容 ≠ env var 兼容

**来源**：PR #10 review（任务 #63 RustFS 迁移）
**严重度**：🔴 高

**问题**：S3 兼容存储产品共享 S3 数据面 API，但管理面和启动配置是产品私有的。沿用其他产品（如 MinIO）的 env var 命名，或凭直觉猜测 env var，容器可能静默忽略凭据，而客户端测试用同样错的假设仍能跑通——故障只在 Console 登录或 IAM 时才暴露。

**❌ 错误范例**：

```yaml
rustfs:
  environment:
    RUSTFS_ACCESS_KEY: rustfsadmin
    RUSTFS_SECRET_KEY: rustfsadmin-please-change-me
```

**✅ 正确范例**：

先确认镜像/版本支持的启动机制，再用官方支持的方式注入凭据。当前测试的 `rustfs/rustfs:latest`，`rustfs server --help` 同时支持 CLI flags 和 `RUSTFS_ACCESS_KEY` / `RUSTFS_SECRET_KEY` env，本项目用 CLI flags 让"不支持的 env 名"无处遁形：

```yaml
rustfs:
  command:
    - server
    - --access-key
    - rustfsadmin
    - --secret-key
    - rustfsadmin-please-change-me
    - /data
```

**Codex 自检方法**：

```bash
docker exec rag-rustfs rustfs server --help | grep -E "access-key|secret-key|ROOT"
grep -nE "RUSTFS_(ROOT_USER|ROOT_PASSWORD)" docker-compose.yml
```

`--help` 输出必须与 `docker-compose.yml` 的凭据机制吻合；不支持的 env 名不得出现在 compose 中。容器重建后必须验证 Web Console / S3 凭据是否生效。

**Console 登录失败时的诊断顺序**（来自 PR #10 排查经验）：

1. **先验 S3 API**：用 `boto3.list_buckets()` 或 `aws s3 ls --endpoint-url ...` 直接打数据面，确认凭据本身正确。
2. S3 API 通 → Console 仍登录不上：99% 是 user error（输错密码 / 大小写 / 粘贴带空格），不是 env var 问题。
3. S3 API 也不通 → 检查 `docker logs` 是否报凭据加载失败，回到本反模式核查 env / CLI flags。

跳过第 1 步直接猜 env 名，是 PR #10 现场犯过的真实弯路。

---

### H2. S3 兼容存储不能复用彼此的私有 health endpoint

**来源**：PR #10 review（任务 #63 RustFS 迁移）
**严重度**：🟡 中

**问题**：S3 兼容存储产品的私有 health endpoint 各自定义，互不兼容。MinIO 的 `/minio/health/live` 在 RustFS 上会 404，即使 S3 数据面是健康的，healthcheck 也会判定容器 unhealthy。

**❌ 错误范例**：

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
```

**✅ 正确范例**：

```yaml
healthcheck:
  test:
    - "CMD-SHELL"
    - "curl -s -o /dev/null -w '%{http_code}' http://localhost:9000/ | grep -qE '^(200|403)$'"
```

如果 RustFS 后续在 release notes 给出稳定的 `/health` 或 `/ready` 端点，优先用 `curl -f` 打官方端点。

**Codex 自检方法**：

```bash
grep -n "/minio/health/live" docker-compose.yml
```

除非服务确实是 MinIO，否则该命令必须无输出。

---

## I. 子 agent 协作

### I1. sub-agent 自行扩范围 / 跳过集成测试

**来源**：CLAUDE.md 原则 P4（v1.2 新增）
**严重度**：🔴 高

**问题**：主 agent 把任务派给 sub-agent 后，sub-agent 看到顺手能修的就修了，或多个 sub-agent 并行改同一批文件无协调，或 sub-agent 自报"测试已通过"主 agent 就直接合并 PR。结果：范围漂移导致 review 爆炸；并行冲突在 merge 时才暴露；最终验证从未在集成后的分支上跑过，单 sub-agent 局部通过的测试在集成后失败被忽略。

**❌ 错误范例**：

```text
主 agent: "派 sub-agent A 改 services/llm.py + sub-agent B 改 services/llm.py"
                                  ↑ 同文件并行，必冲突

主 agent: "sub-agent 说 pytest 全过，直接 commit"
                          ↑ sub-agent 跑的是切片测试，未在集成后分支重跑

sub-agent: "顺手把 services/qdrant.py 的 logger 也改了"
                ↑ 不在派单范围，未记 Handoff §3 偏差
```

**✅ 正确范例**：

```text
主 agent 派单格式：
  - 文件清单：明确列出每个 sub-agent 可碰的文件
  - 不可触碰清单：声明对方的文件
  - 计划先行：>1 文件 / 改抽象层 必须先出计划再改代码
  - 并行条件：文件冲突低 + 边界清晰 才并行
  - 集成步骤：sub-agent 完成 → 主 agent 集成 → 在集成后分支跑 SELF_REVIEW Part A 完整 8 项
  - 偏差登记：任何 sub-agent 顺手做的事 → Handoff §3 列出
```

**Codex 自检方法**：

```bash
# 1. 派单时检查每个 sub-agent prompt 是否含"文件清单 + 不可触碰清单"
grep -rE "sub-agent|subagent|派.*执行" docs/handoffs/ -l | xargs grep -L "文件清单\|不可触碰"

# 2. 集成后验证：merge 后必须在集成分支上完整跑过 Part A
git log --oneline feat/W?-D?-N-xxx | head -10  # 最后一个 commit 必须是 "test: rerun self-review after integration"
```

Handoff §3 必须显式声明：哪些工作是 sub-agent 派出去做的、是否有偏差、最终 SELF_REVIEW 是否在集成后跑过。

---

## J. 路由分流

### J1. admin / CRM / 内部 search endpoint 挂错路由树

**来源**：CLAUDE.md 原则 P3（v1.1 新增）/ 任务 #37 #39 v1.1 升级
**严重度**：🔴 高

**问题**：FastAPI 项目里 admin endpoint（用量统计 / 知识缺口 / CRM 查询 / 内部 search）被挂到顶层 `api_router` 或 `public_router`，外部公众号 / 客服渠道走到的 reverse proxy 路径下能直接访问。原则 P3 要求：物理拆 `internal_router` (`/api/v1/internal/`) 和 `public_router` (`/api/v1/public/`) 两棵独立路由树，admin 类只挂 internal。挂错相当于把内部接口暴露给外部，认证中间件也可能因 router 配置不同跳过。

**❌ 错误范例**：

```python
# app/api/__init__.py
api_router = APIRouter(prefix="/api/v1")
api_router.include_router(admin.router)        # ❌ admin 挂顶层
api_router.include_router(usage.router)        # ❌ usage 挂顶层
api_router.include_router(public_chat.router)  # ❌ 内外混挂
```

**✅ 正确范例**：

```python
# app/api/__init__.py
internal_router = APIRouter(prefix="/api/v1/internal", dependencies=[Depends(require_internal_user)])
public_router   = APIRouter(prefix="/api/v1/public",   dependencies=[Depends(require_external_or_internal)])
api_router      = APIRouter(prefix="/api/v1")  # 仅中性 endpoint

internal_router.include_router(admin.router)
internal_router.include_router(usage.router)
internal_router.include_router(crm.router)
internal_router.include_router(internal_search.router)

public_router.include_router(public_chat.router)
public_router.include_router(external_search.router)

api_router.include_router(feedback.router)     # 中性
api_router.include_router(health.router)       # 中性

app.include_router(internal_router)
app.include_router(public_router)
app.include_router(api_router)
```

**Codex 自检方法**：

```bash
# 1. 检查 admin / usage / crm 类 router 是否只挂在 internal_router
grep -nE "include_router\(.*(admin|usage|crm|internal_search)" backend/app/api/__init__.py | grep -v "internal_router"
# 必须无输出

# 2. 跑测试：外部 user 请求 /api/v1/internal/* 必须 403
pytest backend/tests/test_router_isolation.py -v

# 3. CI gate：fail 时立刻阻断 merge
```

任务 #37 §4.10-4.11 / #39 §4 给了具体范本。

---

## K. 数据脱敏

### K1. Pydantic response 明文返回敏感字段给外部用户

**来源**：CLAUDE.md 原则 P1（v1.1 新增）
**严重度**：🔴 高

**问题**：Pydantic response model 直接定义 `phone: str` / `email: str` / `contract_amount: Decimal` 字段，"前端再隐藏"。结果：外部公众号渠道 / 第三方爬虫 / 抓包工具直接拿到 11 位手机号、完整邮箱、合同金额。前端隐藏不是安全边界，必须在 API 层 sanitize。

**❌ 错误范例**：

```python
class CustomerOut(BaseModel):
    name: str
    phone: str            # ❌ 明文返回
    email: str            # ❌ 明文返回
    contract_amount: Decimal  # ❌ 明文返回

@router.get("/customers/{id}")
async def get_customer(id: str, user: User = Depends(get_current_user)):
    customer = await crm.get_customer(id)
    return CustomerOut.model_validate(customer)  # ❌ 不分内外用户
```

**✅ 正确范例**：

```python
# app/api/utils/sanitize.py
def mask_phone(p: str) -> str:
    return p[:3] + "****" + p[-4:] if p and len(p) == 11 else "****"

def mask_email(e: str) -> str:
    if not e or "@" not in e: return "****"
    name, domain = e.split("@", 1)
    return name[:2] + "***@" + domain

def sanitize_customer(payload: dict, user: User) -> dict:
    if user.is_external:
        payload["phone"] = mask_phone(payload.get("phone", ""))
        payload["email"] = mask_email(payload.get("email", ""))
        payload.pop("contract_amount", None)
    return payload

@router.get("/customers/{id}")
async def get_customer(id: str, user: User = Depends(get_current_user)):
    customer = await crm.get_customer(id)
    return sanitize_customer(customer.model_dump(), user)
```

**Codex 自检方法**：

```bash
# 1. grep 检查 response model 不能直接出现 raw 手机号 / 邮箱 / 金额字段
grep -nE "phone:\s*str|email:\s*str|amount:\s*(int|float|Decimal)" backend/app/models/ | grep -v "_masked\|sanitized\|internal"

# 2. 集成测试：用外部 user 拉任何 endpoint，断言 JSON 不含 11 位手机号
pytest backend/tests/test_sanitize.py::test_external_user_no_raw_phone -v

# 3. 断言示例
assert not re.search(r"\b1[3-9]\d{9}\b", response.text)
```

任何返回客户 / 员工 / 合同字段的 endpoint，必须经 `sanitize(payload, user)` 后再返回。

---

## 如何追加新反模式

每次审查（或自审查 Part E3）发现新反模式时：

1. 选个未占用的 ID（按字母+序号，如 `F1`, `A2`）
2. 复制以下模板填写：

```
### [ID]. [标题]

**来源**：PR #N review / 或 自审 task ID
**严重度**：🔴 高 / 🟡 中 / 🟢 低

**问题**：[1-2 句描述]

**❌ 错误范例**：

[10 行以内代码]

**✅ 正确范例**：

[10 行以内代码]

**Codex 自检方法**：

[grep / 命令，能自动检出该反模式]
```

3. 更新顶部"索引"表格
4. 提 PR，commit message：`docs: add antipattern [ID] [标题]`

---

## 维护原则

- **不要删除已有反模式**：即使后来发现不算问题，标记为"已废弃"而非删除
- **简洁优先**：每条 50 行以内，长篇分析写到 PR 描述
- **可执行优先**：每条必须有 Codex 能跑的自检命令
- **真实优先**：每条必须来自真实 PR review 或自审发现，不要凭空设想

---

_v1.4 | 反模式 11 条 + G 类占位 | 最后更新：2026-06-05_

变更（v1.4）：
- 新增 I1 sub-agent 自行扩范围 / 跳过集成测试（来源 原则 P4）
- 新增 J1 admin / CRM / 内部 search endpoint 挂错路由树（来源 原则 P3）
- 新增 K1 Pydantic response 明文返回敏感字段给外部用户（来源 原则 P1）
