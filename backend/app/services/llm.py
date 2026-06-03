"""Unified LlamaIndex clients for LLM, embedding, and rerank calls.

All model endpoints, model names, and credentials come from settings so business
code can switch providers without touching call sites.
"""

from collections.abc import Mapping
from typing import Final, TypedDict

import httpx
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.openai_like import OpenAILike
from pydantic import SecretStr

from app.core.config import settings
from app.core.exceptions import LLMServiceError

__all__ = ["get_llm", "get_embedding", "get_reranker", "BailianRerank"]

_RERANK_PATH: Final = "/services/rerank/text-rerank/text-rerank"
_RERANK_TIMEOUT_SECONDS: Final = 30.0
_RERANK_MAX_ATTEMPTS: Final = 3
_EMBED_BATCH_SIZE: Final = 32
_LLM_CONTEXT_WINDOW: Final = 128000


class _RerankResult(TypedDict):
    index: int
    relevance_score: float


def get_llm() -> OpenAILike:
    """Return a configured LlamaIndex LLM client.

    The client uses the OpenAI-compatible endpoint configured in settings. Callers
    intentionally cannot override parameters here because configuration must stay
    centralized for provider switching.
    """
    return OpenAILike(
        model=settings.llm_model,
        api_base=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
        is_chat_model=True,
        context_window=_LLM_CONTEXT_WINDOW,
    )


def get_embedding() -> OpenAILikeEmbedding:
    """Return the local bge-m3 embedding client through infinity."""
    return OpenAILikeEmbedding(
        model_name=settings.embed_model,
        api_base=settings.embed_base_url,
        api_key="not-needed",
        embed_batch_size=_EMBED_BATCH_SIZE,
    )


class BailianRerank(BaseNodePostprocessor):
    """Bailian rerank wrapper for LlamaIndex node postprocessing."""

    model: str
    top_n: int
    base_url: str
    api_key: SecretStr

    def _postprocess_nodes(
        self,
        nodes: list[NodeWithScore],
        query_bundle: QueryBundle | None = None,
    ) -> list[NodeWithScore]:
        if query_bundle is None or not nodes:
            return nodes

        documents = [node.node.get_content() for node in nodes]
        results = self._request_rerank(query=query_bundle.query_str, documents=documents)
        return self._apply_results(nodes=nodes, results=results)

    def _request_rerank(self, *, query: str, documents: list[str]) -> list[_RerankResult]:
        payload = {
            "model": self.model,
            "input": {"query": query, "documents": documents},
            "parameters": {"return_documents": False, "top_n": self.top_n},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url.rstrip('/')}{_RERANK_PATH}"

        last_error: Exception | None = None
        for _ in range(_RERANK_MAX_ATTEMPTS):
            try:
                with httpx.Client(timeout=_RERANK_TIMEOUT_SECONDS) as client:
                    response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return _parse_rerank_results(response.json())
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                last_error = exc

        message = "Bailian rerank request failed"
        if last_error is not None:
            raise LLMServiceError(message) from last_error
        raise LLMServiceError(message)

    def _apply_results(
        self,
        *,
        nodes: list[NodeWithScore],
        results: list[_RerankResult],
    ) -> list[NodeWithScore]:
        ranked_nodes: list[NodeWithScore] = []
        sorted_results = sorted(
            results[: self.top_n],
            key=lambda result: result["relevance_score"],
            reverse=True,
        )

        for result in sorted_results:
            node_index = result["index"]
            if node_index < 0 or node_index >= len(nodes):
                raise LLMServiceError("Bailian rerank response contains invalid node index")
            ranked_nodes.append(
                nodes[node_index].model_copy(update={"score": result["relevance_score"]})
            )

        return ranked_nodes


def get_reranker() -> BailianRerank:
    """Return a configured Bailian reranker sharing the LLM API key."""
    return BailianRerank(
        model=settings.rerank_model,
        top_n=settings.rerank_n,
        base_url=settings.rerank_base_url,
        api_key=settings.llm_api_key,
    )


def _parse_rerank_results(data: object) -> list[_RerankResult]:
    if not isinstance(data, Mapping):
        raise ValueError("Rerank response must be a JSON object")

    output = data.get("output")
    if not isinstance(output, Mapping):
        raise ValueError("Rerank response missing output object")

    raw_results = output.get("results")
    if not isinstance(raw_results, list):
        raise ValueError("Rerank response missing results list")

    results: list[_RerankResult] = []
    for raw_result in raw_results:
        if not isinstance(raw_result, Mapping):
            raise ValueError("Rerank result must be an object")

        index = raw_result.get("index")
        score = raw_result.get("relevance_score")
        if not isinstance(index, int) or not isinstance(score, int | float):
            raise ValueError("Rerank result missing index or relevance_score")

        results.append({"index": index, "relevance_score": float(score)})

    return results
