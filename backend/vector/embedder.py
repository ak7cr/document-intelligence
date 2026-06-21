"""Lazy singleton for BAAI/bge-small-en-v1.5 (384-dim, cosine).

numpy and sentence_transformers are imported lazily (inside functions) so
they are only loaded after Celery forks a child process.  Importing them at
module level causes SIGABRT on macOS because the Objective-C runtime aborts
any forked process that inherited a multi-threaded library (numpy loads
OpenBLAS/Accelerate at import time).
"""

from __future__ import annotations

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384
_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        # Force CPU — bge-small-en-v1.5 is 33M params and fast enough on CPU.
        # Keeping it off GPU leaves VRAM free for EasyOCR's CRAFT model.
        _model = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embed document passages. Returns list of float vectors (len = EMBEDDING_DIM)."""
    if not texts:
        return []
    result = _get_model().encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )
    return result.tolist()


def embed_query(text: str) -> list[float]:
    """Embed a search query with BGE retrieval prefix."""
    result = _get_model().encode(
        _QUERY_PREFIX + text,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return result.tolist()
