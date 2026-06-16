"""Lazy singleton for BAAI/bge-small-en-v1.5 (384-dim, cosine).

Passage embeddings: no prefix.
Query embeddings: add BGE retrieval instruction prefix.
"""

from __future__ import annotations

import numpy as np

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_passages(texts: list[str]) -> np.ndarray:
    """Embed document passages. Returns float32 array of shape (N, 384)."""
    if not texts:
        return np.empty((0, EMBEDDING_DIM), dtype=np.float32)
    return _get_model().encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )


def embed_query(text: str) -> list[float]:
    """Embed a search query with BGE retrieval prefix."""
    vec = _get_model().encode(
        _QUERY_PREFIX + text,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vec.tolist()
