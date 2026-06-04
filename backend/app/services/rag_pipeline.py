import asyncio
from pathlib import Path

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import MetadataMode, NodeWithScore, TextNode
from loguru import logger

from app.core.config import settings
from app.core.exceptions import LLMServiceError, ValidationError
from app.models.query import SourceChunk
from app.services.llm import get_embedding, get_llm, get_reranker
from app.services.qdrant_store import ChunkPayload, ensure_collection, search_chunks, upsert_chunks

PROMPT_PATH = Path(__file__).parents[1] / "prompts" / "base_qa.txt"
SUPPORTED_SUFFIXES = {".md", ".txt"}
VECTOR_SIZE = 1024


async def ingest_file(file_path: Path, collection: str | None = None) -> int:
    """读文件 → 切片 → 向量化 → 入库。返回入库的 chunk 数。"""
    if file_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValidationError(f"Unsupported file format: {file_path.suffix}")

    collection_name = collection or settings.qdrant_collection
    text = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
    splitter = SentenceSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = [chunk for chunk in splitter.split_text(text) if chunk.strip()]
    if not chunks:
        return 0

    embedder = get_embedding()
    vectors = await asyncio.to_thread(embedder.get_text_embedding_batch, chunks)
    payloads = [
        ChunkPayload(
            chunk_id=f"{file_path.stem}:{index}",
            text=chunk,
            vector=vector,
            metadata={
                "doc_id": file_path.stem,
                "file_path": str(file_path),
                "chunk_index": index,
            },
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]

    await asyncio.to_thread(ensure_collection, collection_name, VECTOR_SIZE)
    await asyncio.to_thread(upsert_chunks, collection_name, payloads)
    return len(payloads)


async def retrieve(query: str, top_k: int, rerank_n: int) -> list[SourceChunk]:
    """Embedding → Qdrant 检索 → Rerank → 返回 Top-rerank_n。"""
    embedder = get_embedding()
    query_vector = await embedder.aget_query_embedding(query)
    sources = await asyncio.to_thread(
        search_chunks,
        settings.qdrant_collection,
        query_vector,
        top_k,
    )
    if not sources:
        return []

    nodes = [_source_to_node(source) for source in sources]
    try:
        ranked_nodes = await asyncio.to_thread(
            get_reranker().postprocess_nodes,
            nodes,
            query_str=query,
        )
    except LLMServiceError as exc:
        logger.warning(f"Rerank failed; falling back to vector order: {exc.message}")
        return sources[:rerank_n]

    return [_node_to_source(node) for node in ranked_nodes[:rerank_n]]


async def generate_answer(query: str, sources: list[SourceChunk]) -> str:
    """根据召回的 sources + query，让 Omni 生成答案。"""
    if not sources:
        return "暂未收录此问题"

    template = await asyncio.to_thread(PROMPT_PATH.read_text, encoding="utf-8")
    sources_block = "\n".join(
        f"--- 文档: {source.doc_id} ---\n{source.text}\n" for source in sources
    )
    prompt = template.format(sources=sources_block, query=query)
    response = await asyncio.to_thread(get_llm().complete, prompt)
    return str(response.text)


def _source_to_node(source: SourceChunk) -> NodeWithScore:
    metadata = {
        **source.metadata,
        "doc_id": source.doc_id,
        "chunk_id": source.chunk_id,
    }
    return NodeWithScore(
        node=TextNode(id_=source.chunk_id, text=source.text, metadata=metadata),
        score=source.score,
    )


def _node_to_source(node: NodeWithScore) -> SourceChunk:
    metadata = {
        key: value
        for key, value in node.node.metadata.items()
        if isinstance(value, str | int | float)
    }
    return SourceChunk(
        doc_id=str(metadata.get("doc_id", "")),
        chunk_id=str(metadata.get("chunk_id", node.node.node_id)),
        text=node.node.get_content(metadata_mode=MetadataMode.NONE),
        score=float(node.score or 0.0),
        metadata=metadata,
    )
