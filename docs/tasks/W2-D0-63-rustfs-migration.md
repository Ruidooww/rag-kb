# Task #63: 切换对象存储 MinIO → RustFS

> **Phase**: 1 | **位置**: Week 1-Week 2 之间技术栈调整
> **预估工时**: 1.5-2 小时
> **优先级**: 🟡 中（W2-D4 #28 双轨入库前必须完成）
> **前置任务**: #15-#22 + #65（LangGraph）建议先做
> **按 v2.1 自审查机制执行**

---

## 1. 任务背景

MinIO 在 2021 年从 Apache 2.0 改为 AGPLv3。虽然公司内部使用合规，但为了：

1. **未来给前台智能客服铺路**：客服 Agent 可能需要预签名 URL / 大文件上传
2. **规避未来商用授权讨论**：直接换成 Apache 2.0 协议的替代品
3. **保持 S3 API 兼容**：抽象层零代码改动即可切换

我们换成 **RustFS**：
- Rust 写，Apache 2.0
- 单二进制部署
- 完全兼容 MinIO 的 S3 API
- 资源占用比 MinIO 低

**注意**：本任务**只切底层存储**，不修改任何 Agent 设计或业务代码。所有 Agent 通过 backend API 访问文件，不直接调 RustFS。

---

## 2. 前置依赖

| # | 验证方法 | 期望 |
|---|---------|------|
| Week 1 主线全合并 | `gh pr list --state merged` | PR #1-#8 都 merged |
| #65 LangGraph 已合并（推荐先做）| `grep -c "铁律 #8" CLAUDE.md` | >= 1 |
| Docker 4 服务跑着 | `docker compose ps` | qdrant/postgres/minio/infinity 都 healthy |
| 当前 MinIO 没有重要数据 | `docker exec rag-minio mc ls local/` | 空或仅测试数据 |
| main 干净 | `git status` | clean |

---

## 3. 任务目标

### 3.1 替换存储服务
- docker-compose.yml：删除 minio 服务，新增 rustfs 服务
- 验证 4 个 Docker 服务（qdrant / postgres / rustfs / infinity）全部 healthy

### 3.2 抽象存储访问
- 新增 `backend/app/services/storage.py`（DocumentStorage ABC + S3CompatibleStorage 实现）
- 业务代码通过 `storage.py` 访问文件，不直接调 S3 SDK
- 当前 Phase 1 还没真用对象存储的业务代码，主要是**为 Phase 2 #28 双轨入库铺路**

### 3.3 更新配置
- `.env.example` 把 MINIO_* 改 STORAGE_*
- `config.yaml` / `core/config.py` 同步字段重命名

### 3.4 测试覆盖
- `backend/tests/services/test_storage.py`（at least integration test）

---

## 4. 输出文件清单

### 4.1 `docker-compose.yml`（替换 minio → rustfs）

把 minio 服务整段替换为：

