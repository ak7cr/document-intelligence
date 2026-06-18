"""Cross-encoder reranker — improves RAG chunk ordering before the LLM call.

Downloads cross-encoder/ms-marco-MiniLM-L-6-v2 (~68 MB) on first use.
Falls back silently to the original Qdrant order if loading fails.
"""

import logging

logger = logging.getLogger(__name__)

_model = None
_load_attempted = False


def _get_model():
    global _model, _load_attempted
    if _load_attempted:
        return _model
    _load_attempted = True
    try:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
        logger.info("Cross-encoder reranker loaded")
    except Exception as exc:
        logger.warning("Cross-encoder unavailable (%s) — reranking disabled", exc)
        _model = None
    return _model


def rerank(query: str, chunks: list[dict]) -> list[dict]:
    """Rerank chunks by cross-encoder relevance score. Returns new sorted list."""
    if not chunks:
        return chunks
    model = _get_model()
    if model is None:
        return chunks
    try:
        pairs = [(query, c["text"]) for c in chunks]
        scores = model.predict(pairs)
        return [c for c, _ in sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)]
    except Exception as exc:
        logger.warning("Reranking failed (%s) — using original order", exc)
        return chunks
