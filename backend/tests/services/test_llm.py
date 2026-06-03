import json
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.base.llms.types import CompletionResponse
from llama_index.core.schema import NodeWithScore, TextNode
from pydantic import SecretStr, ValidationError

from app.core.config import Settings, settings
from app.core.exceptions import LLMServiceError
from app.services.llm import BailianRerank, get_embedding, get_llm, get_reranker


def _has_real_llm_api_key() -> bool:
    api_key = settings.llm_api_key.get_secret_value()
    return bool(api_key) and not api_key.startswith("sk-请填入")


requires_real_llm_key = pytest.mark.skipif(
    not _has_real_llm_api_key(),
    reason="需要真实 LLM_API_KEY",
)


class _RerankHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        content_length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(content_length))
        assert payload["input"]["query"] == "热带水果"
        assert payload["parameters"]["top_n"] == 2

        response_body = {
            "output": {
                "results": [
                    {"index": 2, "relevance_score": 0.95},
                    {"index": 0, "relevance_score": 0.82},
                ]
            }
        }
        response_bytes = json.dumps(response_body).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, format: str, *args: object) -> None:
        return


@pytest.fixture
def local_rerank_server_url() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RerankHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_settings_loads_from_env(tmp_path: Path) -> None:
    assert settings.llm_model
    assert settings.llm_base_url
    assert settings.embed_model
    assert settings.embed_base_url
    assert settings.rerank_model
    assert settings.rerank_base_url

    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LLM_BASE_URL=https://example.test/v1",
                "LLM_MODEL=test-model",
                "RERANK_BASE_URL=https://example.test/api/v1",
                "RERANK_MODEL=test-rerank",
                "EMBED_BASE_URL=http://localhost:8080",
                "EMBED_MODEL=BAAI/bge-m3",
                "POSTGRES_URL=postgresql+asyncpg://rag:ragpass@localhost:5432/rag",
                "QDRANT_URL=http://localhost:6333",
                "MINIO_ENDPOINT=localhost:9000",
                "MINIO_ACCESS_KEY=minioadmin",
                "MINIO_SECRET_KEY=minioadmin",
                "MINIO_BUCKET=rag-documents",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        Settings(_env_file=env_file)


def test_get_llm_returns_configured_client() -> None:
    llm = get_llm()

    assert llm.model == settings.llm_model
    assert llm.api_base == settings.llm_base_url
    assert llm.temperature == settings.temperature
    assert llm.max_tokens == settings.max_tokens


@requires_real_llm_key
@pytest.mark.integration
def test_get_llm_completion() -> None:
    response = get_llm().complete("用一句话介绍 RAG")

    assert isinstance(response, CompletionResponse)
    assert response.text
    assert len(response.text) > 10


def test_get_embedding_dimension() -> None:
    embedder = get_embedding()

    vector = embedder.get_text_embedding("测试文本")

    assert isinstance(embedder, BaseEmbedding)
    assert isinstance(vector, list)
    assert len(vector) == 1024
    assert all(isinstance(value, float) for value in vector)


def test_get_embedding_batch() -> None:
    vectors = get_embedding().get_text_embedding_batch(["a", "b", "c"])

    assert len(vectors) == 3
    assert all(len(vector) == 1024 for vector in vectors)


@requires_real_llm_key
@pytest.mark.integration
def test_reranker_reorders_nodes() -> None:
    nodes = [
        NodeWithScore(node=TextNode(text="苹果"), score=0.1),
        NodeWithScore(node=TextNode(text="汽车"), score=0.1),
        NodeWithScore(node=TextNode(text="水果香蕉"), score=0.1),
    ]

    ranked_nodes = get_reranker().postprocess_nodes(nodes, query_str="热带水果")

    assert 0 < len(ranked_nodes) <= settings.rerank_n
    first_content = ranked_nodes[0].node.get_content()
    assert "水果" in first_content or "苹果" in first_content


def test_reranker_empty_input() -> None:
    assert get_reranker().postprocess_nodes([], query_str="热带水果") == []


def test_reranker_reorders_nodes_with_local_http_server(local_rerank_server_url: str) -> None:
    nodes = [
        NodeWithScore(node=TextNode(text="苹果"), score=0.1),
        NodeWithScore(node=TextNode(text="汽车"), score=0.1),
        NodeWithScore(node=TextNode(text="水果香蕉"), score=0.1),
    ]
    reranker = BailianRerank(
        model="test-rerank",
        top_n=2,
        base_url=local_rerank_server_url,
        api_key=SecretStr("test-key"),
    )

    ranked_nodes = reranker.postprocess_nodes(nodes, query_str="热带水果")

    assert [node.node.get_content() for node in ranked_nodes] == ["水果香蕉", "苹果"]
    assert [node.score for node in ranked_nodes] == [0.95, 0.82]


def test_reranker_api_failure() -> None:
    reranker = BailianRerank(
        model=settings.rerank_model,
        top_n=settings.rerank_n,
        base_url="http://127.0.0.1:1",
        api_key=settings.llm_api_key,
    )
    nodes = [NodeWithScore(node=TextNode(text="苹果"), score=0.1)]

    with pytest.raises(LLMServiceError):
        reranker.postprocess_nodes(nodes, query_str="热带水果")
