"""Qdrant operations for document chunk vectors."""

from __future__ import annotations

import logging
import os

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)

from vector.embedder import EMBEDDING_DIM, embed_query

logger = logging.getLogger(__name__)

COLLECTION = "tender_chunks"
_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", "6333"))
        _client = QdrantClient(host=host, port=port, timeout=10)
    return _client


def init_collection() -> None:
    """Create the Qdrant collection if it doesn't already exist."""
    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        logger.info("Qdrant: created collection '%s'", COLLECTION)
    else:
        logger.debug("Qdrant: collection '%s' already exists", COLLECTION)


def upsert_chunks(points: list[PointStruct]) -> None:
    """Upsert a batch of embedded chunk points."""
    if not points:
        return
    _get_client().upsert(collection_name=COLLECTION, points=points, wait=True)


def delete_doc_vectors(document_id: str) -> None:
    """Remove all Qdrant points belonging to a document."""
    _get_client().delete(
        collection_name=COLLECTION,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
            )
        ),
        wait=True,
    )


def search_chunks(
    query: str,
    session_id: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Semantic search: embed *query* and return top-K matching chunks.

    If *session_id* is provided, results are scoped to that session only.
    """
    query_vec = embed_query(query)

    must = []
    if session_id:
        must.append(FieldCondition(key="session_id", match=MatchValue(value=session_id)))
    query_filter = Filter(must=must) if must else None

    hits = _get_client().search(
        collection_name=COLLECTION,
        query_vector=query_vec,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )
    return [
        {
            "score": round(float(h.score), 4),
            "document_id": h.payload.get("document_id"),
            "chunk_id": h.payload.get("chunk_id"),
            "chunk_index": h.payload.get("chunk_index"),
            "filename": h.payload.get("filename"),
            "text": h.payload.get("text"),
        }
        for h in hits
    ]
