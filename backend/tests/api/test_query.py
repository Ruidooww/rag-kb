import pytest
from fastapi.testclient import TestClient

from app.api import query as query_api
from app.core.config import settings
from app.models.query import SourceChunk
from app.services.rag_pipeline import ingest_file


def _has_real_llm_api_key() -> bool:
    api_key = settings.llm_api_key.get_secret_value()
    return bool(api_key) and not api_key.startswith("sk-请填入")


requires_real_llm_key = pytest.mark.skipif(
    not _has_real_llm_api_key(),
    reason="需要真实 LLM_API_KEY",
)


@requires_real_llm_key
@pytest.mark.integration
def test_query_endpoint_basic(client: TestClient) -> None:
    sample_doc = (
        __import__("pathlib").Path(__file__).parents[1]
        / "fixtures"
        / "sample_docs"
        / "product_x_manual.md"
    )
    __import__("asyncio").run(ingest_file(sample_doc))

    response = client.post("/api/v1/query", json={"query": "产品 X 怎么安装？", "top_k": 5})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"]
    assert data["sources"]
    assert isinstance(data["latency_ms"], int)


def test_query_endpoint_validation(client: TestClient) -> None:
    response = client.post("/api/v1/query", json={"query": ""})

    assert response.status_code == 422


def test_query_endpoint_includes_latency(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_retrieve(query: str, top_k: int, rerank_n: int) -> list[SourceChunk]:
        assert query == "产品 X 怎么安装？"
        assert top_k == settings.top_k
        assert rerank_n == settings.rerank_n
        return [
            SourceChunk(
                doc_id="product_x_manual",
                chunk_id="product_x_manual:0",
                text="产品 X 安装需要复制配置文件。",
                score=0.9,
                metadata={"chunk_index": 0},
            )
        ]

    async def fake_generate_answer(query: str, sources: list[SourceChunk]) -> str:
        assert query == "产品 X 怎么安装？"
        assert sources
        return "先复制配置文件，再启动服务。[来源: product_x_manual]"

    monkeypatch.setattr(query_api, "retrieve", fake_retrieve)
    monkeypatch.setattr(query_api, "generate_answer", fake_generate_answer)

    response = client.post("/api/v1/query", json={"query": "产品 X 怎么安装？"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "先复制配置文件，再启动服务。[来源: product_x_manual]"
    assert data["sources"][0]["doc_id"] == "product_x_manual"
    assert isinstance(data["latency_ms"], int)
    assert data["model_used"] == settings.llm_model
