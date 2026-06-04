from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.core.exceptions import VectorStoreError
from app.models.query import SourceChunk


@dataclass(frozen=True)
class ChunkPayload:
    chunk_id: str
    text: str
    vector: list[float]
    metadata: dict[str, str | int | float]


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, timeout=5)


def ensure_collection(collection: str, vector_size: int = 1024) -> None:
    try:
        client = get_qdrant_client()
        if client.collection_exists(collection):
            return
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE,
            ),
        )
    except Exception as exc:
        raise VectorStoreError(f"Qdrant collection ensure failed: {collection}") from exc


def upsert_chunks(collection: str, chunks: list[ChunkPayload]) -> None:
    if not chunks:
        return

    try:
        client = get_qdrant_client()
        points = [
            models.PointStruct(
                id=str(uuid5(NAMESPACE_URL, f"{collection}:{chunk.chunk_id}")),
                vector=chunk.vector,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    **chunk.metadata,
                },
            )
            for chunk in chunks
        ]
        client.upsert(collection_name=collection, points=points)
    except Exception as exc:
        raise VectorStoreError(f"Qdrant chunk upsert failed: {collection}") from exc


def search_chunks(
    collection: str,
    query_vector: Sequence[float],
    top_k: int,
    filter: Mapping[str, str | int | float] | None = None,
    *,
    metadata_filter: Mapping[str, str | int | float] | None = None,
) -> list[SourceChunk]:
    effective_filter = metadata_filter if metadata_filter is not None else filter

    try:
        client = get_qdrant_client()
        response = client.query_points(
            collection_name=collection,
            query=list(query_vector),
            query_filter=_build_filter(effective_filter),
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return [_point_to_source(point) for point in response.points]
    except Exception as exc:
        raise VectorStoreError(f"Qdrant chunk search failed: {collection}") from exc


def _build_filter(
    metadata_filter: Mapping[str, str | int | float] | None,
) -> models.Filter | None:
    if not metadata_filter:
        return None

    return models.Filter(
        must=[
            models.FieldCondition(
                key=key,
                match=models.MatchValue(value=value),
            )
            for key, value in metadata_filter.items()
        ]
    )


def _point_to_source(point: models.ScoredPoint) -> SourceChunk:
    payload = point.payload or {}
    metadata = {
        key: value
        for key, value in payload.items()
        if key != "text" and isinstance(value, str | int | float)
    }
    chunk_id = str(metadata.get("chunk_id", point.id))
    doc_id = str(metadata.get("doc_id", ""))
    text = str(payload.get("text", ""))

    return SourceChunk(
        doc_id=doc_id,
        chunk_id=chunk_id,
        text=text,
        score=float(point.score),
        metadata=metadata,
    )
