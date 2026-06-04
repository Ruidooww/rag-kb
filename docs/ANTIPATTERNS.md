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

_v1.1 | 反模式 6 条 | 最后更新：2026-06-04_
