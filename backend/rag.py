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
        f"[Source: {c['filename']}, chunk {c['chunk_index']}]\n{c['text']}"
        for c in chunks
    ]
    context = "\n\n---\n\n".join(context_parts)

    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Document excerpts:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

    answer = generate(prompt)

    sources = [
        {
            "filename": c["filename"],
            "chunk_index": c["chunk_index"],
            "text": c["text"][:350] + ("..." if len(c["text"]) > 350 else ""),
            "score": c["score"],
        }
        for c in chunks
    ]

    return {"answer": answer, "sources": sources}
