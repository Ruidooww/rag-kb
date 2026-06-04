from collections.abc import Iterator

import pytest

from app.core.config import settings
from app.core.exceptions import VectorStoreError
from app.services.qdrant_store import (
    ChunkPayload,
    ensure_collection,
    get_qdrant_client,
    search_chunks,
    upsert_chunks,
)


@pytest.fixture
def qdrant_test_collection() -> Iterator[str]:
    collection = f"{settings.qdrant_collection}_pytest"
    client = get_qdrant_client()
    if client.collection_exists(collection):
        client.delete_collection(collection)
    yield collection
    if client.collection_exists(collection):
        client.delete_collection(collection)


@pytest.mark.integration
def test_ensure_collection_idempotent(qdrant_test_collection: str) -> None:
    ensure_collection(qdrant_test_collection)
    ensure_collection(qdrant_test_collection)

    assert get_qdrant_client().collection_exists(qdrant_test_collection)


@pytest.mark.integration
def test_upsert_and_search(qdrant_test_collection: str) -> None:
    ensure_collection(qdrant_test_collection)
    chunks = [
        ChunkPayload(
            chunk_id="product-install",
            text="产品 X 安装需要先复制配置文件，再启动 Docker 服务。",
            vector=[0.1] * 1024,
            metadata={"doc_id": "product_x_manual", "chunk_index": 0},
        ),
        ChunkPayload(
            chunk_id="faq-privacy",
            text="隐私问题需要通过脱敏和供应商协议控制。",
            vector=[0.2] * 1024,
            metadata={"doc_id": "faq_general", "chunk_index": 0},
        ),
        ChunkPayload(
            chunk_id="team-review",
            text="代码 review 需要检查测试、风险和错误处理。",
            vector=[0.3] * 1024,
            metadata={"doc_id": "team_handbook", "chunk_index": 0},
        ),
    ]

    upsert_chunks(qdrant_test_collection, chunks)
    results = search_chunks(qdrant_test_collection, [0.1] * 1024, top_k=2)

    assert len(results) == 2
    assert results[0].chunk_id
    assert results[0].doc_id
    assert results[0].text


@pytest.mark.integration
def test_search_with_filter(qdrant_test_collection: str) -> None:
    ensure_collection(qdrant_test_collection)
    upsert_chunks(
        qdrant_test_collection,
        [
            ChunkPayload(
                chunk_id="doc-a",
                text="产品安装说明",
                vector=[0.1] * 1024,
                metadata={"doc_id": "product_x_manual", "chunk_index": 0},
            ),
            ChunkPayload(
                chunk_id="doc-b",
                text="团队流程说明",
                vector=[0.1] * 1024,
                metadata={"doc_id": "team_handbook", "chunk_index": 0},
            ),
        ],
    )

    results = search_chunks(
        qdrant_test_collection,
        [0.1] * 1024,
        top_k=5,
        metadata_filter={"doc_id": "team_handbook"},
    )

    assert [source.doc_id for source in results] == ["team_handbook"]


def test_vector_store_error_on_invalid_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "qdrant_url", "http://127.0.0.1:1")

    with pytest.raises(VectorStoreError):
        ensure_collection("invalid_url_collection")