```yaml
  # ===== 对象存储（RustFS，S3 兼容，Apache 2.0）=====
  rustfs:
    image: rustfs/rustfs:latest
    container_name: rag-rustfs
    command: server /data --console-address ":9001"
    environment:
      RUSTFS_ACCESS_KEY: rustfsadmin
      RUSTFS_SECRET_KEY: rustfsadmin-please-change-me
      RUSTFS_VOLUMES: /data
    ports:
      - "9000:9000"     # S3 API
      - "9001:9001"     # Web Console
    volumes:
      - ./data/rustfs:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**注意**：
- 如果 RustFS 没暴露 `/minio/health/live`，改用其他健康检查端点（查 RustFS 官方文档）
- 默认密码 `rustfsadmin-please-change-me`，已加进 #61 backlog 提醒

### 4.2 `.env.example`（重命名 MINIO_* → STORAGE_*）

替换原 MinIO 配置段为：

```env
# ===== 对象存储（RustFS，S3 兼容）=====
STORAGE_BACKEND=rustfs            # 可选 rustfs / s3 / local（local 不支持，预留）
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_ACCESS_KEY=rustfsadmin
STORAGE_SECRET_KEY=rustfsadmin-please-change-me
STORAGE_BUCKET=rag-documents
STORAGE_REGION=us-east-1          # S3 SDK 需要，本地用 us-east-1 即可
```

### 4.3 `backend/app/core/config.py`（追加字段）

加新字段（删除老的 minio_*）：

```python
storage_backend: str = "rustfs"
storage_endpoint: str
storage_access_key: SecretStr
storage_secret_key: SecretStr
storage_bucket: str
storage_region: str = "us-east-1"
```

### 4.4 `backend/app/services/storage.py`（新建）

抽象层 + RustFS 实现：

```python
"""文档对象存储抽象层。

业务代码必须通过 `get_storage()` 访问文件，不要直接调 boto3/botocore。
未来切其他 S3 兼容存储（Garage / AWS S3 等）只需修改实现，不改业务代码。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Final

import boto3
from botocore.client import Config
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AppException

__all__ = ["DocumentStorage", "S3CompatibleStorage", "get_storage", "StorageError"]


class StorageError(AppException):
    error_code = "STORAGE_ERROR"
    status_code = 502


class DocumentStorage(ABC):
    @abstractmethod
    async def save(self, doc_id: str, content: bytes, *, content_type: str = "application/octet-stream") -> str: ...

    @abstractmethod
    async def load(self, doc_id: str) -> bytes: ...

    @abstractmethod
    async def delete(self, doc_id: str) -> None: ...

    @abstractmethod
    async def exists(self, doc_id: str) -> bool: ...

    @abstractmethod
    async def get_presigned_download_url(self, doc_id: str, *, expires_in: int = 3600) -> str: ...


_BUCKET_KEY_PREFIX: Final = "documents"


class S3CompatibleStorage(DocumentStorage):
    """S3 兼容存储实现（RustFS / Garage / AWS S3 / MinIO）。"""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint,
            aws_access_key_id=settings.storage_access_key.get_secret_value(),
            aws_secret_access_key=settings.storage_secret_key.get_secret_value(),
            region_name=settings.storage_region,
            config=Config(signature_version="s3v4"),
        )
        self._bucket = settings.storage_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception:
            self._client.create_bucket(Bucket=self._bucket)
            logger.info(f"Created bucket {self._bucket}")

    def _key(self, doc_id: str) -> str:
        return f"{_BUCKET_KEY_PREFIX}/{doc_id}"

    # 实现 save / load / delete / exists / get_presigned_download_url
    # 用 to_thread.run_sync 包装 boto3 同步调用（boto3 是 sync）
    # 详情见 spec §5
```

### 4.5 `backend/tests/services/test_storage.py`（新建）

至少 5 个测试用例，全部标 `@pytest.mark.integration`：

- `test_save_and_load_roundtrip`
- `test_exists_for_missing_key_returns_false`
- `test_delete_removes_file`
- `test_get_presigned_url_returns_https`（或 http:）
- `test_storage_error_on_invalid_endpoint`

注：需 RustFS 服务跑着才能通过。

### 4.6 `data/rustfs/`（新建空目录）

`mkdir data/rustfs` 让 Docker 卷映射有挂载点。
`.gitignore` 已有 `data/` 通配，不需追加。

### 4.7 `docs/STACK_UPDATE_V2.2.md`（在 #65 创建的文件里追加段落）

如 #65 已创建，本任务在末尾追加一段：

```markdown
## 7. 存储层调整：MinIO → RustFS

### 变更原因
- 规避 MinIO AGPLv3
- 为前台智能客服铺路（预签名 URL / 大文件）
- Apache 2.0 + Rust 单二进制更轻

### 抽象层设计
backend/app/services/storage.py 提供 DocumentStorage ABC，业务代码不直接调 boto3。

### Agent 集成
Agent 不直接访问 RustFS，通过 backend REST API（GET /api/v1/documents/{id}/file 或 url）访问。
```

### 4.8 `docs/CODEX_QUICK_REF.md`（新增"对象存储"小章节）

在"🛠 常用命令"前追加：

```markdown
## 💾 对象存储（RustFS）

| 操作 | 方法 |
|------|------|
| 保存文件 | `await get_storage().save(doc_id, bytes)` |
| 读文件 | `await get_storage().load(doc_id) -> bytes` |
| 预签名下载 URL | `await get_storage().get_presigned_download_url(doc_id, expires_in=3600)` |
| 删除 | `await get_storage().delete(doc_id)` |
| Web Console | http://localhost:9001（用户名 rustfsadmin）|

**业务代码禁止直接 import boto3** —— 走 services/storage.py 抽象。
```

### 4.9 `backend/pyproject.toml`（追加依赖）

```bash
uv add boto3 botocore
```

注：之前如果有 minio SDK 依赖，删掉 → `uv remove minio`。

---

## 5. S3CompatibleStorage 完整实现参考

```python
import asyncio
from anyio import to_thread


class S3CompatibleStorage(DocumentStorage):
    # ... (上面的 __init__ 和 _key 等)

    async def save(self, doc_id, content, *, content_type="application/octet-stream"):
        try:
            await to_thread.run_sync(
                lambda: self._client.put_object(
                    Bucket=self._bucket,
                    Key=self._key(doc_id),
                    Body=content,
                    ContentType=content_type,
                )
            )
            return f"s3://{self._bucket}/{self._key(doc_id)}"
        except Exception as exc:
            raise StorageError(f"Failed to save {doc_id}") from exc

    async def load(self, doc_id):
        try:
            response = await to_thread.run_sync(
                lambda: self._client.get_object(Bucket=self._bucket, Key=self._key(doc_id))
            )
            return await to_thread.run_sync(lambda: response["Body"].read())
        except self._client.exceptions.NoSuchKey:
            raise StorageError(f"Document not found: {doc_id}")
        except Exception as exc:
            raise StorageError(f"Failed to load {doc_id}") from exc

    async def delete(self, doc_id):
        try:
            await to_thread.run_sync(
                lambda: self._client.delete_object(Bucket=self._bucket, Key=self._key(doc_id))
            )
        except Exception as exc:
            raise StorageError(f"Failed to delete {doc_id}") from exc

    async def exists(self, doc_id):
        try:
            await to_thread.run_sync(
                lambda: self._client.head_object(Bucket=self._bucket, Key=self._key(doc_id))
            )
            return True
        except self._client.exceptions.ClientError:
            return False

    async def get_presigned_download_url(self, doc_id, *, expires_in=3600):
        try:
            return await to_thread.run_sync(
                lambda: self._client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self._bucket, "Key": self._key(doc_id)},
                    ExpiresIn=expires_in,
                )
            )
        except Exception as exc:
            raise StorageError(f"Failed to presign URL for {doc_id}") from exc


def get_storage() -> DocumentStorage:
    """工厂函数：根据 settings.storage_backend 返回实现。"""
    return S3CompatibleStorage()
```

---

## 6. 验收标准

### 6.1 服务启动
- [ ] `docker compose pull` 拉取 rustfs 镜像成功
- [ ] `docker compose up -d` 4 服务 healthy
- [ ] `docker compose ps` 看到 rag-rustfs container 运行
- [ ] http://localhost:9001 可以访问 Web Console
- [ ] http://localhost:9000 S3 API 响应（返回 XML 即可）

### 6.2 代码可运行
- [ ] `uv sync` 成功
- [ ] `uv run pytest tests/services/test_storage.py -v` integration 测试全绿
- [ ] `uv run pytest -m "not integration"` 不退化（保持 #20 的 13+ passed）
- [ ] storage.py 可被 `from app.services.storage import get_storage` 正确 import

### 6.3 抽象正确性
- [ ] save / load roundtrip 成功（写入后能读出相同内容）
- [ ] get_presigned_download_url 返回 URL 含 X-Amz-Signature

### 6.4 静态检查
- [ ] ruff / mypy / format 全绿

### 6.5 铁律合规
- [ ] grep `from boto3|import boto3` 仅在 `backend/app/services/storage.py`
- [ ] 业务代码无 `MINIO_` 残留：`grep -rE "MINIO_" backend/ docs/` 仅在 archive 或 history

### 6.6 Git / Handoff
- [ ] 分支 `feat/W2-D0-63-rustfs-migration`
- [ ] commit 含 `Refs: #63`
- [ ] PR 标题含 `#63`
- [ ] Handoff §0-§8 完整

---

## 7. 禁止事项

- ❌ 不要保留旧的 minio 服务定义（彻底替换）
- ❌ 不要在业务代码 import boto3（必须走 storage.py）
- ❌ 不要把 STORAGE_SECRET_KEY 真实值提交到 .env.example
- ❌ 不要让 storage.py 暴露 sync 接口（必须 async）
- ❌ 不要装 minio Python SDK（删掉，用 boto3）
- ❌ 不要直接装 `mc` CLI 工具（spec 不需要）

---

## 8. 常见陷阱

| 陷阱 | 后果 | 正确做法 |
|------|------|---------|
| RustFS 镜像 tag 不存在 | docker pull 失败 | 查 docker hub 实际 tag（如 `rustfs/rustfs:latest`，必要时锁定具体版本）|
| RustFS S3 API 不完全兼容 | head_bucket 等失败 | 用 boto3 + `signature_version="s3v4"` |
| 预签名 URL 失效 | 405 / 403 | 检查 region 和 host header |
| 异步 + boto3 混用阻塞 | event loop 卡住 | 必须用 `anyio.to_thread.run_sync` |
| bucket 不存在导致首次报错 | startup 卡住 | `_ensure_bucket` 幂等创建 |
| presigned URL 内网地址 | 客户端访问 404 | 部署时配反向代理或 STORAGE_ENDPOINT 用公网域名 |

---

## 9. 参考资料

- RustFS 官网：https://rustfs.com / https://github.com/rustfs/rustfs
- boto3 S3 客户端：https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
- 本项目：`CLAUDE.md` 铁律 #1 #2 / `docs/CODEX_QUICK_REF.md`

---

## 10. 估时拆解

| 子步骤 | 预估 |
|--------|------|
| 阅读 spec + RustFS 文档 | 20 分钟 |
| docker-compose.yml 替换 minio | 10 分钟 |
| .env.example + config.py 字段重命名 | 15 分钟 |
| 写 storage.py 抽象层 + 实现 | 40 分钟 |
| 写 test_storage.py 5 个用例 | 30 分钟 |
| 验证 4 个服务 healthy + bucket 创建 | 15 分钟 |
| 更新 QUICK_REF / STACK_UPDATE | 15 分钟 |
| Self-Review + Handoff | 30 分钟 |
| 提交 + PR | 10 分钟 |
| **合计** | **~3 小时** |

---

## 11. 与下一轮的衔接

#63 完成后，**Phase 2 W2-D4 #28 双轨入库**可以放心用 RustFS 存原文档了。

Handoff §7 应说明：
1. RustFS 已部署，Web Console http://localhost:9001
2. storage.py 抽象层入口：`get_storage()`
3. bucket 名走 settings.storage_bucket（默认 rag-documents）
4. 预签名 URL 接口已就绪，给前台智能客服 / Phase 3-4 上传 API 用
5. 默认密码 rustfsadmin-please-change-me，Phase 2 前必改（已在 #61 backlog）

---

_v1.0 | 任务 ID：#63 | 最后更新：2026-06-04_
