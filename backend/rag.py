"""RAG pipeline: retrieve relevant chunks then generate a grounded answer."""

import os

from llm.client import generate
from vector.store import search_chunks

TOP_K = int(os.getenv("RAG_TOP_K", "5"))

_SYSTEM_PROMPT = (
    "You are a tender document analyst. "
    "Answer the question using ONLY the document excerpts provided below. "
    "Be concise and precise. "
    "When referencing specific information, mention the source document name. "
    'If the answer cannot be found in the excerpts, say "I could not find this '
    'information in the uploaded documents." and stop.'
)


def _build_sources(chunks: list[dict]) -> list[dict]:
    """Enrich raw Qdrant chunks with page_number estimated from DB metadata."""
    from models import Document

    doc_ids = list({c["document_id"] for c in chunks if c.get("document_id")})

    doc_meta: dict[str, dict] = {}
    for doc in Document.query.filter(Document.id.in_(doc_ids)).all():
        doc_meta[doc.id] = {
            "chunk_count": len(doc.chunks),
            "page_count": doc.text.page_count if doc.text else None,
        }

    sources = []
    for c in chunks:
        doc_id = c.get("document_id") or ""
        meta = doc_meta.get(doc_id, {})
        chunk_count = meta.get("chunk_count") or 0
        page_count = meta.get("page_count")

        if page_count and chunk_count > 0:
            progress = c["chunk_index"] / max(chunk_count - 1, 1)
            page_number = round(progress * (page_count - 1)) + 1
        else:
            page_number = None

        snippet = c["text"][:350] + ("..." if len(c["text"]) > 350 else "")
        sources.append({
            "document_id": doc_id,
            "filename": c["filename"],
            "chunk_index": c["chunk_index"],
            "page_number": page_number,
            "text": snippet,
            "score": c["score"],
        })

    return sources


def answer_question(session_id: str, question: str) -> dict:
    """Retrieve top-K chunks for *question*, build a grounded prompt, return answer + sources."""

    chunks = search_chunks(question, session_id=session_id, top_k=TOP_K)

    if not chunks:
        return {
            "answer": (
                "No indexed documents found for this session. "
                "Upload documents and wait for them to finish processing (status = ready)."
            ),
            "sources": [],
        }

    context_parts = [
        f"[Source {i + 1}: {c['filename']}, chunk {c['chunk_index']}]\n{c['text']}"
        for i, c in enumerate(chunks)
    ]
    context = "\n\n---\n\n".join(context_parts)

    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Document excerpts:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

    answer = generate(prompt)
    sources = _build_sources(chunks)

    return {"answer": answer, "sources": sources}
