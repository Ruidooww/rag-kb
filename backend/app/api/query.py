from time import perf_counter

from fastapi import APIRouter

from app.core.config import settings
from app.models.query import QueryRequest, QueryResponse
from app.services.rag_pipeline import generate_answer, retrieve

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """基础 RAG 问答。"""
    started_at = perf_counter()
    top_k = request.top_k or settings.top_k
    rerank_n = request.rerank_n or settings.rerank_n
    sources = await retrieve(request.query, top_k=top_k, rerank_n=rerank_n)
    answer = await generate_answer(request.query, sources)

    return QueryResponse(
        answer=answer,
        sources=sources,
        latency_ms=int((perf_counter() - started_at) * 1000),
        model_used=settings.llm_model,
    )
